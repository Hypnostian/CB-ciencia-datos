"""Lógica de negocio pura (sin base de datos ni red): avance, proyección, alertas y recomendaciones.

Convenciones de los datos de entrada:
  cursos:  lista de dicts {id, codigo, nombre, creditos, semestre_plan, tipo, estado, intentos_reprobados}
           donde estado es 'aprobado' | 'en_curso' | 'reprobado' | 'pendiente'
  reqs:    {curso_id: [{requisito_id, es_simulado}]}
Los prerrequisitos son simulados (UNAB no los publica); se marcan siempre en la salida.
"""
from __future__ import annotations

from functools import lru_cache

CREDITOS_POR_SEMESTRE_DEFECTO = 18
MAX_SEMESTRES_PROYECCION = 16
NOTA_APROBACION = 3.0


def siguiente_periodo(pid: str) -> str:
    anio, sem = pid.split("-")
    return f"{anio}-2" if sem == "1" else f"{int(anio) + 1}-1"


def semestre_real(cursos: list[dict]) -> int:
    """1 + semestres completos del plan cubiertos por los créditos aprobados."""
    aprobados = sum(c["creditos"] for c in cursos if c["estado"] == "aprobado")
    por_sem: dict[int, int] = {}
    for c in cursos:
        por_sem[c["semestre_plan"]] = por_sem.get(c["semestre_plan"], 0) + c["creditos"]
    acum, completos = 0, 0
    for s in sorted(por_sem):
        acum += por_sem[s]
        if acum <= aprobados:
            completos += 1
    return 1 + completos


UMBRAL_REZAGO_CREDITOS = 6


def brecha_creditos(cursos: list[dict], semestre_actual: int) -> int:
    """Créditos que faltan aprobar frente a los que el plan espera haber completado antes del semestre actual."""
    esperados = sum(c["creditos"] for c in cursos if c["semestre_plan"] < semestre_actual)
    aprobados = sum(c["creditos"] for c in cursos if c["estado"] == "aprobado")
    return max(0, esperados - aprobados)


def resumen_avance(cursos: list[dict], total_creditos: int) -> dict:
    aprobados = [c for c in cursos if c["estado"] == "aprobado"]
    cred_aprob = sum(c["creditos"] for c in aprobados)
    cred_curso = sum(c["creditos"] for c in cursos if c["estado"] == "en_curso")

    def corto(c):
        return {"codigo": c["codigo"], "nombre": c["nombre"], "creditos": c["creditos"], "estado": c["estado"]}

    por_sem: dict[int, dict] = {}
    for c in sorted(cursos, key=lambda x: (x["semestre_plan"], x["codigo"])):
        bloque = por_sem.setdefault(c["semestre_plan"], {"semestre": c["semestre_plan"], "aprobados": [], "pendientes": []})
        (bloque["aprobados"] if c["estado"] == "aprobado" else bloque["pendientes"]).append(corto(c))
    return {
        "creditos_aprobados": cred_aprob,
        "creditos_totales": total_creditos,
        "creditos_en_curso": cred_curso,
        "porcentaje_avance": round(100 * cred_aprob / total_creditos, 1) if total_creditos else 0.0,
        "cursos_aprobados": len(aprobados),
        "cursos_plan": len(cursos),
        "semestre_real": semestre_real(cursos),
        "por_semestre": list(por_sem.values()),
    }


def _alturas(pendientes_ids: set[int], reqs: dict[int, list[dict]]) -> dict[int, int]:
    """Longitud de la cadena más larga de cursos pendientes que dependen de cada curso (para priorizar)."""
    dependientes: dict[int, list[int]] = {i: [] for i in pendientes_ids}
    for cid in pendientes_ids:
        for r in reqs.get(cid, []):
            if r["requisito_id"] in pendientes_ids:
                dependientes[r["requisito_id"]].append(cid)

    @lru_cache(maxsize=None)
    def h(i: int) -> int:
        return 1 + max((h(d) for d in dependientes[i]), default=0)

    return {i: h(i) for i in pendientes_ids}


