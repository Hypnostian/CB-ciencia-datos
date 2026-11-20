"""Implementación de las herramientas MCP. Reciben un repositorio (RepoPG o uno falso en pruebas)."""
from __future__ import annotations

import functools
import re
from datetime import date, datetime, timedelta, timezone

from . import logica

ZONA_CO = timezone(timedelta(hours=-5))  # hora de Colombia

CODIGO_RE = re.compile(r"^U00[0-9]{6}$")


class ErrorEstudiante(Exception):
    pass


def _contexto(repo, codigo: str) -> dict:
    codigo = (codigo or "").strip().upper()
    if not CODIGO_RE.match(codigo):
        raise ErrorEstudiante("Código de estudiante inválido: debe tener el formato U00 seguido de 6 dígitos (ej. U00123456).")
    est = repo.estudiante(codigo)
    nuevo = False
    if not est and hasattr(repo, "asegurar_estudiante"):
        # Código válido que no está en la base: se crea un estudiante sintético (siempre el mismo para ese código).
        nuevo = repo.asegurar_estudiante(codigo)
        est = repo.estudiante(codigo)
    if not est:
        raise ErrorEstudiante(f"No existe el estudiante {codigo}.")
    periodo = repo.periodo_actual()
    return {"est": est, "periodo": periodo["id"] if periodo else None, "codigo": codigo, "nuevo": nuevo}


def _identidad(est: dict) -> dict:
    return {"codigo": est["codigo"], "nombre": f"{est['nombres']} {est['apellidos']}", "programa": est["programa"],
            "semestre_actual": est["semestre_actual"], "estado": est["estado"]}


def con_errores(f):
    """Convierte los errores de validación en un JSON {error: ...} para que el chatbot lo explique."""
    @functools.wraps(f)
    def envoltura(*a, **kw):
        try:
            return f(*a, **kw)
        except ErrorEstudiante as e:
            return {"error": str(e)}
    return envoltura


def _requisitos_grado(repo, codigo: str) -> tuple[dict, dict]:
    """Estado de las Competencias Digitales R2025 y de las horas libres. Si faltan en la base, se generan."""
    filas = repo.competencias(codigo)
    horas = repo.horas_libres(codigo)
    if (not filas or not horas) and hasattr(repo, "asegurar_requisitos"):
        repo.asegurar_requisitos(codigo)
        filas, horas = repo.competencias(codigo), repo.horas_libres(codigo)
    h = logica.estado_horas_libres(horas["horas_cumplidas"], horas["horas_requeridas"]) if horas else None
    return logica.estado_competencias(filas), h


def estado_matricula(repo, estudiante_codigo: str) -> dict:
    c = _contexto(repo, estudiante_codigo)
    cursos = repo.matricula_actual(c["codigo"])
    return {
        "estudiante": _identidad(c["est"]),
        "periodo_actual": c["periodo"],
        "cursos_inscritos": cursos,
        "total_cursos": len(cursos),
        "creditos_inscritos": sum(x["creditos"] for x in cursos),
    }


def perfil_estudiante(repo, estudiante_codigo: str) -> dict:
    """Ficha del estudiante para la app: identidad, horario del periodo actual (con NRC y docente) y avance."""
    c = _contexto(repo, estudiante_codigo)
    est = c["est"]
    cursos = repo.matricula_actual(c["codigo"])
    avance = logica.resumen_avance(repo.cursos_estudiante(c["codigo"]), est["total_creditos"])
    comp, horas = _requisitos_grado(repo, c["codigo"])
    return {
        "codigo": est["codigo"], "nombre": f"{est['nombres']} {est['apellidos']}",
        "nombres": est["nombres"], "apellidos": est["apellidos"], "correo": est["correo"],
        "programa": est["programa"], "semestre_actual": est["semestre_actual"], "estado": est["estado"],
        "periodo_actual": c["periodo"],
        "horario": cursos,
        "creditos_inscritos": sum(x["creditos"] for x in cursos),
        "avance": {k: avance.get(k) for k in ("creditos_aprobados", "creditos_totales", "creditos_en_curso",
                                             "porcentaje_avance", "cursos_aprobados", "cursos_plan")},
        "competencias_digitales": {k: comp[k] for k in ("requisito", "fecha_prueba", "competencias", "faltantes",
                                                        "total_aprobadas", "total_pilares", "cumplido")},
        "horas_libres": {k: horas[k] for k in ("horas_cumplidas", "horas_requeridas", "horas_faltantes", "completo")}
        if horas else None,
        "nuevo": c["nuevo"],
    }


