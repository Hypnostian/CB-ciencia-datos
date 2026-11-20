"""Acceso a PostgreSQL (psycopg 3 con pool de conexiones). Todas las consultas son parametrizadas."""
from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def a_json(v: Any) -> Any:
    """Convierte fechas y Decimal a tipos serializables en JSON."""
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, dict):
        return {k: a_json(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [a_json(x) for x in v]
    return v


class RepoPG:
    def __init__(self, url: str | None = None, min_size: int = 1, max_size: int = 5):
        url = url or os.environ["DATABASE_URL"]
        self.pool = ConnectionPool(url, min_size=min_size, max_size=max_size, open=False,
                                   kwargs={"row_factory": dict_row, "autocommit": True, "prepare_threshold": None},
                                   timeout=15)
        self.pool.open(wait=True, timeout=30)

    def cerrar(self) -> None:
        self.pool.close()

    def _todos(self, sql: str, params: tuple | dict = ()) -> list[dict]:
        with self.pool.connection() as conn:
            return [a_json(r) for r in conn.execute(sql, params).fetchall()]

    def _uno(self, sql: str, params: tuple | dict = ()) -> dict | None:
        filas = self._todos(sql, params)
        return filas[0] if filas else None

    # --- estudiante y plan -----------------------------------------------------------------
    def estudiante(self, codigo: str) -> dict | None:
        return self._uno(
            """select e.codigo, e.nombres, e.apellidos, e.correo, e.semestre_actual, e.estado, e.fecha_ingreso,
                      e.programa_id, p.nombre as programa, p.total_creditos
               from estudiantes e join programas p on p.id = e.programa_id where e.codigo = %s""", (codigo,))

    def asegurar_estudiante(self, codigo: str) -> bool:
        """Crea un estudiante sintético para un código válido que aún no existe (ver registro.py)."""
        from . import registro
        with self.pool.connection() as conn:
            return registro.asegurar(conn, codigo)

    def periodo_actual(self) -> dict | None:
        return self._uno("select id, nombre, fecha_inicio, fecha_fin from periodos where actual limit 1")

    def matricula_actual(self, codigo: str) -> list[dict]:
        return self._todos(
            """select nrc, curso_codigo, curso, creditos, profesor, horario
               from v_estado_matricula where estudiante_codigo = %s order by curso""", (codigo,))

    def cursos_estudiante(self, codigo: str) -> list[dict]:
        return self._todos(
            """select curso_id as id, curso_codigo as codigo, curso as nombre, creditos, semestre_plan, tipo,
                      estado, intentos_reprobados, mejor_nota
               from v_cursos_estudiante where estudiante_codigo = %s order by semestre_plan, curso_codigo""", (codigo,))

    def prerrequisitos(self, programa_id: int) -> dict[int, list[dict]]:
        filas = self._todos(
            """select p.curso_id, p.requisito_id, p.es_simulado
               from prerrequisitos p join cursos c on c.id = p.curso_id where c.programa_id = %s""", (programa_id,))
        reqs: dict[int, list[dict]] = {}
        for f in filas:
            reqs.setdefault(f["curso_id"], []).append({"requisito_id": f["requisito_id"], "es_simulado": f["es_simulado"]})
        return reqs

    # --- CCD ---------------------------------------------------------------------------------
    def catalogo_ccd(self) -> list[dict]:
        return self._todos("select id, ruta, nombre, obligatorio, descripcion, fuente_url from cursos_ccd order by ruta, id")

    def historial_ccd(self, codigo: str) -> list[dict]:
        return self._todos(
            """select curso_ccd_id, curso_ccd, ruta, estado, periodo_id, fecha
               from v_historial_ccd where estudiante_codigo = %s order by periodo_id""", (codigo,))

    # --- Competencias Digitales R2025 y horas libres ----------------------------------------------
    def competencias(self, codigo: str) -> list[dict]:
        return self._todos(
            """select orden, competencia, aprobada, materia, fecha_prueba
               from v_competencias_estudiante where estudiante_codigo = %s order by orden""", (codigo,))

    def horas_libres(self, codigo: str) -> dict | None:
        return self._uno("select horas_cumplidas, horas_requeridas, actualizado from horas_libres where estudiante_codigo = %s",
                         (codigo,))

    def asegurar_requisitos(self, codigo: str) -> bool:
        """Crea los resultados de la prueba y las horas libres de un estudiante que aún no los tiene."""
        from . import registro
        with self.pool.connection() as conn:
            with conn.transaction():
                return registro.asegurar_requisitos(conn, codigo)

    # --- calendario, noticias -----------------------------------------------------------------
    def calendario(self, desde: str | None, categoria: str | None) -> list[dict]:
        return self._todos(
            """select evento, categoria, fecha_inicio, fecha_fin, verificado, fuente_url
               from calendario_academico
               where coalesce(fecha_fin, fecha_inicio) >= coalesce(%(desde)s::date, current_date)
                 and (%(cat)s::text is null or norm_texto(categoria) like '%%' || norm_texto(%(cat)s) || '%%')
               order by fecha_inicio""", {"desde": desde, "cat": categoria})

    def noticias(self, limite: int, categoria: str | None) -> list[dict]:
        """Noticias más recientes; `es_hoy` compara la fecha con el día actual en Colombia."""
        return self._todos(
            """select titulo, url, fecha, categoria, resumen, fuente,
                      (fecha at time zone 'America/Bogota')::date = (now() at time zone 'America/Bogota')::date as es_hoy
               from noticias
               where (%(cat)s::text is null or norm_texto(categoria) like '%%' || norm_texto(%(cat)s) || '%%')
               order by fecha desc nulls last limit %(lim)s""", {"cat": categoria, "lim": limite})

    # --- búsquedas ----------------------------------------------------------------------------
    def buscar_profesor(self, texto: str, limite: int = 10) -> list[dict]:
        return self._todos(
            """select nombre, unidad, cargo, apolo_url, cvlac_url from profesores
               where norm_texto(nombre) like '%%' || norm_texto(%(t)s) || '%%'
                  or norm_texto(unidad) like '%%' || norm_texto(%(t)s) || '%%'
               order by nombre limit %(lim)s""", {"t": texto, "lim": limite})

    def buscar_curso(self, texto: str, limite: int = 5) -> list[dict]:
        cursos = self._todos(
            """select id, codigo, nombre, creditos, semestre_plan, tipo, es_oficial from cursos
               where norm_texto(nombre) like '%%' || norm_texto(%(t)s) || '%%' or lower(codigo) = lower(%(t)s)
               order by semestre_plan, nombre limit %(lim)s""", {"t": texto, "lim": limite})
        for c in cursos:
            c["prerrequisitos"] = self._todos(
                """select r.codigo, r.nombre, r.creditos, p.es_simulado from prerrequisitos p
                   join cursos r on r.id = p.requisito_id where p.curso_id = %s order by r.semestre_plan""", (c["id"],))
            c["es_requisito_de"] = self._todos(
                """select d.codigo, d.nombre from prerrequisitos p join cursos d on d.id = p.curso_id
                   where p.requisito_id = %s order by d.semestre_plan""", (c["id"],))
        return cursos

    def match_documentos(self, embedding: list[float], k: int) -> list[dict]:
        vec = "[" + ",".join(f"{x:.7f}" for x in embedding) + "]"
        return self._todos(
            "select id, documento_id, titulo, fuente_url, contenido, similitud from match_documentos(%s::vector, %s)", (vec, k))
