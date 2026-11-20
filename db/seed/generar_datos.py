"""Genera datos SINTÉTICOS (determinísticos, semilla 2026) que simulan Banner-Cosmos.

Uso (desde la raíz del proyecto):
    python db/seed/generar_datos.py

Salida:
    data/sintetica/*.csv     una tabla por archivo
    db/seed/seed.sql         INSERTs para pegar en el SQL Editor de Supabase

Solo son sintéticos: estudiantes, matrículas, notas, NRC, docentes de las secciones e historial CCD.
Los cursos del plan (documento oficial de Ingeniería de Sistemas, 151 créditos), los nombres de los cursos CCD
y los profesores de APOLO son datos oficiales.
Los prerrequisitos NO son publicados por UNAB: se simulan (es_simulado = true).

Los 120 estudiantes (código, nombre, perfil académico, periodo de ingreso y, si aplica, periodo de retiro) están
fijos en db/seed/estudiantes_base.csv, así los perfiles no cambian aunque cambie el plan. Si el archivo no existe,
se crea uno nuevo con las mismas reglas (Faker es_CO y la distribución de INGRESOS).
"""
from __future__ import annotations

import csv
import json
import math
import random
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planes  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "mcp-server"))
from app import registro  # noqa: E402  (misma regla de competencias y horas libres que el servidor MCP)

SEMILLA = 2026
RAIZ = Path(__file__).resolve().parents[2]
DIR_CSV = RAIZ / "data" / "sintetica"
RUTA_SEED_SQL = RAIZ / "db" / "seed" / "seed.sql"
RUTA_CALENDARIO = RAIZ / "data" / "calendario_academico.csv"
RUTA_PROFESORES = RAIZ / "data" / "oficial" / "unab_profesores.json"
RUTA_ROSTER = RAIZ / "db" / "seed" / "estudiantes_base.csv"
DIR_DOCS = RAIZ / "data" / "oficial" / "docs"

N_ESTUDIANTES = 120
PERIODO_ACTUAL = "2026-2"
PERIODOS = [f"{a}-{s}" for a in range(2023, 2027) for s in (1, 2)]  # 2023-1 ... 2026-2
NOTA_APROBACION = 3.0

# Estudiantes fijos para demostraciones (código, perfil, periodo de ingreso).
DEMO = [
    ("U00100001", "normal", "2024-2"),      # semestre 5, avance regular
    ("U00100002", "rezagado", "2023-2"),    # semestre 7 nominal, con materias perdidas
    ("U00100003", "avanzado", "2023-2"),    # va adelantado
    ("U00100004", "normal", "2026-2"),      # estudiante nuevo, primer semestre
]
# Distribución de ingresos (periodo -> cantidad) para completar 120 estudiantes.
INGRESOS = {"2023-1": 19, "2023-2": 15, "2024-1": 19, "2024-2": 15, "2025-1": 17, "2025-2": 15, "2026-1": 12, "2026-2": 8}

CURSOS_CCD = [  # (ruta, nombre oficial, obligatorio)
    (1, "Interacción Digital", True),
    (2, "Habilidades en Analítica Digital", False),
    (2, "Marca Personal Digital", False),
    (2, "Creación de Contenidos Digitales", False),
    (3, "IA Generativa", False),
    (3, "Marco Legal Digital", False),
    (3, "Cuidado y Bienestar Digital", False),
]
DESC_CCD = {
    1: "Ruta 1 del Centro de Competencias Digitales (obligatoria).",
    2: "Ruta 2 del Centro de Competencias Digitales (se elige un curso de la ruta).",
    3: "Ruta 3 del Centro de Competencias Digitales (se elige un curso de la ruta).",
}

PERFILES = {
    # carga objetivo (créditos), media de nota, probabilidad de cancelar un curso
    "normal": dict(cargas=[15, 16, 17, 18], mu=(3.95, 0.3), cancela=0.02),
    "rezagado": dict(cargas=[9, 10, 12, 13], mu=(3.3, 0.25), cancela=0.06),
    "avanzado": dict(cargas=[18, 19, 20], mu=(4.25, 0.2), cancela=0.01),
    "irregular": dict(cargas=[6, 9, 12, 15, 16], mu=(3.65, 0.35), cancela=0.12),
}