def avance_plan(repo, estudiante_codigo: str) -> dict:
    c = _contexto(repo, estudiante_codigo)
    cursos = repo.cursos_estudiante(c["codigo"])
    return {"estudiante": _identidad(c["est"]), "programa": c["est"]["programa"],
            **logica.resumen_avance(cursos, c["est"]["total_creditos"])}


def proyeccion_semestres(repo, estudiante_codigo: str, creditos_por_semestre: int = 18) -> dict:
    c = _contexto(repo, estudiante_codigo)
    creditos_por_semestre = max(6, min(int(creditos_por_semestre), 24))
    cursos = repo.cursos_estudiante(c["codigo"])
    reqs = repo.prerrequisitos(c["est"]["programa_id"])
    return {"estudiante": _identidad(c["est"]), "periodo_actual": c["periodo"],
            **logica.proyectar(cursos, reqs, c["periodo"], creditos_por_semestre)}


def _ccd(repo, codigo: str) -> dict:
    return logica.estado_ccd(repo.catalogo_ccd(), repo.historial_ccd(codigo))


def requisitos_pendientes(repo, estudiante_codigo: str) -> dict:
    c = _contexto(repo, estudiante_codigo)
    cursos = repo.cursos_estudiante(c["codigo"])
    reqs = repo.prerrequisitos(c["est"]["programa_id"])
    ccd = _ccd(repo, c["codigo"])
    al = logica.alertas(cursos, reqs, c["est"]["semestre_actual"], ccd["ruta1_estado"], c["periodo"])
    comp, horas = _requisitos_grado(repo, c["codigo"])
    al += logica.alertas_requisitos(comp, horas, c["est"]["semestre_actual"])
    al.sort(key=lambda a: {"alta": 0, "media": 1, "baja": 2}[a["severidad"]])
    return {"estudiante": _identidad(c["est"]), "total_alertas": len(al), "alertas": al,
            "nota": "Prerrequisitos simulados: la UNAB no los publica."}


def cursos_ccd(repo, estudiante_codigo: str) -> dict:
    c = _contexto(repo, estudiante_codigo)
    hist = repo.historial_ccd(c["codigo"])
    return {"estudiante": _identidad(c["est"]), "historial": hist, **_ccd(repo, c["codigo"]),
            "contacto": "ccdigital@unab.edu.co"}


def competencias_digitales(repo, estudiante_codigo: str) -> dict:
    """Requisito Competencias Digitales R2025: resultado de la prueba por pilar, aprobadas y faltantes."""
    c = _contexto(repo, estudiante_codigo)
    comp, _ = _requisitos_grado(repo, c["codigo"])
    return {"estudiante": _identidad(c["est"]), **comp,
            "nota": "Resultados sintéticos de la prueba (los pilares son los del portal del estudiante).",
            "contacto": "ccdigital@unab.edu.co"}


def horas_libres(repo, estudiante_codigo: str) -> dict:
    """Horas libres acumuladas frente a las 96 requeridas para el grado."""
    c = _contexto(repo, estudiante_codigo)
    _, horas = _requisitos_grado(repo, c["codigo"])
    if horas is None:
        raise ErrorEstudiante("No hay registro de horas libres para este estudiante.")
    return {"estudiante": _identidad(c["est"]), **horas, "nota": "Horas libres sintéticas, asignadas al azar para el demo."}


