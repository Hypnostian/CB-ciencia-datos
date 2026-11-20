"""Experimento para justificar el tamaño de los fragmentos (chunks) y el solape del RAG.

Fragmenta los documentos oficiales principales con varias configuraciones (tamaño máximo y solape en tokens),
calcula los embeddings con Gemini (gemini-embedding-001, 768 dimensiones) y mide, con un conjunto fijo de 25
preguntas típicas de estudiantes, si el fragmento correcto aparece entre los primeros resultados:

  - Acierto@1 y Acierto@3: el documento correcto sale de primero / entre los tres primeros.
  - Evidencia@3: algún fragmento del top 3 trae la frase que responde (no solo el documento correcto).
  - MRR: promedio de 1/posición del primer fragmento correcto.
  - Margen: similitud del primer fragmento correcto menos la del mejor fragmento de otro documento (cuánto se
    separa la respuesta correcta de la competencia).
  - Contexto top 5: tokens que recibiría el agente con los 5 fragmentos recuperados (costo y latencia).
  - Secciones partidas: artículos o secciones que no caben en un fragmento y quedan divididos.

Todo se hace en memoria (no toca la base). El plan de Ingeniería de Sistemas Virtual se incluye a propósito como
distractor: es un plan parecido pero de otro programa.

Uso (desde la raíz del proyecto; lee GEMINI_API_KEY y DATABASE_URL del .env):
    python rag/evaluar_chunks.py              # estructura + índice en producción (pocas llamadas a la API)
    python rag/evaluar_chunks.py --comparar   # además recalcula la comparación de tamaños (~700 embeddings)
Los embeddings se guardan en rag/.cache_embeddings.json (ignorado por git) para no recalcularlos.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingesta  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = Path(__file__).with_name("evaluacion_chunks.json")
CACHE = Path(__file__).with_name(".cache_embeddings.json")
CONFIGURACIONES = [(300, 45), (800, 0), (800, 120), (1500, 225)]  # (tokens máximos, tokens de solape)
ELEGIDA = (800, 120)

# (pregunta, documentos válidos, texto que debe aparecer en el fragmento recuperado)
PREGUNTAS = [
    ("¿Cuándo un estudiante queda en prueba académica?", ["reglamento"], "prueba academica cuando"),
    ("¿Puedo cancelar materias después de matricularlas?", ["reglamento"], "cancelacion ordinaria"),
    ("¿Cómo solicito el reintegro a la universidad?", ["reglamento"], "reintegro"),
    ("¿Cómo se calcula el promedio general acumulado?", ["reglamento"], "calculo del ppa y pga"),
    ("¿Qué es una homologación de cursos?", ["reglamento"], "homologacion es un proceso"),
    ("¿Qué son las validaciones de un curso y quién las puede pedir?", ["reglamento"], "validaciones"),
    ("¿Cuántos créditos tiene el plan de Ingeniería de Sistemas?", ["plan_sistemas", "plan_asistente"], "151"),
    ("¿Qué materias se ven en cuarto semestre de Ingeniería de Sistemas?", ["plan_sistemas", "plan_asistente"], "base de datos i"),
    ("¿En qué semestre se hace la práctica en ingeniería de sistemas?", ["plan_sistemas", "plan_asistente"], "practica en ingenieria de sistemas"),
    ("¿Cuánto cuesta la matrícula de primer ingreso de Ingeniería de Sistemas?", ["programa_ingenieria_de_sistemas"], "7.554.880"),
    ("¿Qué título otorga el programa de Ingeniería de Sistemas?", ["programa_ingenieria_de_sistemas"], "ingeniero/a de sistemas"),
    ("¿Cómo funciona la formación en competencias digitales?", ["ccd_asi_funciona"], "rutas"),
    ("¿Cuándo son las pruebas de competencias digitales para sexto semestre?", ["ccd_pruebas_desde_sexto_semestre"], "sexto"),
    ("¿Puedo homologar los cursos de competencias digitales si ya vi Informática?", ["ccd_homologacion"], "informatica"),
    ("¿Qué cursos vacacionales intensivos de competencias digitales hay?", ["ccd_cursos_vacacionales_intensivos", "ccd_cursos_vacacionales_proximamente"], "vacacional"),
    ("¿Qué es la prueba diagnóstica de competencias digitales de primer ingreso virtual?", ["ccd_prueba_diagnostica_primer_ingreso_virtual"], "diagnostica"),
    ("¿Cuáles son los pasos para matricularme en pregrado?", ["matricula_pregrado"], "matricula"),
    # Preguntas de detalle, con otras palabras que las del documento
    ("¿Qué promedio necesito para estudiar dos carreras al tiempo?", ["reglamento"], "3.50"),
    ("¿Cuántas veces puedo cancelar la misma materia?", ["reglamento"], "hasta dos veces"),
    ("¿Con qué nota final puedo habilitar una materia?", ["reglamento"], "dos, punto, cinco (2.5)"),
    ("¿Cuánto pesa la prueba de habilitación en la nota definitiva?", ["reglamento"], "cuarenta por ciento"),
    ("Si no presenté un parcial, ¿puedo pedir un examen supletorio?", ["reglamento"], "supletorias"),
    ("¿Cuánto vale el cobro de competencias digitales en Ingeniería de Sistemas?", ["programa_ingenieria_de_sistemas"], "362.550"),
    ("¿Qué materias tiene el primer semestre de Ingeniería de Sistemas virtual?", ["plan_sistemas_virtual"], "ideando la ingenieria"),
    ("¿Cuántos créditos vale Proyectos en ingeniería de sistemas II?", ["plan_sistemas", "plan_asistente"], "proyectos en ingenieria de sistemas ii"),
]


def normalizar(t: str) -> str:
    t = "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")
    return " ".join(t.split())


def corpus() -> list[dict]:
    """Documentos oficiales de data/oficial/docs, los dos planes de Sistemas (presencial y virtual) y el del asistente."""
    docs = []
    for d, f in zip(ingesta.docs_oficiales(), sorted((RAIZ / "data/oficial/docs").glob("*.txt"))):
        d["id"] = f.stem.split("_estudiantil")[0] if "reglamento" in f.stem else f.stem
        docs.append(d)
    for d in ingesta.docs_planes({d["fuente_url"] for d in docs}):
        if "ingenieria-de-sistemas" in d["fuente_url"]:
            d["id"] = "plan_sistemas_virtual" if "virtual" in d["fuente_url"] else "plan_sistemas"
            docs.append(d)
    d = ingesta.doc_plan()
    d["id"] = "plan_asistente"
    docs.append(d)
    return docs


def embeddings(textos: list[str], tarea: str) -> list[list[float]]:
    """batchEmbedContents de Gemini en lotes de 50, con vectores normalizados y caché en disco."""
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    clave = lambda t: hashlib.sha1(f"{tarea}|{t}".encode()).hexdigest()  # noqa: E731
    faltan = [t for t in dict.fromkeys(textos) if clave(t) not in cache]
    for i in range(0, len(faltan), 20):  # lotes pequeños y caché por lote: respeta el límite por minuto
        lote = faltan[i:i + 20]
        for t, v in zip(lote, _calcular(lote, tarea)):
            cache[clave(t)] = [round(x, 6) for x in v]
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
        time.sleep(4)
    return [cache[clave(t)] for t in textos]


def _calcular(textos: list[str], tarea: str) -> list[list[float]]:
    modelo = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:batchEmbedContents"
    salida = []
    for i in range(0, len(textos), 50):
        lote = [{"model": f"models/{modelo}", "content": {"parts": [{"text": t}]}, "taskType": tarea,
                 "outputDimensionality": 768} for t in textos[i:i + 50]]
        for intento in range(6):
            req = urllib.request.Request(url, data=json.dumps({"requests": lote}).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    vecs = [e["values"] for e in json.load(r)["embeddings"]]
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 503) and intento < 5:
                    time.sleep(15 * 2 ** intento)  # 15 s, 30 s, 1 min, 2 min, 4 min
                    continue
                raise
        for v in vecs:
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            salida.append([x / n for x in v])
        time.sleep(1.5)
    return salida


def coseno(a, b):
    return sum(x * y for x, y in zip(a, b))


def evaluar(fragmentos: list[dict], vec_preguntas) -> dict:
    a1 = a3 = ev3 = 0
    rr = margen = contexto = 0.0
    detalle = []
    for (pregunta, validos, evidencia), q in zip(PREGUNTAS, vec_preguntas):
        orden = sorted(fragmentos, key=lambda f: -coseno(q, f["vec"]))
        correcto = [f["doc"] in validos for f in orden]
        pos = next((i + 1 for i, c in enumerate(correcto) if c), None)
        a1 += correcto[0]
        a3 += any(correcto[:3])
        rr += 1 / pos if pos else 0
        con_evidencia = any(f["doc"] in validos and normalizar(evidencia) in normalizar(f["texto"]) for f in orden[:3])
        ev3 += con_evidencia
        mejor_ok = next((coseno(q, f["vec"]) for f in orden if f["doc"] in validos), 0.0)
        mejor_otro = next((coseno(q, f["vec"]) for f in orden if f["doc"] not in validos), 0.0)
        margen += mejor_ok - mejor_otro
        contexto += sum(f["tokens"] for f in orden[:5])
        detalle.append({"pregunta": pregunta, "posicion": pos, "evidencia_top3": con_evidencia,
                        "top1": orden[0]["doc"], "similitud_top1": round(coseno(q, orden[0]["vec"]), 3)})
    n = len(PREGUNTAS)
    return {"acierto@1": round(a1 / n, 3), "acierto@3": round(a3 / n, 3), "evidencia@3": round(ev3 / n, 3),
            "mrr": round(rr / n, 3), "margen": round(margen / n, 3), "contexto_top5_tokens": round(contexto / n),
            "detalle": detalle}


def fragmentos_de(docs: list[dict], max_tok: int, solape: int) -> list[dict]:
    ingesta.MAX_PALABRAS = int(max_tok / ingesta.TOKENS_POR_PALABRA)
    ingesta.SOLAPE_PALABRAS = int(solape / ingesta.TOKENS_POR_PALABRA)
    salida = [{"doc": d["id"], "texto": c["contenido"], "tokens": c["tokens_aprox"], "seccion": c["metadata"]["encabezado"]}
              for d in docs for c in ingesta.fragmentar(d["texto"])]
    ingesta.MAX_PALABRAS = int(ingesta.MAX_TOKENS / ingesta.TOKENS_POR_PALABRA)
    ingesta.SOLAPE_PALABRAS = int(ingesta.SOLAPE_TOKENS / ingesta.TOKENS_POR_PALABRA)
    return salida


def estructura(docs: list[dict]) -> list[dict]:
    """Métricas que no necesitan la API: fragmentos, tamaño, secciones partidas y peor caso del contexto top 5."""
    filas = []
    for max_tok, solape in CONFIGURACIONES:
        fr = fragmentos_de(docs, max_tok, solape)
        por_seccion: dict = {}
        for f in fr:
            por_seccion[(f["doc"], f["seccion"])] = por_seccion.get((f["doc"], f["seccion"]), 0) + 1
        tokens = sorted((f["tokens"] for f in fr), reverse=True)
        filas.append({"max_tokens": max_tok, "solape_tokens": solape, "fragmentos": len(fr),
                      "tokens_promedio": round(sum(tokens) / len(tokens)), "tokens_maximo": tokens[0],
                      "secciones_partidas": sum(1 for k, v in por_seccion.items() if v > 1 and k[1]),
                      "contexto_top5_peor_caso": sum(tokens[:5])})
    return filas


def produccion(docs: list[dict], vec_preguntas) -> dict:
    """Evalúa las preguntas contra el índice real de Supabase (145 documentos) con match_documentos, como n8n."""
    import psycopg
    url = {d["id"]: d["fuente_url"] for d in docs}
    a1 = a3 = ev3 = 0
    rr = sim = 0.0
    detalle = []
    with psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None) as conn:
        total = conn.execute("select count(*) from documentos_fragmentos").fetchone()[0]
        for (pregunta, validos, evidencia), q in zip(PREGUNTAS, vec_preguntas):
            filas = conn.execute("select fuente_url, contenido, similitud from match_documentos(%s::vector, 5)",
                                 ("[" + ",".join(f"{x:.6f}" for x in q) + "]",)).fetchall()
            ok_urls = {url[v] for v in validos}
            correcto = [f[0] in ok_urls for f in filas]
            pos = next((i + 1 for i, c in enumerate(correcto) if c), None)
            a1 += correcto[0]
            a3 += any(correcto[:3])
            rr += 1 / pos if pos else 0
            sim += filas[0][2]
            con_ev = any(f[0] in ok_urls and normalizar(evidencia) in normalizar(f[1]) for f in filas[:3])
            ev3 += con_ev
            detalle.append({"pregunta": pregunta, "posicion": pos, "evidencia_top3": con_ev,
                            "similitud_top1": round(filas[0][2], 3)})
    n = len(PREGUNTAS)
    return {"fragmentos_indice": total, "preguntas": n, "acierto@1": round(a1 / n, 3), "acierto@3": round(a3 / n, 3),
            "evidencia@3": round(ev3 / n, 3), "mrr": round(rr / n, 3), "similitud_top1_promedio": round(sim / n, 3),
            "detalle": detalle}


def comparar(docs: list[dict], vec_preguntas) -> dict:
    """Compara las configuraciones calculando los embeddings de todos los fragmentos (costoso: ~700 llamadas)."""
    resultados = []
    for max_tok, solape in CONFIGURACIONES:
        fr = fragmentos_de(docs, max_tok, solape)
        for f, v in zip(fr, embeddings([f["texto"] for f in fr], "RETRIEVAL_DOCUMENT")):
            f["vec"] = v
        resultados.append({"max_tokens": max_tok, "solape_tokens": solape, "fragmentos": len(fr), **evaluar(fr, vec_preguntas)})
    return {"preguntas": len(PREGUNTAS), "resultados": resultados}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ingesta.cargar_env()
    docs = corpus()
    previo = json.loads(SALIDA.read_text(encoding="utf-8")) if SALIDA.exists() else {}
    print(f"Corpus del experimento: {len(docs)} documentos oficiales (incluye el plan de Sistemas Virtual como distractor)")
    vec_preguntas = embeddings([p for p, _, _ in PREGUNTAS], "RETRIEVAL_QUERY")

    est = estructura(docs)
    print("\n1) Estructura de los fragmentos (sin API)")
    print("   máx/solape  fragmentos  tokens prom.  tokens máx.  secciones partidas  contexto top 5 (peor caso)")
    for e in est:
        print(f"   {e['max_tokens']:>4}/{e['solape_tokens']:<5}  {e['fragmentos']:>10}  {e['tokens_promedio']:>12}  "
              f"{e['tokens_maximo']:>11}  {e['secciones_partidas']:>18}  {e['contexto_top5_peor_caso']:>14}")

    comp = previo.get("comparacion")
    if comp is None and "resultados" in previo:
        comp = {"preguntas": previo["preguntas"], "resultados": previo["resultados"]}
    if "--comparar" in sys.argv:
        comp = comparar(docs, vec_preguntas)
    if comp:
        print(f"\n2) Recuperación por configuración ({comp['preguntas']} preguntas, embeddings de cada fragmento)")
        for r in comp["resultados"]:
            print(f"   {r['max_tokens']:>4}/{r['solape_tokens']:<5}  acierto@1 {r['acierto@1']:.2f}  "
                  f"acierto@3 {r['acierto@3']:.2f}  evidencia@3 {r['evidencia@3']:.2f}  MRR {r['mrr']:.2f}")

    prod = produccion(docs, vec_preguntas)
    print(f"\n3) Índice en producción (Supabase, {prod['fragmentos_indice']} fragmentos de 145 documentos, 800/120, "
          f"top 5 como n8n)")
    print(f"   {prod['preguntas']} preguntas: acierto@1 {prod['acierto@1']:.2f}, acierto@3 {prod['acierto@3']:.2f}, "
          f"evidencia@3 {prod['evidencia@3']:.2f}, MRR {prod['mrr']:.2f}, "
          f"similitud top 1 promedio {prod['similitud_top1_promedio']:.2f}")
    for d in prod["detalle"]:
        if d["posicion"] != 1 or not d["evidencia_top3"]:
            ev = "sí" if d["evidencia_top3"] else "no"
            print(f"   - {d['pregunta']} -> posición {d['posicion']}, evidencia en top 3: {ev}")

    SALIDA.write_text(json.dumps({"modelo": os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001"), "dimensiones": 768,
                                  "elegida": {"max_tokens": ELEGIDA[0], "solape_tokens": ELEGIDA[1]}, "estructura": est,
                                  "comparacion": comp, "produccion": prod}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResultados en {SALIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