def proyectar(cursos: list[dict], reqs: dict[int, list[dict]], periodo_actual: str,
              creditos_por_semestre: int = CREDITOS_POR_SEMESTRE_DEFECTO) -> dict:
    """Llena cada semestre futuro hasta `creditos_por_semestre` respetando prerrequisitos.

    Supuesto: los cursos que el estudiante tiene en curso se aprueban al cerrar el periodo actual.
    Los cursos reprobados se priorizan.
    """
    cap = max(int(creditos_por_semestre), 1)
    completados = {c["id"] for c in cursos if c["estado"] in ("aprobado", "en_curso")}
    pendientes = {c["id"]: c for c in cursos if c["id"] not in completados}
    alt = _alturas(set(pendientes), reqs)
    plan, periodo, bloqueados = [], periodo_actual, []
    for n in range(1, MAX_SEMESTRES_PROYECCION + 1):
        if not pendientes:
            break
        periodo = siguiente_periodo(periodo)
        elegibles = [c for c in pendientes.values() if all(r["requisito_id"] in completados for r in reqs.get(c["id"], []))]
        if not elegibles:
            bloqueados = [c["codigo"] for c in pendientes.values()]
            break
        elegibles.sort(key=lambda c: (c["estado"] != "reprobado", -alt[c["id"]], c["semestre_plan"], c["id"]))
        carga, sel = 0, []
        for c in elegibles:
            if carga + c["creditos"] <= cap or (not sel and c["creditos"] > cap):
                sel.append(c)
                carga += c["creditos"]
        for c in sel:
            del pendientes[c["id"]]
        completados |= {c["id"] for c in sel}
        plan.append({
            "semestre_futuro": n,
            "periodo_estimado": periodo,
            "creditos": carga,
            "cursos": [{"codigo": c["codigo"], "nombre": c["nombre"], "creditos": c["creditos"],
                        "semestre_plan": c["semestre_plan"],
                        "motivo": "reprobado, debe repetirse" if c["estado"] == "reprobado" else "plan de estudios"} for c in sel],
        })
    return {
        "creditos_por_semestre": cap,
        "semestres_restantes": len(plan),
        "graduacion_estimada": plan[-1]["periodo_estimado"] if plan and not pendientes else None,
        "creditos_pendientes_por_cursar": sum(c["creditos"] for c in cursos if c["estado"] in ("pendiente", "reprobado")),
        "plan": plan,
        "cursos_sin_ubicar": bloqueados,
        "supuestos": [
            "Los cursos en curso en el periodo actual se aprueban al cerrar el periodo.",
            "Se ofrecen todos los cursos en todos los periodos.",
            "Prerrequisitos simulados: la UNAB no los publica.",
        ],
    }