HORARIOS = [
    "Lun-Mié 07:00-09:00", "Lun-Mié 09:00-11:00", "Lun-Mié 11:00-13:00", "Lun-Mié 14:00-16:00",
    "Mar-Jue 07:00-09:00", "Mar-Jue 09:00-11:00", "Mar-Jue 11:00-13:00", "Mar-Jue 14:00-16:00",
    "Vie 07:00-11:00", "Vie 14:00-18:00", "Lun-Mié 18:00-20:00", "Mar-Jue 18:00-20:00",
]


def fechas_periodo(pid: str) -> tuple[date, date]:
    a, s = pid.split("-")
    a = int(a)
    return (date(a, 1, 26), date(a, 5, 30)) if s == "1" else (date(a, 8, 3), date(a, 12, 5))


def crear_roster(rnd: random.Random, fake: Faker) -> list[dict]:
    """Roster nuevo de 120 estudiantes (solo se usa si no existe db/seed/estudiantes_base.csv)."""
    filas = [dict(codigo=c, perfil=p, periodo_ingreso=i) for c, p, i in DEMO]
    usados = {f["codigo"] for f in filas}
    cuenta = dict(INGRESOS)
    for _, _, ing in DEMO:
        cuenta[ing] -= 1
    for ing, n in cuenta.items():
        for _ in range(n):
            cod = f"U00{rnd.randint(100000, 999999)}"
            while cod in usados:
                cod = f"U00{rnd.randint(100000, 999999)}"
            usados.add(cod)
            perfil = "normal" if ing == PERIODO_ACTUAL else                 rnd.choices(["normal", "rezagado", "avanzado", "irregular"], weights=[60, 20, 12, 8])[0]
            filas.append(dict(codigo=cod, perfil=perfil, periodo_ingreso=ing))
    candidatos = [f for f in filas if f["periodo_ingreso"] in ("2023-1", "2023-2", "2024-1") and f["codigo"] not in usados_demo()]
    retirados = {f["codigo"] for f in rnd.sample(candidatos, 4)}
    for f in filas:
        pila = fake.first_name_female if rnd.random() < 0.45 else fake.first_name_male
        f["nombres"] = pila() + (" " + pila() if rnd.random() < 0.35 else "")
        f["apellidos"] = f"{fake.last_name()} {fake.last_name()}"
        idx = PERIODOS.index(f["periodo_ingreso"])
        f["periodo_retiro"] = PERIODOS[rnd.randint(idx + 1, len(PERIODOS) - 2)] if f["codigo"] in retirados else ""
    with open(RUTA_ROSTER, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["codigo", "nombres", "apellidos", "periodo_ingreso", "perfil", "periodo_retiro"])
        w.writeheader()
        w.writerows(filas)
    return filas


def usados_demo() -> set[str]:
    return {d[0] for d in DEMO}


