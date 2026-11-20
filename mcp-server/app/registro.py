"""
Alta automática de estudiantes sintéticos.

Si llega un código válido (U00 + 6 dígitos) que no está en la base, se crea un estudiante sintético con las mismas
reglas del generador de datos (db/seed/generar_datos.py): perfil académico, carga por periodo, prerrequisitos,
notas, cancelaciones e historial del Centro de Competencias Digitales. Todo sale de un generador aleatorio con
semilla en el código, así que el mismo código produce siempre el mismo estudiante.

Los nombres de algunos códigos pueden fijarse en estudiantes_fijos.json (por ejemplo, el del autor del proyecto);
el resto de su información académica también es sintética.
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

NOTA_APROBACION = 3.0
PERFILES = {
    # carga objetivo (créditos), media de nota, probabilidad de cancelar un curso
    "normal": dict(cargas=[15, 16, 17, 18], mu=(3.95, 0.3), cancela=0.02),
    "rezagado": dict(cargas=[9, 10, 12, 13], mu=(3.3, 0.25), cancela=0.06),
    "avanzado": dict(cargas=[18, 19, 20], mu=(4.25, 0.2), cancela=0.01),
    "irregular": dict(cargas=[6, 9, 12, 15, 16], mu=(3.65, 0.35), cancela=0.12),
}
# Misma proporción de ingresos que el generador (periodo -> peso).
PESO_INGRESO = {"2023-1": 19, "2023-2": 15, "2024-1": 19, "2024-2": 15, "2025-1": 17, "2025-2": 15, "2026-1": 12, "2026-2": 8}
RUTA_FIJOS = Path(__file__).with_name("estudiantes_fijos.json")


def estudiantes_fijos() -> dict[str, dict]:
    if not RUTA_FIJOS.exists():
        return {}
    return {e["codigo"].upper(): e for e in json.loads(RUTA_FIJOS.read_text(encoding="utf-8"))}


def _catalogo(conn) -> dict:
    periodos = conn.execute("select id, fecha_inicio, fecha_fin, actual from periodos order by id").fetchall()
    programa = conn.execute("select id from programas order by id limit 1").fetchone()
    cursos = conn.execute("select id, creditos, semestre_plan from cursos where programa_id = %s order by id",
                          (programa["id"],)).fetchall()
    reqs: dict[int, list[int]] = {}
    for r in conn.execute("select curso_id, requisito_id from prerrequisitos").fetchall():
        reqs.setdefault(r["curso_id"], []).append(r["requisito_id"])
    secciones: dict[tuple[int, str], list[dict]] = {}
    for s in conn.execute("select nrc, curso_id, periodo_id, horario from secciones order by nrc").fetchall():
        secciones.setdefault((s["curso_id"], s["periodo_id"]), []).append(s)
    ccd: dict[int, list[int]] = {}
    for c in conn.execute("select id, ruta from cursos_ccd order by id").fetchall():
        ccd.setdefault(c["ruta"], []).append(c["id"])
    return dict(periodos=periodos, programa_id=programa["id"], cursos=cursos, reqs=reqs, secciones=secciones, ccd=ccd)


def _nombre(rnd: random.Random, semilla: int) -> tuple[str, str]:
    from faker import Faker
    fake = Faker("es_CO")
    fake.seed_instance(semilla)
    femenino = rnd.random() < 0.45
    pila = fake.first_name_female if femenino else fake.first_name_male
    nombres = pila() + (" " + pila() if rnd.random() < 0.35 else "")
    return nombres, f"{fake.last_name()} {fake.last_name()}"


def generar(codigo: str, cat: dict, fijo: dict | None = None) -> dict:
    """Devuelve las filas (estudiante, matrículas e historial CCD) del estudiante sintético `codigo`."""
    fijo = fijo or {}
    rnd = random.Random(f"cb-estudiante-{codigo}")
    ids_periodo = [p["id"] for p in cat["periodos"]]
    fechas = {p["id"]: (p["fecha_inicio"], p["fecha_fin"]) for p in cat["periodos"]}
    actual = next((p["id"] for p in cat["periodos"] if p["actual"]), ids_periodo[-1])
    disponibles = [p for p in ids_periodo if p <= actual]

    ingreso = fijo.get("ingreso") if fijo.get("ingreso") in disponibles else \
        rnd.choices(disponibles, weights=[PESO_INGRESO.get(p, 10) for p in disponibles])[0]
    nombre_perfil = fijo.get("perfil") if fijo.get("perfil") in PERFILES else \
        rnd.choices(list(PERFILES), weights=[60, 20, 12, 8])[0]
    if ingreso == actual:
        nombre_perfil = "normal"
    perfil = PERFILES[nombre_perfil]
    mu = rnd.gauss(*perfil["mu"])

    curso_por_id = {c["id"]: c for c in cat["cursos"]}
    aprobados: set[int] = set()
    fallidos: set[int] = set()
    matriculas, periodos_cursados = [], []
    for pid in disponibles[disponibles.index(ingreso):]:
        pendientes = [c for c in cat["cursos"] if c["id"] not in aprobados]
        if not pendientes:
            break
        objetivo = rnd.choice(perfil["cargas"])
        elegibles = [c for c in pendientes if all(r in aprobados for r in cat["reqs"].get(c["id"], []))]
        elegibles.sort(key=lambda c: (c["id"] not in fallidos, c["semestre_plan"], c["id"]))
        carga, ocupados, nuevos = 0, set(), set()
        for c in elegibles:
            opciones = cat["secciones"].get((c["id"], pid), [])
            if not opciones or carga + c["creditos"] > objetivo:
                continue
            libres = [s for s in opciones if s["horario"] not in ocupados]  # evita cruces de horario
            if not libres:
                continue
            sec = rnd.choice(libres)
            ocupados.add(sec["horario"])
            carga += c["creditos"]
            m = dict(nrc=sec["nrc"], periodo_id=pid, estado="", nota_final=None)
            if pid == actual:
                m["estado"] = "inscrita"
            elif rnd.random() < perfil["cancela"]:
                m["estado"] = "cancelada"
            else:
                nota = round(min(5.0, max(0.0, rnd.gauss(mu, 0.55))), 1)
                m["estado"], m["nota_final"] = "finalizada", nota
                if nota >= NOTA_APROBACION:
                    nuevos.add(c["id"])
                    fallidos.discard(c["id"])
                else:
                    fallidos.add(c["id"])
            matriculas.append(m)
        if carga:
            periodos_cursados.append(pid)
        aprobados |= nuevos

    total = sum(c["creditos"] for c in cat["cursos"])
    graduado = sum(curso_por_id[i]["creditos"] for i in aprobados) >= total
    semilla = int(codigo[3:])
    nombres, apellidos = _nombre(rnd, semilla)
    estudiante = dict(
        codigo=codigo, nombres=fijo.get("nombres") or nombres, apellidos=fijo.get("apellidos") or apellidos,
        correo=f"{codigo.lower()}@demo.unab.local", programa_id=cat["programa_id"],
        semestre_actual=max(1, min(max(c["semestre_plan"] for c in cat["cursos"]), len(periodos_cursados))),
        estado="graduado" if graduado else "activo",
        fecha_ingreso=fechas[ingreso][0])

    # Historial del Centro de Competencias Digitales (mismas probabilidades del generador).
    historial = []
    periodos_alumno = disponibles[disponibles.index(ingreso):]
    n = len(periodos_alumno)

    def fecha_en(pid: str, aprobado: bool) -> date:
        ini, fin = fechas[pid]
        return fin - timedelta(days=rnd.randint(2, 20)) if aprobado else ini + timedelta(days=rnd.randint(20, 70))

    def agregar(curso_id: int, pid: str, estado: str):
        historial.append(dict(curso_ccd_id=curso_id, periodo_id=pid, estado=estado, fecha=fecha_en(pid, estado == "aprobado")))

    def cursar(curso_id: int, desde: int):
        pos = min(desde, n - 1)
        pid = periodos_alumno[pos]
        if pid == actual:
            agregar(curso_id, pid, "en_curso")
            return
        if rnd.random() < 0.06 and pos + 1 < n:
            agregar(curso_id, pid, "reprobado")
            pid2 = periodos_alumno[pos + 1]
            agregar(curso_id, pid2, "en_curso" if pid2 == actual else "aprobado")
            return
        agregar(curso_id, pid, "aprobado")

    ccd = cat["ccd"]
    if ccd.get(1) and not (n >= 3 and rnd.random() < 0.15) and (n >= 2 or rnd.random() < 0.5):
        cursar(ccd[1][0], rnd.randint(0, min(1, n - 1)))
    if ccd.get(2) and n >= 3 and rnd.random() < 0.6:
        cursar(rnd.choice(ccd[2]), rnd.randint(1, n - 1))
    if ccd.get(3) and n >= 5 and rnd.random() < 0.45:
        cursar(rnd.choice(ccd[3]), rnd.randint(2, n - 1))

    return dict(estudiante=estudiante, matriculas=matriculas, historial_ccd=historial, perfil=nombre_perfil)


# --- Competencias Digitales R2025 y horas libres ----------------------------------------------------
# Pilares del requisito, en el orden del portal del estudiante (ver db/migrations/005_competencias_horas.sql).
PILARES = ["Vida en línea", "MS Word", "MS Excel", "MS PowerPoint", "Cultura digital"]
# Ajuste de la probabilidad de aprobar cada pilar frente al nivel del estudiante (sintético).
AJUSTE_PILAR = {"Vida en línea": 0.12, "MS Word": 0.05, "MS Excel": -0.12, "MS PowerPoint": 0.02, "Cultura digital": 0.06}
# Sesiones de la prueba (sábados de marzo y septiembre); la de marzo de 2026 es la fecha publicada por la UNAB.
SESIONES_PRUEBA = [date(2023, 9, 23), date(2024, 3, 16), date(2024, 9, 21), date(2025, 3, 22), date(2025, 9, 20),
                   date(2026, 3, 21), date(2026, 9, 19)]
HORAS_REQUERIDAS = 96
HORAS_MAXIMAS = 120  # puede pasar de 96: el requisito queda cumplido


def requisitos(codigo: str, fecha_ingreso: date) -> dict:
    """Resultado de la prueba por pilar y horas libres del estudiante, siempre los mismos para el mismo código."""
    if isinstance(fecha_ingreso, str):
        fecha_ingreso = date.fromisoformat(fecha_ingreso[:10])
    rnd = random.Random(f"cb-requisitos-{codigo}")
    nivel = rnd.uniform(0.3, 0.95)
    posibles = [s for s in SESIONES_PRUEBA if s >= fecha_ingreso + timedelta(days=30)] or SESIONES_PRUEBA[-1:]
    fecha = rnd.choice(posibles)
    resultados = [dict(pilar=p, aprobada=rnd.random() < min(0.97, max(0.05, nivel + AJUSTE_PILAR[p])), fecha_prueba=fecha)
                  for p in PILARES]
    return dict(resultados=resultados, horas_libres=rnd.randint(0, HORAS_MAXIMAS))


def asegurar_requisitos(conn, codigo: str) -> bool:
    """Crea los resultados de la prueba y las horas libres si el estudiante aún no los tiene. True si los creó."""
    est = conn.execute("select fecha_ingreso from estudiantes where codigo = %s", (codigo,)).fetchone()
    if not est:
        return False
    if conn.execute("select 1 from horas_libres where estudiante_codigo = %s", (codigo,)).fetchone():
        return False
    ids = {r["nombre"]: r["id"] for r in conn.execute("select id, nombre from competencias_digitales").fetchall()}
    req = requisitos(codigo, est["fecha_ingreso"])
    for r in req["resultados"]:
        if r["pilar"] in ids:
            conn.execute("""insert into resultados_competencias (estudiante_codigo, competencia_id, aprobada, fecha_prueba)
                            values (%s, %s, %s, %s) on conflict do nothing""",
                         (codigo, ids[r["pilar"]], r["aprobada"], r["fecha_prueba"]))
    conn.execute("""insert into horas_libres (estudiante_codigo, horas_cumplidas, horas_requeridas)
                    values (%s, %s, %s) on conflict do nothing""", (codigo, req["horas_libres"], HORAS_REQUERIDAS))
    return True


def asegurar(conn, codigo: str) -> bool:
    """Crea el estudiante si no existe. Devuelve True si lo creó. `conn` es una conexión psycopg con dict_row."""
    with conn.transaction():
        conn.execute("select pg_advisory_xact_lock(hashtext(%s))", (codigo,))
        if conn.execute("select 1 from estudiantes where codigo = %s", (codigo,)).fetchone():
            return False
        filas = generar(codigo, _catalogo(conn), estudiantes_fijos().get(codigo))
        e = filas["estudiante"]
        conn.execute(
            """insert into estudiantes (codigo, nombres, apellidos, correo, programa_id, semestre_actual, estado, fecha_ingreso)
               values (%(codigo)s, %(nombres)s, %(apellidos)s, %(correo)s, %(programa_id)s, %(semestre_actual)s,
                       %(estado)s, %(fecha_ingreso)s)""", e)
        for m in filas["matriculas"]:
            conn.execute("""insert into matriculas (estudiante_codigo, nrc, periodo_id, estado, nota_final)
                            values (%s, %s, %s, %s, %s)""", (codigo, m["nrc"], m["periodo_id"], m["estado"], m["nota_final"]))
        for h in filas["historial_ccd"]:
            conn.execute("""insert into historial_ccd (estudiante_codigo, curso_ccd_id, periodo_id, estado, fecha)
                            values (%s, %s, %s, %s, %s)""", (codigo, h["curso_ccd_id"], h["periodo_id"], h["estado"], h["fecha"]))
        asegurar_requisitos(conn, codigo)
    return True
