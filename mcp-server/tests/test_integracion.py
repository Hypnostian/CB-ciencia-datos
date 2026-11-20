"""Pruebas contra una base real con migraciones y seed cargados. Se omiten sin TEST_DATABASE_URL."""
import asyncio
import os

import pytest
from fastmcp import Client

from app.servidor import crear_servidor

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL no definida")


@pytest.fixture(scope="module")
def mcp():
    from app.repo import RepoPG
    repo = RepoPG(URL)
    yield crear_servidor(repo, lambda t: [0.01] * 768)
    repo.cerrar()


def llamar(mcp, nombre, args):
    async def go():
        async with Client(mcp) as c:
            r = await c.call_tool(nombre, args)
            return r.structured_content or r.data
    return asyncio.run(go())


@pytest.mark.parametrize("cod", ["U00100001", "U00100002", "U00100003", "U00100004"])
def test_estudiantes_demo(mcp, cod):
    av = llamar(mcp, "avance_plan", {"estudiante_codigo": cod})
    assert 0 <= av["porcentaje_avance"] <= 100 and av["creditos_totales"] == 151
    pr = llamar(mcp, "proyeccion_semestres", {"estudiante_codigo": cod})
    assert pr["semestres_restantes"] >= 1
    assert llamar(mcp, "recomendaciones", {"estudiante_codigo": cod})["recomendaciones"]


def test_buscar_documentos_con_embedding_simulado(mcp):
    r = llamar(mcp, "buscar_documentos", {"pregunta": "reglamento", "k": 2})
    assert r["total"] >= 0 and all(-1.0001 <= f["similitud"] <= 1.0001 for f in r["fragmentos"])  # coseno: de -1 a 1


def test_calendario_y_curso(mcp):
    assert llamar(mcp, "calendario", {"categoria": "ccd", "desde": "2026-01-01"})["total"] == 3
    assert llamar(mcp, "info_curso", {"texto": "calculo integral"})["total"] == 1