def recomendaciones(repo, estudiante_codigo: str) -> dict:
    c = _contexto(repo, estudiante_codigo)
    cursos = repo.cursos_estudiante(c["codigo"])
    reqs = repo.prerrequisitos(c["est"]["programa_id"])
    ccd = _ccd(repo, c["codigo"])
    eventos = [e for e in repo.calendario(None, "ccd") if e.get("verificado")][:2]
    salida = logica.recomendar(cursos, reqs, c["est"]["semestre_actual"], c["periodo"], ccd, eventos)
    comp, horas = _requisitos_grado(repo, c["codigo"])
    extra = []
    if comp["faltantes"]:
        extra.append({"prioridad": "alta" if c["est"]["semestre_actual"] >= 6 else "media", "tipo": "competencias_digitales",
                      "mensaje": "Inscribe el curso de los pilares de competencias digitales que no aprobaste en la prueba: "
                                 + ", ".join(comp["faltantes"]) + "."})
    if horas and not horas["completo"]:
        extra.append({"prioridad": "media" if c["est"]["semestre_actual"] >= 7 else "baja", "tipo": "horas_libres",
                      "mensaje": f"Suma horas libres: te faltan {horas['horas_faltantes']} de {horas['horas_requeridas']}."})
    if extra:
        orden = {"alta": 0, "media": 1, "baja": 2}
        recs = [r for r in salida["recomendaciones"] if r["tipo"] != "general"] + extra
        salida["recomendaciones"] = sorted(recs, key=lambda r: orden[r["prioridad"]])[:7]
    salida["competencias_digitales"] = {"faltantes": comp["faltantes"], "cumplido": comp["cumplido"]}
    salida["horas_libres"] = horas
    return {"estudiante": _identidad(c["est"]), "periodo_actual": c["periodo"], **salida}


def _fecha_valida(texto: str | None) -> str | None:
    if not texto:
        return None
    try:
        return date.fromisoformat(texto[:10]).isoformat()
    except ValueError:
        raise ErrorEstudiante("La fecha debe tener el formato AAAA-MM-DD.")


def calendario(repo, desde: str | None = None, categoria: str | None = None) -> dict:
    eventos = repo.calendario(_fecha_valida(desde), (categoria or "").strip() or None)
    return {"total": len(eventos), "eventos": eventos,
            "nota": "Los eventos con verificado=false son fechas de demostración, no oficiales."}


def noticias(repo, limite: int = 5, categoria: str | None = None) -> dict:
    """Noticias del día (educación, tecnología, ingeniería de sistemas y vida UNAB) con fuente y fecha.

    Primero las de hoy (hora de Colombia); si hay menos que `limite`, se completa con las más recientes.
    """
    limite = max(1, min(int(limite), 30))
    items = repo.noticias(limite, (categoria or "").strip() or None)
    de_hoy = sum(1 for n in items if n.get("es_hoy"))
    return {"fecha_consulta": datetime.now(ZONA_CO).date().isoformat(), "total": len(items), "de_hoy": de_hoy,
            "categorias": sorted({n["categoria"] for n in items if n.get("categoria")}), "noticias": items}


def buscar_profesor(repo, texto: str) -> dict:
    texto = (texto or "").strip()
    if len(texto) < 2:
        return {"error": "Escribe al menos 2 letras del nombre o la unidad."}
    prof = repo.buscar_profesor(texto)
    return {"total": len(prof), "profesores": prof, "fuente": "APOLO UNAB (datos públicos)"}


def info_curso(repo, texto: str) -> dict:
    texto = (texto or "").strip()
    if len(texto) < 2:
        return {"error": "Escribe el nombre o código del curso."}
    cursos = repo.buscar_curso(texto)
    return {"total": len(cursos), "cursos": cursos,
            "nota": "Prerrequisitos con es_simulado=true son inventados para el demo: la UNAB no los publica."}


def buscar_documentos(repo, embedder, pregunta: str, k: int = 5) -> dict:
    pregunta = (pregunta or "").strip()
    if not pregunta:
        return {"error": "La pregunta no puede estar vacía."}
    k = max(1, min(int(k), 10))
    vec = embedder(pregunta)
    frags = repo.match_documentos(vec, k)
    return {"total": len(frags), "fragmentos": frags}
