"""Ingesta RAG: documentos oficiales -> fragmentos -> embeddings Gemini -> pgvector (Supabase).

Fuentes:
  - data/oficial/docs/*.txt   (primera línea = URL de la fuente; el resto es el texto)
  - data/oficial/docs/planes/*.txt   (planes de estudio de todos los programas de la UNAB, uno por archivo)
  - plan de estudios de Ingeniería de Sistemas que usa la base (db/seed/planes.py: documento oficial, 151 créditos)
  - resumen de profesores de APOLO (data/oficial/unab_profesores.json), solo como contexto general

Uso (desde la raíz del proyecto):
    python rag/ingesta.py --dry-run       # escribe rag/salida_chunks.json, sin APIs ni base de datos
    python rag/ingesta.py                 # embeddings con Gemini + upsert en la base (GEMINI_API_KEY, DATABASE_URL)

Variables: GEMINI_API_KEY, GEMINI_EMBED_MODEL (gemini-embedding-001), EMBED_DIM (768), DATABASE_URL.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "db" / "seed"))
import planes  # noqa: E402

DIR_DOCS = RAIZ / "data" / "oficial" / "docs"
RUTA_PROFESORES = RAIZ / "data" / "oficial" / "unab_profesores.json"
RUTA_SALIDA = Path(__file__).resolve().parent / "salida_chunks.json"

TOKENS_POR_PALABRA = 1.35        # estimación para español
MAX_TOKENS = 800
SOLAPE_TOKENS = 120              # entre 100 y 150
MAX_PALABRAS = int(MAX_TOKENS / TOKENS_POR_PALABRA)
SOLAPE_PALABRAS = int(SOLAPE_TOKENS / TOKENS_POR_PALABRA)
URL_PROFESORES = "https://apolo.unab.edu.co/es/persons/"


def cargar_env() -> None:
    ruta = RAIZ / ".env"
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# --- carga de documentos --------------------------------------------------------------------
def docs_oficiales() -> list[dict]:
    docs = []
    if not DIR_DOCS.exists():
        return docs
    for f in sorted(DIR_DOCS.glob("*.txt")):
        lineas = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        if not lineas:
            continue
        url, cuerpo = None, lineas
        for i, l in enumerate(lineas[:5]):  # "Fuente: <url>", "URL: <url>" o la URL sola
            m = re.match(r"^\s*(?:fuente|url)\s*:\s*(https?://\S+)\s*$", l, re.I) or re.match(r"^\s*(https?://\S+)\s*$", l)
            if m:
                url, cuerpo = m.group(1), lineas[:i] + lineas[i + 1:]
                break
        if not url:  # sin URL en las primeras líneas: se toma todo como texto
            url = f"archivo:{f.name}"
        # Título: la primera línea con texto real (se saltan números de página y el nombre de la universidad,
        # como en la portada del Reglamento); si no sirve, el nombre del archivo.
        primera = next((l.strip() for l in cuerpo
                        if len(re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", "", l)) >= 4
                        and l.strip().lower() not in {"universidad autónoma de bucaramanga", "unab"}), "")
        titulo = primera.lstrip("# ").strip() if 0 < len(primera) <= 140 else f.stem.replace("_", " ")
        if titulo.isupper():
            titulo = f.stem.replace("_", " ").capitalize()
        docs.append(dict(titulo=titulo, fuente_url=url, tipo="documento_oficial", texto="\n".join(cuerpo)))
    return docs


def docs_planes(vistas: set[str] | None = None) -> list[dict]:
    """Planes de estudio de todos los programas (data/oficial/docs/planes/*.txt), un documento por plan.

    Cada archivo trae la URL de su fuente en las primeras líneas (la página del programa). Si esa URL ya la
    usa otro documento (por ejemplo, el texto de la página del programa), se le agrega #plan-<archivo> para
    que no se pisen en la base, porque los documentos se identifican por su URL.
    """
    carpeta = DIR_DOCS / "planes"
    if not carpeta.exists():
        return []
    docs, vistas = [], set(vistas or ())
    for f in sorted(carpeta.glob("*.txt")):
        lineas = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        if not any(l.strip() for l in lineas):
            continue
        url, cuerpo = None, lineas
        for i, l in enumerate(lineas[:6]):
            m = re.match(r"^\s*(?:fuente|url|documento)\s*:\s*(https?://\S+)\s*$", l, re.I) or re.match(r"^\s*(https?://\S+)\s*$", l)
            if m:
                url, cuerpo = m.group(1), lineas[:i] + lineas[i + 1:]
                break
        url = url or f"archivo:planes/{f.name}"
        if url in vistas:
            url = f"{url}#plan-{f.stem}"
        vistas.add(url)
        primera = next((l.strip().lstrip("# ").strip() for l in cuerpo if len(re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", "", l)) >= 4), "")
        titulo = primera if 0 < len(primera) <= 140 else "Plan de estudios " + f.stem.replace("-", " ")
        if not titulo.lower().startswith("plan"):
            titulo = f"Plan de estudios: {titulo}"
        # El total en el título ayuda a distinguir versiones del mismo programa (página frente a portal).
        m = re.search(r"Total de créditos del programa:\s*(\d+)", "\n".join(cuerpo[:8]))
        if m:
            titulo += f" ({m.group(1)} créditos)"
        docs.append(dict(titulo=titulo, fuente_url=url, tipo="plan_estudios", texto="\n".join(cuerpo)))
    return docs


def doc_plan() -> dict:
    """Plan de Ingeniería de Sistemas tal como está en la base de datos (cursos, créditos, tipo y semestre)."""
    plan, origen = planes.cargar_plan()
    total = sum(c[2] for c in plan)
    partes = [f"# Plan de estudios de {planes.PROGRAMA_NOMBRE} (UNAB), modalidad presencial",
              f"Total de créditos del programa: {total}. Duración: 8 semestres más la práctica en ingeniería de sistemas "
              f"(semestre {planes.SEMESTRES_PLAN}).",
              f"Fuente oficial: documento del plan de estudios publicado en la página del programa ({planes.PLAN_FUENTE_URL}).",
              "Es el mismo plan que usa la base de datos del asistente para calcular el avance, la proyección y los "
              "requisitos de cada estudiante. Las electivas que se repiten se numeran (I, II, III, IV).",
              "La UNAB no publica prerrequisitos entre cursos; los que usa el asistente son simulados."]
    for sem in sorted({c[0] for c in plan}):
        cursos = [c for c in plan if c[0] == sem]
        partes.append(f"## Semestre {sem} ({sum(c[2] for c in cursos)} créditos)")
        partes += [f"- {n}: {cr} créditos ({tipo})" for _, n, cr, tipo in cursos]
    return dict(titulo=f"Plan de estudios {planes.PROGRAMA_NOMBRE} (UNAB, {total} créditos, plan usado por el asistente)",
                fuente_url=planes.PLAN_DOCUMENTO_URL + "#plan-asistente", tipo="plan_estudios", texto="\n".join(partes))


def doc_profesores() -> dict | None:
    if not RUTA_PROFESORES.exists():
        return None
    datos = json.loads(RUTA_PROFESORES.read_text(encoding="utf-8"))
    if isinstance(datos, dict):
        datos = next((v for v in datos.values() if isinstance(v, list)), [])
    por_unidad: dict[str, list[str]] = {}
    for d in datos:
        if not isinstance(d, dict):
            continue
        nombre = next((d[k] for k in ("nombre", "name") if isinstance(d.get(k), str)), None)
        if not nombre:
            continue
        unidades = [u.get("nombre", "").strip() for u in d.get("unidades") or [] if isinstance(u, dict) and u.get("nombre")]
        if not unidades:
            unidades = [next((d[k] for k in ("unidad", "departamento", "unit", "facultad") if isinstance(d.get(k), str)), "Sin unidad")]
        linea = f"- {nombre}"
        if d.get("cargo"):
            linea += f" ({str(d['cargo'])[:120]})"
        if d.get("apolo_url"):
            linea += f": perfil {d['apolo_url']}"
        por_unidad.setdefault(unidades[0], []).append(linea)
    if not por_unidad:
        return None
    partes = ["# Profesores de la UNAB (resumen de APOLO)",
              "Perfiles públicos del portal APOLO (apolo.unab.edu.co), agrupados por unidad académica."]
    for u, lineas in sorted(por_unidad.items()):
        partes.append(f"## {u} ({len(lineas)} profesores)")
        partes += sorted(lineas)
    return dict(titulo="Profesores de la UNAB (APOLO)", fuente_url=URL_PROFESORES, tipo="profesores", texto="\n".join(partes))


# --- fragmentación ----------------------------------------------------------------------------
def es_encabezado(l: str) -> bool:
    s = l.strip()
    if not s or len(s) > 90:
        return False
    return (s.startswith("#") or s.endswith(":") or (s.isupper() and len(s) > 3)
            or bool(re.match(r"^(art[ií]culo|cap[ií]tulo|t[ií]tulo|secci[oó]n|semestre)\b", s, re.I)))


def n_palabras(t: str) -> int:
    return len(t.split())


def fragmentar(texto: str) -> list[dict]:
    """Divide en fragmentos de ~800 tokens con solape de ~120 y antepone el encabezado vigente."""
    secciones: list[tuple[str, list[str]]] = [("", [])]
    for linea in texto.splitlines():
        if es_encabezado(linea):
            secciones.append((linea.strip().lstrip("# ").strip(), []))
        elif linea.strip():
            secciones[-1][1].append(linea.strip())
    chunks = []
    for encabezado, lineas in secciones:
        if not lineas:
            continue
        # Líneas muy largas se parten por palabras para no exceder el máximo.
        trozos = []
        for l in lineas:
            p = l.split()
            if len(p) <= MAX_PALABRAS:
                trozos.append(l)
            else:
                paso = MAX_PALABRAS - SOLAPE_PALABRAS
                trozos += [" ".join(p[i:i + MAX_PALABRAS]) for i in range(0, len(p), paso)]
        presupuesto = MAX_PALABRAS - n_palabras(encabezado)
        actual: list[str] = []
        cuenta = 0
        for t in trozos:
            w = n_palabras(t)
            if actual and cuenta + w > presupuesto:
                chunks.append((encabezado, list(actual)))
                # solape: las últimas líneas hasta ~SOLAPE_PALABRAS
                cola, c = [], 0
                for prev in reversed(actual):
                    if c + n_palabras(prev) > SOLAPE_PALABRAS + 30 and cola:
                        break
                    cola.insert(0, prev)
                    c += n_palabras(prev)
                actual, cuenta = cola, c
            actual.append(t)
            cuenta += w
        if actual and (not chunks or chunks[-1][1] != actual):
            chunks.append((encabezado, actual))
    salida = []
    for i, (enc, ls) in enumerate(chunks):
        cuerpo = "\n".join(ls)
        contenido = f"{enc}\n{cuerpo}" if enc else cuerpo
        salida.append(dict(indice=i, contenido=contenido, metadata=dict(encabezado=enc, indice=i),
                           tokens_aprox=math.ceil(n_palabras(contenido) * TOKENS_POR_PALABRA)))
    return salida


def preparar() -> list[dict]:
    oficiales = docs_oficiales()
    docs = oficiales + docs_planes({d["fuente_url"] for d in oficiales})
    # El plan detallado de Ingeniería de Sistemas (con tipo de curso) se mantiene aparte.
    docs.append(doc_plan())
    prof = doc_profesores()
    if prof:
        docs.append(prof)
    for d in docs:
        d["chunks"] = fragmentar(d.pop("texto"))
        for c in d["chunks"]:
            c["metadata"].update(titulo=d["titulo"], fuente_url=d["fuente_url"], tipo=d["tipo"])
    return docs


# --- Gemini + base de datos -------------------------------------------------------------------
def embedding(texto: str, clave: str, modelo: str, dim: int) -> list[float]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:embedContent"
    cuerpo = json.dumps({"model": f"models/{modelo}", "content": {"parts": [{"text": texto}]},
                         "taskType": "RETRIEVAL_DOCUMENT", "outputDimensionality": dim}).encode()
    for intento in range(6):
        req = urllib.request.Request(url, data=cuerpo, method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": clave})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                vec = json.load(r)["embedding"]["values"]
            norma = math.sqrt(sum(x * x for x in vec)) or 1.0  # con dimensión reducida hay que normalizar
            return [x / norma for x in vec]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and intento < 5:
                time.sleep(2 ** intento)
                continue
            raise RuntimeError(f"Gemini respondió {e.code}: {e.read().decode(errors='ignore')[:300]}") from e
    raise RuntimeError("Gemini no respondió tras varios intentos")


def cargar_en_base(docs: list[dict]) -> None:
    import psycopg

    clave = os.environ.get("GEMINI_API_KEY")
    url_db = os.environ.get("DATABASE_URL")
    if not clave or not url_db:
        sys.exit("Faltan GEMINI_API_KEY y/o DATABASE_URL (o usa --dry-run).")
    modelo = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    dim = int(os.environ.get("EMBED_DIM", "768"))
    with psycopg.connect(url_db, prepare_threshold=None) as conn:  # compatible con el pooler de Supabase
        for d in docs:
            doc_id = conn.execute(
                """insert into documentos (titulo, fuente_url, tipo) values (%s, %s, %s)
                   on conflict (fuente_url) do update set titulo = excluded.titulo, tipo = excluded.tipo
                   returning id""", (d["titulo"], d["fuente_url"], d["tipo"])).fetchone()[0]
            conn.execute("delete from documentos_fragmentos where documento_id = %s", (doc_id,))
            for c in d["chunks"]:
                vec = embedding(c["contenido"], clave, modelo, dim)
                conn.execute(
                    "insert into documentos_fragmentos (documento_id, contenido, metadata, embedding) values (%s, %s, %s::jsonb, %s::vector)",
                    (doc_id, c["contenido"], json.dumps(c["metadata"], ensure_ascii=False), "[" + ",".join(f"{x:.7f}" for x in vec) + "]"))
                time.sleep(0.7)  # respeta el límite gratuito (~100 solicitudes por minuto)
            conn.commit()
            print(f"  {d['titulo']}: {len(d['chunks'])} fragmentos")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="solo fragmenta y escribe rag/salida_chunks.json")
    ap.add_argument("--solo", help="carga solo los documentos cuyo título o tipo contenga este texto (p. ej. profesores)")
    args = ap.parse_args()
    cargar_env()
    docs = preparar()
    if args.solo:
        docs = [d for d in docs if args.solo.lower() in (d["titulo"] + " " + d["tipo"]).lower()]
    total = sum(len(d["chunks"]) for d in docs)
    if args.dry_run:
        RUTA_SALIDA.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{len(docs)} documentos, {total} fragmentos -> {RUTA_SALIDA.relative_to(RAIZ)}")
        return 0
    print(f"Ingesta de {len(docs)} documentos ({total} fragmentos)")
    cargar_en_base(docs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