def alertas(cursos: list[dict], reqs: dict[int, list[dict]], semestre_actual: int, ccd_ruta1: str,
            periodo_actual: str | None = None) -> list[dict]:
    """Alertas: prerrequisitos que bloquean, cursos reprobados, CCD obligatorio faltante y rezago.

    ccd_ruta1: 'aprobado' | 'en_curso' | 'pendiente' (Interacción Digital).
    """
    por_id = {c["id"]: c for c in cursos}
    salida = []
    for c in sorted(cursos, key=lambda x: (x["semestre_plan"], x["codigo"])):
        if c["estado"] in ("aprobado", "en_curso"):
            continue
        faltan = [por_id[r["requisito_id"]] for r in reqs.get(c["id"], []) if por_id[r["requisito_id"]]["estado"] != "aprobado"]
        if faltan and c["semestre_plan"] <= semestre_actual + 1:
            solo_en_curso = all(f["estado"] == "en_curso" for f in faltan)
            alta = any(f["estado"] == "reprobado" for f in faltan) or c["semestre_plan"] < semestre_actual
            salida.append({
                "tipo": "prerrequisito_bloqueado",
                "severidad": "baja" if solo_en_curso else ("alta" if alta else "media"),
                "curso": c["nombre"], "curso_codigo": c["codigo"], "semestre_plan": c["semestre_plan"],
                "requisitos_faltantes": [{"codigo": f["codigo"], "nombre": f["nombre"], "estado": f["estado"]} for f in faltan],
                "prerrequisito_simulado": True,
                "mensaje": f"{c['nombre']} está bloqueado: falta aprobar " + ", ".join(
                    f"{f['nombre']} ({'en curso' if f['estado'] == 'en_curso' else f['estado']})" for f in faltan)
                + (". Se desbloquea si apruebas lo que cursas ahora." if solo_en_curso else "."),
            })
        elif c["estado"] == "reprobado":
            salida.append({
                "tipo": "curso_reprobado", "severidad": "media", "curso": c["nombre"], "curso_codigo": c["codigo"],
                "semestre_plan": c["semestre_plan"],
                "mensaje": f"Debes repetir {c['nombre']} (reprobado {c['intentos_reprobados']} vez/veces) y no está inscrito este periodo.",
            })
    if ccd_ruta1 != "aprobado":
        en_curso = ccd_ruta1 == "en_curso"
        salida.append({
            "tipo": "ccd_obligatorio", "severidad": "baja" if en_curso else ("alta" if semestre_actual >= 3 else "media"),
            "curso": "Interacción Digital (CCD Ruta 1)",
            "mensaje": "Estás cursando la Ruta 1 del CCD, que es obligatoria." if en_curso
            else "Te falta aprobar la Ruta 1 del Centro de Competencias Digitales (Interacción Digital), que es obligatoria.",
        })
    sr = semestre_real(cursos)
    gap = brecha_creditos(cursos, semestre_actual)
    if gap >= UMBRAL_REZAGO_CREDITOS:
        salida.append({
            "tipo": "rezago", "severidad": "alta" if gap >= 2 * UMBRAL_REZAGO_CREDITOS else "media",
            "semestre_nominal": semestre_actual, "semestre_real": sr, "creditos_de_rezago": gap,
            "mensaje": f"Vas en semestre {semestre_actual}, pero te faltan {gap} créditos aprobados frente a lo esperado "
                       f"para este punto del plan (tus créditos equivalen al semestre {sr}).",
        })
    orden = {"alta": 0, "media": 1, "baja": 2}
    salida.sort(key=lambda a: orden[a["severidad"]])
    return salida


def estado_ccd(catalogo: list[dict], historial: list[dict]) -> dict:
    """Rutas cumplidas y faltantes para la insignia (Ruta 1 obligatoria + un curso de la Ruta 2 + uno de la Ruta 3)."""
    est = {h["curso_ccd_id"]: h["estado"] for h in sorted(historial, key=lambda h: h["estado"] == "aprobado")}
    rutas = {}
    for r in (1, 2, 3):
        cursos = [c for c in catalogo if c["ruta"] == r]
        lista = [{"curso": c["nombre"], "estado": est.get(c["id"], "sin_cursar"), "obligatorio": c["obligatorio"]} for c in cursos]
        cumplida = any(x["estado"] == "aprobado" for x in lista)
        rutas[r] = {"ruta": r, "cumplida": cumplida, "obligatoria": r == 1, "cursos": lista}
    faltantes = []
    for r, v in rutas.items():
        if not v["cumplida"]:
            opciones = [x["curso"] for x in v["cursos"] if x["estado"] != "aprobado"]
            faltantes.append({"ruta": r, "obligatoria": r == 1,
                              "accion": ("Aprobar " + opciones[0]) if r == 1 else "Aprobar uno de: " + ", ".join(opciones)})
    return {
        "rutas": list(rutas.values()),
        "rutas_cumplidas": [r for r, v in rutas.items() if v["cumplida"]],
        "rutas_faltantes": faltantes,
        "insignia_completa": all(v["cumplida"] for v in rutas.values()),
        "ruta1_estado": next((x["estado"] for x in rutas[1]["cursos"]), "sin_cursar"),
    }


HORAS_LIBRES_REQUERIDAS = 96
FUENTE_PRUEBAS_CD = "https://unab.edu.co/inscripcion-a-las-pruebas-de-competencias-digitales-estudiantes-desde-sexto-semestre/"