def leer_roster(rnd: random.Random, fake: Faker) -> list[dict]:
    if not RUTA_ROSTER.exists():
        return crear_roster(rnd, fake)
    with open(RUTA_ROSTER, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def generar() -> dict:
    rnd = random.Random(SEMILLA)
    fake = Faker("es_CO")
    Faker.seed(SEMILLA)
    fake.seed_instance(SEMILLA)

    # --- programa, cursos, prerrequisitos -------------------------------------------------
    plan, origen_plan = planes.cargar_plan()
    programa = dict(id=1, codigo=planes.PROGRAMA_CODIGO, nombre=planes.PROGRAMA_NOMBRE,
                    total_creditos=sum(c[2] for c in plan), fuente_url=planes.PLAN_FUENTE_URL)
    cursos = []
    contador_sem: dict[int, int] = {}
    for sem, nombre, cred, tipo in plan:
        contador_sem[sem] = contador_sem.get(sem, 0) + 1
        cursos.append(dict(id=len(cursos) + 1, programa_id=1, codigo=planes.codigo_curso(sem, contador_sem[sem]),
                           nombre=nombre, creditos=cred, semestre_plan=sem, tipo=tipo, es_oficial=True))
    id_por_nombre = {c["nombre"]: c["id"] for c in cursos}
    curso_por_id = {c["id"]: c for c in cursos}
    prerreq = [dict(curso_id=id_por_nombre[a], requisito_id=id_por_nombre[b], es_simulado=True)
               for a, b in planes.prerrequisitos_para([(c["semestre_plan"], c["nombre"], c["creditos"], c["tipo"]) for c in cursos])]
    reqs_de: dict[int, list[int]] = {}
    for p in prerreq:
        reqs_de.setdefault(p["curso_id"], []).append(p["requisito_id"])

    # --- periodos --------------------------------------------------------------------------
    periodos = []
    for pid in PERIODOS:
        ini, fin = fechas_periodo(pid)
        periodos.append(dict(id=pid, nombre=f"Periodo {pid} (simulado)", fecha_inicio=ini, fecha_fin=fin,
                             actual=(pid == PERIODO_ACTUAL)))

    # --- secciones (NRC únicos de 5 dígitos, docentes sintéticos) -------------------------
    nrcs = rnd.sample(range(10000, 100000), len(cursos) * len(PERIODOS) * 3)
    docentes = sorted({fake.name() for _ in range(80)})[:48]
    secciones = []
    sec_por = {}  # (curso_id, periodo) -> [seccion]
    for c in cursos:
        for pid in PERIODOS:
            n = rnd.choice([2, 3]) if c["semestre_plan"] <= 2 else rnd.choice([1, 2])
            for _ in range(n):
                s = dict(nrc=f"{nrcs.pop():05d}", curso_id=c["id"], periodo_id=pid, docente=rnd.choice(docentes),
                         horario=rnd.choice(HORARIOS), cupo=rnd.choice([25, 30, 35, 40]))
                secciones.append(s)
                sec_por.setdefault((c["id"], pid), []).append(s)
    ocupacion: dict[str, int] = {}

    # --- cursos CCD ------------------------------------------------------------------------
    fuente_ccd = "https://unab.edu.co/asi-funciona-la-formacion-en-competencias-digitales-de-la-unab/"
    if DIR_DOCS.exists():
        for f in sorted(DIR_DOCS.glob("*.txt")):
            if "ccd" in f.name.lower() or "competencias" in f.name.lower():
                for l in f.read_text(encoding="utf-8", errors="ignore").splitlines()[:5]:
                    m = re.match(r"^\s*(?:(?:fuente|url)\s*:\s*)?(https?://\S+)\s*$", l, re.I)
                    if m:
                        fuente_ccd = m.group(1)
                        break
    cursos_ccd = [dict(id=i + 1, ruta=r, nombre=n, obligatorio=o, descripcion=DESC_CCD[r], fuente_url=fuente_ccd)
                  for i, (r, n, o) in enumerate(CURSOS_CCD)]

    # --- estudiantes (roster fijo) + simulación académica sobre el plan oficial -------------
    roster = {f["codigo"]: f for f in leer_roster(rnd, fake)}
    assert len(roster) == N_ESTUDIANTES, len(roster)
    inactivos = {c for c, f in roster.items() if f["periodo_retiro"]}

    estudiantes, matriculas, historial_ccd = [], [], []
    id_matricula = 0
    id_hist = 0

    for f in sorted(roster.values(), key=lambda x: (x["periodo_ingreso"], x["codigo"])):
        cod, perfil_nombre, ing = f["codigo"], f["perfil"], f["periodo_ingreso"]
        perfil = PERFILES[perfil_nombre]
        mu = rnd.gauss(*perfil["mu"])
        idx_ing = PERIODOS.index(ing)
        idx_stop = PERIODOS.index(f["periodo_retiro"]) if cod in inactivos else len(PERIODOS) - 1
        aprobados: set[int] = set()
        fallidos: set[int] = set()
        periodos_cursados = 0
        graduado = False
        for idx in range(idx_ing, idx_stop + 1):
            pid = PERIODOS[idx]
            pendientes = [c for c in cursos if c["id"] not in aprobados]
            if not pendientes:
                graduado = True
                break
            objetivo = rnd.choice(perfil["cargas"])
            elegibles = [c for c in pendientes if all(r in aprobados for r in reqs_de.get(c["id"], []))]
            elegibles.sort(key=lambda c: (c["id"] not in fallidos, c["semestre_plan"], c["id"]))
            carga, elegidos = 0, []
            for c in elegibles:
                if carga + c["creditos"] <= objetivo:
                    elegidos.append(c)
                    carga += c["creditos"]
            if elegidos:
                periodos_cursados += 1
            nuevos_aprobados = set()
            for c in elegidos:
                opciones = sec_por[(c["id"], pid)]
                libres = [s for s in opciones if ocupacion.get(s["nrc"], 0) < s["cupo"]] or opciones
                sec = rnd.choice(libres)
                ocupacion[sec["nrc"]] = ocupacion.get(sec["nrc"], 0) + 1
                id_matricula += 1
                m = dict(id=id_matricula, estudiante_codigo=cod, nrc=sec["nrc"], periodo_id=pid, estado="", nota_final=None)
                if pid == PERIODO_ACTUAL:
                    m["estado"] = "inscrita"
                elif rnd.random() < perfil["cancela"]:
                    m["estado"] = "cancelada"
                else:
                    nota = round(min(5.0, max(0.0, rnd.gauss(mu, 0.55))), 1)
                    m["estado"], m["nota_final"] = "finalizada", nota
                    if nota >= NOTA_APROBACION:
                        nuevos_aprobados.add(c["id"])
                        fallidos.discard(c["id"])
                    else:
                        fallidos.add(c["id"])
                matriculas.append(m)
            aprobados |= nuevos_aprobados
        total_aprob = sum(curso_por_id[i]["creditos"] for i in aprobados)
        if total_aprob >= programa["total_creditos"]:
            graduado = True
        estado = "graduado" if graduado else ("inactivo" if cod in inactivos else "activo")
        n_sem = max(1, min(planes.SEMESTRES_PLAN, periodos_cursados))
        ini_ing = fechas_periodo(ing)[0]
        estudiantes.append(dict(
            codigo=cod, nombres=f["nombres"], apellidos=f["apellidos"], correo=f"{cod.lower()}@demo.unab.local",
            programa_id=1, semestre_actual=n_sem, estado=estado, fecha_ingreso=ini_ing,
            _perfil=perfil_nombre, _idx_ing=idx_ing, _idx_stop=idx_stop, _n=periodos_cursados))

    # --- historial CCD ---------------------------------------------------------------------
    def fecha_en(pid: str, aprobado: bool) -> date:
        ini, fin = fechas_periodo(pid)
        return fin - timedelta(days=rnd.randint(2, 20)) if aprobado else ini + timedelta(days=rnd.randint(20, 70))

    for e in estudiantes:
        if e["estado"] == "inactivo" and e["_n"] < 2:
            continue
        i0, i1 = e["_idx_ing"], e["_idx_stop"]
        periodos_alumno = PERIODOS[i0:i1 + 1]
        n = len(periodos_alumno)

        def agregar(curso_id: int, pid: str, estado: str):
            nonlocal id_hist
            id_hist += 1
            historial_ccd.append(dict(id=id_hist, estudiante_codigo=e["codigo"], curso_ccd_id=curso_id, periodo_id=pid,
                                      estado=estado, fecha=fecha_en(pid, estado == "aprobado")))

        def cursar(curso_id: int, desde: int):
            """Intenta un curso CCD desde la posición `desde` de periodos_alumno. Devuelve True si queda aprobado."""
            pos = min(desde, n - 1)
            pid = periodos_alumno[pos]
            if pid == PERIODO_ACTUAL:
                agregar(curso_id, pid, "en_curso")
                return False
            if rnd.random() < 0.06 and pos + 1 < n:
                agregar(curso_id, pid, "reprobado")
                pid2 = periodos_alumno[pos + 1]
                agregar(curso_id, pid2, "en_curso" if pid2 == PERIODO_ACTUAL else "aprobado")
                return pid2 != PERIODO_ACTUAL
            agregar(curso_id, pid, "aprobado")
            return True

        # Ruta 1 (obligatoria). Algunos de semestres avanzados no la han cursado: generan alerta.
        if n >= 3 and rnd.random() < 0.15:
            pass
        elif n >= 2 or rnd.random() < 0.5:
            cursar(1, rnd.randint(0, min(1, n - 1)))
        if n >= 3 and rnd.random() < 0.6:
            cursar(rnd.choice([2, 3, 4]), rnd.randint(1, n - 1))
        if n >= 5 and rnd.random() < 0.45:
            cursar(rnd.choice([5, 6, 7]), rnd.randint(2, n - 1))

    # --- profesores oficiales (APOLO), si existen --------------------------------------------
    profesores = leer_profesores()

    for e in estudiantes:
        for k in [k for k in e if k.startswith("_")]:
            del e[k]
    # Competencias Digitales R2025 y horas libres: cada estudiante tiene su propio generador con semilla en el
    # código (registro.requisitos), así no altera la secuencia aleatoria del resto de los datos.
    fuente_pruebas = "https://unab.edu.co/inscripcion-a-las-pruebas-de-competencias-digitales-estudiantes-desde-sexto-semestre/"
    competencias = [dict(id=i + 1, orden=i + 1, nombre=p, materia=f"Examen {p}", requisito="Competencias Digitales R2025",
                         fuente_url=fuente_pruebas) for i, p in enumerate(registro.PILARES)]
    id_pilar = {c["nombre"]: c["id"] for c in competencias}
    resultados, horas = [], []
    for e in estudiantes:
        req = registro.requisitos(e["codigo"], e["fecha_ingreso"])
        for r in req["resultados"]:
            resultados.append(dict(estudiante_codigo=e["codigo"], competencia_id=id_pilar[r["pilar"]],
                                   aprobada=r["aprobada"], fecha_prueba=r["fecha_prueba"]))
        horas.append(dict(estudiante_codigo=e["codigo"], horas_cumplidas=req["horas_libres"],
                          horas_requeridas=registro.HORAS_REQUERIDAS))

    return dict(programas=[programa], cursos=cursos, prerrequisitos=prerreq, periodos=periodos,
                profesores=profesores, secciones=secciones, estudiantes=estudiantes, matriculas=matriculas,
                cursos_ccd=cursos_ccd, historial_ccd=historial_ccd, calendario_academico=leer_calendario(),
                competencias_digitales=competencias, resultados_competencias=resultados, horas_libres=horas,
                _origen_plan=origen_plan)


def leer_profesores() -> list[dict]:
    """Profesores reales de APOLO (solo consulta; nunca se asignan a secciones sintéticas)."""
    if not RUTA_PROFESORES.exists():
        return []
    datos = json.loads(RUTA_PROFESORES.read_text(encoding="utf-8"))
    if isinstance(datos, dict):
        datos = next((v for v in datos.values() if isinstance(v, list)), [])

    def pick(d, *claves):
        for k in claves:
            v = d.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return None

    salida, vistos = [], set()
    for d in datos:
        if not isinstance(d, dict):
            continue
        nombre = pick(d, "nombre", "name", "nombre_completo")
        if not nombre:
            continue
        url = pick(d, "apolo_url", "url", "perfil", "profile_url", "perfil_url")
        if url and url in vistos:
            continue
        vistos.add(url)
        unidades = [u.get("nombre", "").strip() for u in d.get("unidades") or [] if isinstance(u, dict)]
        unidad = "; ".join(u for u in unidades if u) or pick(d, "unidad", "departamento", "unit", "facultad", "afiliacion")
        salida.append(dict(id=len(salida) + 1, nombre=nombre, unidad=unidad,
                           cargo=pick(d, "cargo", "puesto", "jobTitle", "job_title"), apolo_url=url,
                           cvlac_url=pick(d, "cvlac_url", "cvlac")))
    return salida


def leer_calendario() -> list[dict]:
    filas = []
    with open(RUTA_CALENDARIO, newline="", encoding="utf-8") as f:
        for i, r in enumerate(csv.DictReader(f), 1):
            filas.append(dict(id=i, evento=r["evento"], categoria=r["categoria"] or None,
                              fecha_inicio=r["fecha_inicio"] or None, fecha_fin=r["fecha_fin"] or None,
                              verificado=r["verificado"].strip().lower() == "true", fuente_url=r["fuente_url"] or None))
    return filas


# --- salida -------------------------------------------------------------------------------------
ORDEN_TABLAS = ["programas", "periodos", "cursos", "prerrequisitos", "profesores", "secciones", "estudiantes",
                "matriculas", "cursos_ccd", "historial_ccd", "calendario_academico",
                "competencias_digitales", "resultados_competencias", "horas_libres"]
COLUMNAS = {
    "programas": ["id", "codigo", "nombre", "total_creditos", "fuente_url"],
    "periodos": ["id", "nombre", "fecha_inicio", "fecha_fin", "actual"],
    "cursos": ["id", "programa_id", "codigo", "nombre", "creditos", "semestre_plan", "tipo", "es_oficial"],
    "prerrequisitos": ["curso_id", "requisito_id", "es_simulado"],
    "profesores": ["id", "nombre", "unidad", "cargo", "apolo_url", "cvlac_url"],
    "secciones": ["nrc", "curso_id", "periodo_id", "docente", "horario", "cupo"],
    "estudiantes": ["codigo", "nombres", "apellidos", "correo", "programa_id", "semestre_actual", "estado", "fecha_ingreso"],
    "matriculas": ["id", "estudiante_codigo", "nrc", "periodo_id", "estado", "nota_final"],
    "cursos_ccd": ["id", "ruta", "nombre", "obligatorio", "descripcion", "fuente_url"],
    "historial_ccd": ["id", "estudiante_codigo", "curso_ccd_id", "periodo_id", "estado", "fecha"],
    "calendario_academico": ["id", "evento", "categoria", "fecha_inicio", "fecha_fin", "verificado", "fuente_url"],
    "competencias_digitales": ["id", "orden", "nombre", "materia", "requisito", "fuente_url"],
    "resultados_competencias": ["estudiante_codigo", "competencia_id", "aprobada", "fecha_prueba"],
    "horas_libres": ["estudiante_codigo", "horas_cumplidas", "horas_requeridas"],
}
TABLAS_CON_SERIAL = ["programas", "cursos", "profesores", "matriculas", "cursos_ccd", "historial_ccd", "calendario_academico",
                     "competencias_digitales"]


def lit(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def escribir(datos: dict) -> None:
    DIR_CSV.mkdir(parents=True, exist_ok=True)
    for t in ORDEN_TABLAS:
        with open(DIR_CSV / f"{t}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(COLUMNAS[t])
            for r in datos[t]:
                w.writerow(["" if r[c] is None else (str(r[c]).lower() if isinstance(r[c], bool) else r[c]) for c in COLUMNAS[t]])

    lineas = [
        "-- seed.sql: datos SINTETICOS (Faker es_CO, semilla 2026) que simulan Banner-Cosmos.",
        "-- Generado por db/seed/generar_datos.py. Ejecutar despues de las migraciones 001 a 006.",
        "-- Borra y vuelve a cargar solo las tablas del simulador (no toca documentos, noticias ni n8n_chat_histories).",
        "begin;",
        "truncate table programas, periodos, estudiantes, cursos_ccd, profesores, calendario_academico, competencias_digitales "
        "restart identity cascade;",
    ]
    for t in ORDEN_TABLAS:
        filas = datos[t]
        cols = COLUMNAS[t]
        for i in range(0, len(filas), 200):
            lote = filas[i:i + 200]
            vals = ",\n".join("(" + ", ".join(lit(r[c]) for c in cols) + ")" for r in lote)
            lineas.append(f"insert into {t} ({', '.join(cols)}) values\n{vals};")
    for t in TABLAS_CON_SERIAL:
        lineas.append(f"select setval(pg_get_serial_sequence('{t}', 'id'), greatest((select coalesce(max(id), 1) from {t}), 1));")
    lineas.append("commit;")
    RUTA_SEED_SQL.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def resumen(datos: dict) -> None:
    print(f"Plan de estudios: {datos['_origen_plan']}")
    for t in ORDEN_TABLAS:
        print(f"  {t}: {len(datos[t])}")
    est = datos["estudiantes"]
    por_estado: dict[str, int] = {}
    for e in est:
        por_estado[e["estado"]] = por_estado.get(e["estado"], 0) + 1
    print("  estados de estudiantes:", por_estado)
    notas = [m["nota_final"] for m in datos["matriculas"] if m["nota_final"] is not None]
    print(f"  notas: {len(notas)}, reprobadas: {sum(1 for n in notas if n < NOTA_APROBACION)}")


def main() -> None:
    datos = generar()
    escribir(datos)
    resumen(datos)


if __name__ == "__main__":
    main()