def estado_competencias(filas: list[dict]) -> dict:
    """Requisito Competencias Digitales R2025 a partir del resultado de la prueba de cada pilar.

    filas: [{orden, competencia, aprobada, materia, fecha_prueba}] (una por pilar presentado).
    """
    pilares = sorted(filas, key=lambda f: f.get("orden", 0))
    lista = [{"competencia": f["competencia"], "estado": "aprobada" if f["aprobada"] else "no aprobada",
              "cumplida_con": f.get("materia") if f["aprobada"] else None} for f in pilares]
    aprobadas = [x["competencia"] for x in lista if x["estado"] == "aprobada"]
    faltantes = [x["competencia"] for x in lista if x["estado"] != "aprobada"]
    fechas = sorted({str(f["fecha_prueba"]) for f in pilares if f.get("fecha_prueba")})
    if not pilares:
        mensaje = "Aún no hay resultados de la prueba de competencias digitales."
    elif not faltantes:
        mensaje = "Aprobaste la prueba en los 5 pilares: el requisito de Competencias Digitales está cumplido."
    else:
        mensaje = (f"Te faltan {len(faltantes)} de {len(lista)} competencias digitales: " + ", ".join(faltantes)
                   + ". La prueba de cada pilar se presenta una sola vez; si no alcanzaste el umbral, debes inscribir "
                     "el curso correspondiente a cada pilar pendiente.")
    return {
        "requisito": "Competencias Digitales R2025",
        "prueba_presentada": bool(pilares),
        "fecha_prueba": fechas[-1] if fechas else None,
        "competencias": lista,
        "aprobadas": aprobadas,
        "faltantes": faltantes,
        "total_aprobadas": len(aprobadas),
        "total_pilares": len(lista),
        "cumplido": bool(pilares) and not faltantes,
        "mensaje": mensaje,
        "fuente_url": FUENTE_PRUEBAS_CD,
    }


def estado_horas_libres(horas_cumplidas: int | None, requeridas: int = HORAS_LIBRES_REQUERIDAS) -> dict:
    """Horas libres acumuladas frente a las 96 que pide el grado (si pasa de 96, el requisito está cumplido)."""
    horas = max(0, int(horas_cumplidas or 0))
    requeridas = max(1, int(requeridas or HORAS_LIBRES_REQUERIDAS))
    completo = horas >= requeridas
    faltan = max(0, requeridas - horas)
    return {
        "horas_cumplidas": horas,
        "horas_requeridas": requeridas,
        "horas_faltantes": faltan,
        "horas_adicionales": max(0, horas - requeridas),
        "porcentaje": round(min(100.0, 100 * horas / requeridas), 1),
        "completo": completo,
        "mensaje": (f"Tienes {horas} horas libres: ya completaste las {requeridas} horas libres necesarias para graduarte."
                    if completo else f"Tienes {horas} de {requeridas} horas libres; te faltan {faltan} para cumplir el requisito de grado."),
    }


def alertas_requisitos(competencias: dict | None, horas: dict | None, semestre_actual: int) -> list[dict]:
    """Alertas de requisitos de grado: competencias digitales sin aprobar y horas libres pendientes."""
    salida = []
    if competencias and competencias.get("faltantes"):
        n = len(competencias["faltantes"])
        salida.append({
            "tipo": "competencias_digitales", "severidad": "alta" if semestre_actual >= 6 else "media",
            "faltantes": competencias["faltantes"],
            "mensaje": f"Te faltan {n} competencia(s) digital(es) del requisito R2025: " + ", ".join(competencias["faltantes"])
                       + ". Debes inscribir el curso de cada pilar pendiente.",
        })
    if horas and not horas.get("completo"):
        salida.append({
            "tipo": "horas_libres", "severidad": "media" if semestre_actual >= 7 else "baja",
            "horas_faltantes": horas["horas_faltantes"],
            "mensaje": f"Te faltan {horas['horas_faltantes']} horas libres de {horas['horas_requeridas']} para graduarte.",
        })
    return salida


def recomendar(cursos: list[dict], reqs: dict[int, list[dict]], semestre_actual: int, periodo_actual: str,
               ccd: dict, eventos_ccd: list[dict]) -> dict:
    """Recomendaciones basadas en reglas a partir de alertas, proyección y estado del CCD."""
    al = alertas(cursos, reqs, semestre_actual, ccd["ruta1_estado"], periodo_actual)
    rezago = brecha_creditos(cursos, semestre_actual)
    reprobados = [c for c in cursos if c["estado"] == "reprobado"]
    sr = semestre_real(cursos)

    if rezago >= 2 * UMBRAL_REZAGO_CREDITOS or len(reprobados) >= 3:
        carga, razon = 14, "tienes rezago importante o varios cursos reprobados: conviene una carga moderada y priorizar los pendientes"
    elif rezago >= UMBRAL_REZAGO_CREDITOS or reprobados:
        carga, razon = 16, "tienes algo de rezago o un curso por repetir: prioriza lo pendiente sin sobrecargarte"
    elif sr > semestre_actual:
        carga, razon = 20, "vas adelantado: puedes tomar una carga alta si tu horario lo permite"
    else:
        carga, razon = 18, "vas al día: la carga estándar del plan es adecuada"

    proy = proyectar(cursos, reqs, periodo_actual, carga)
    siguiente = proy["plan"][0] if proy["plan"] else None
    recs = []
    for a in al:
        if a["tipo"] == "prerrequisito_bloqueado" and a["severidad"] != "baja":
            recs.append({"prioridad": "alta" if a["severidad"] == "alta" else "media", "tipo": "desbloquear",
                         "mensaje": "Aprueba primero " + ", ".join(f["nombre"] for f in a["requisitos_faltantes"])
                                    + f" para poder cursar {a['curso']}."})
        elif a["tipo"] == "curso_reprobado":
            recs.append({"prioridad": "alta", "tipo": "repetir", "mensaje": f"Inscribe de nuevo {a['curso']} el próximo periodo."})
        elif a["tipo"] == "ccd_obligatorio" and a["severidad"] != "baja":
            cuando = ""
            if eventos_ccd:
                e = eventos_ccd[0]
                cuando = f" Próxima oportunidad: {e['evento']} ({e['fecha_inicio']} a {e['fecha_fin']})."
            recs.append({"prioridad": "alta", "tipo": "ccd", "mensaje": "Inscríbete en Interacción Digital (Ruta 1 del CCD), es obligatoria." + cuando})
        elif a["tipo"] == "rezago":
            recs.append({"prioridad": "media", "tipo": "rezago",
                         "mensaje": "Para cerrar el rezago, prioriza los cursos de semestres anteriores antes que electivas o adelantos."})
    if ccd["ruta1_estado"] == "aprobado" and not ccd["insignia_completa"]:
        faltan = ", ".join(f"Ruta {f['ruta']}" for f in ccd["rutas_faltantes"])
        recs.append({"prioridad": "baja", "tipo": "ccd", "mensaje": f"Para la insignia del CCD te faltan: {faltan}. Los cursos intensivos y vacacionales son una buena opción."})
    if proy["semestres_restantes"] and proy["semestres_restantes"] <= 2 and not proy["cursos_sin_ubicar"]:
        recs.append({"prioridad": "media", "tipo": "grado", "mensaje": f"Te quedan {proy['semestres_restantes']} semestre(s): revisa requisitos de grado y la práctica en ingeniería de sistemas."})
    if not recs:
        recs.append({"prioridad": "baja", "tipo": "general", "mensaje": "No hay alertas: sigue el plan y cuida tu carga académica."})
    orden = {"alta": 0, "media": 1, "baja": 2}
    recs.sort(key=lambda r: orden[r["prioridad"]])
    recs = recs[:6]
    return {
        "semestre_nominal": semestre_actual,
        "semestre_real": sr,
        "carga_sugerida_creditos": carga,
        "razon_carga": razon,
        "cursos_sugeridos_proximo_periodo": siguiente,
        "recomendaciones": recs,
        "alertas": al,
        "semestres_restantes": proy["semestres_restantes"],
        "nota": "Prerrequisitos simulados: la UNAB no los publica.",
    }
