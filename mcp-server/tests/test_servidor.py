import asyncio

import httpx
import pytest
from fastmcp import Client

from app.servidor import ClaveApiMiddleware, crear_app, crear_servidor
from tests.datos_falsos import PILARES, RepoFalso

HERRAMIENTAS = {"estado_matricula", "avance_plan", "proyeccion_semestres", "requisitos_pendientes", "cursos_ccd",
                "recomendaciones", "calendario", "noticias", "buscar_documentos", "buscar_profesor", "info_curso",
                "perfil_estudiante", "competencias_digitales", "horas_libres"}
COD = "U00123456"


def servidor(repo=None):
    return crear_servidor(repo or RepoFalso({"A": "aprobado", "D": "aprobado"}), lambda t: [0.0] * 768)


async def llamar(mcp, nombre, args):
    async with Client(mcp) as c:
        r = await c.call_tool(nombre, args)
        return r.structured_content or r.data


def test_herramientas_exactas():
    async def go():
        async with Client(servidor()) as c:
            return {t.name for t in await c.list_tools()}
    assert asyncio.run(go()) == HERRAMIENTAS


@pytest.mark.parametrize("nombre", ["estado_matricula", "avance_plan", "proyeccion_semestres", "requisitos_pendientes",
                                    "cursos_ccd", "recomendaciones", "competencias_digitales", "horas_libres"])
def test_herramientas_de_estudiante(nombre):
    r = asyncio.run(llamar(servidor(), nombre, {"estudiante_codigo": COD}))
    assert r["estudiante"]["codigo"] == COD


def test_competencias_digitales_faltantes():
    r = asyncio.run(llamar(servidor(), "competencias_digitales", {"estudiante_codigo": COD}))
    assert r["aprobadas"] == ["Vida en línea", "MS Word"]
    assert r["faltantes"] == ["MS Excel", "MS PowerPoint", "Cultura digital"]
    assert r["cumplido"] is False and r["total_pilares"] == 5
    assert r["competencias"][0]["cumplida_con"] == "Examen Vida en línea"


def test_competencias_completas_y_horas_cumplidas():
    repo = RepoFalso(aprobadas=PILARES, horas=104)
    r = asyncio.run(llamar(servidor(repo), "competencias_digitales", {"estudiante_codigo": COD}))
    assert r["cumplido"] is True and r["faltantes"] == []
    h = asyncio.run(llamar(servidor(repo), "horas_libres", {"estudiante_codigo": COD}))
    assert h["completo"] is True and h["horas_adicionales"] == 8 and "ya completaste" in h["mensaje"]


def test_horas_libres_pendientes_y_alertas():
    h = asyncio.run(llamar(servidor(), "horas_libres", {"estudiante_codigo": COD}))
    assert (h["horas_cumplidas"], h["horas_faltantes"], h["completo"]) == (40, 56, False)
    al = asyncio.run(llamar(servidor(), "requisitos_pendientes", {"estudiante_codigo": COD}))["alertas"]
    assert {"competencias_digitales", "horas_libres"} <= {a["tipo"] for a in al}


def test_perfil_trae_competencias_y_horas():
    p = asyncio.run(llamar(servidor(), "perfil_estudiante", {"estudiante_codigo": COD}))
    assert p["competencias_digitales"]["total_aprobadas"] == 2
    assert p["horas_libres"]["horas_requeridas"] == 96


def test_estado_matricula_creditos():
    r = asyncio.run(llamar(servidor(), "estado_matricula", {"estudiante_codigo": COD}))
    assert r["creditos_inscritos"] == 3 and r["periodo_actual"] == "2026-2"


def test_proyeccion_con_argumento():
    r = asyncio.run(llamar(servidor(), "proyeccion_semestres", {"estudiante_codigo": COD, "creditos_por_semestre": 12}))
    assert r["creditos_por_semestre"] == 12 and r["semestres_restantes"] >= 2


def test_codigo_invalido_y_no_existente():
    assert "inválido" in asyncio.run(llamar(servidor(), "avance_plan", {"estudiante_codigo": "123"}))["error"]
    assert "No existe" in asyncio.run(llamar(servidor(), "avance_plan", {"estudiante_codigo": "U00999999"}))["error"]


def test_herramientas_sin_estudiante():
    mcp = servidor()
    assert asyncio.run(llamar(mcp, "calendario", {"categoria": "ccd"}))["total"] == 1
    n = asyncio.run(llamar(mcp, "noticias", {"limite": 3}))
    assert n["total"] == 2 and n["de_hoy"] == 1 and n["categorias"] == ["Educación", "Tecnología"]
    assert asyncio.run(llamar(mcp, "noticias", {"categoria": "tecno"}))["noticias"][0]["fuente"] == "El Tiempo"
    assert asyncio.run(llamar(mcp, "buscar_profesor", {"texto": "profe"}))["total"] == 1
    r = asyncio.run(llamar(mcp, "info_curso", {"texto": "integral"}))
    assert r["cursos"][0]["prerrequisitos"][0]["es_simulado"] is True
    assert "AAAA-MM-DD" in asyncio.run(llamar(mcp, "calendario", {"desde": "mañana"}))["error"]


def test_buscar_documentos_con_embedding_simulado():
    repo = RepoFalso()
    r = asyncio.run(llamar(servidor(repo), "buscar_documentos", {"pregunta": "¿cuándo es la matrícula?", "k": 3}))
    assert r["fragmentos"][0]["fuente_url"] == "https://x"
    assert len(repo.ultimo_vector) == 768


def test_api_key():
    async def go():
        app = crear_app(servidor(), "secreta")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            sin = await c.post("/mcp", json={})
            mala = await c.post("/mcp", json={}, headers={"X-API-Key": "otra"})
            salud = await c.get("/health")
            return sin.status_code, mala.status_code, salud.status_code
    assert asyncio.run(go()) == (401, 401, 200)


def test_middleware_exige_clave():
    with pytest.raises(ValueError):
        ClaveApiMiddleware(object(), "")


def test_api_noticias_para_la_app():
    from starlette.testclient import TestClient
    app = servidor().http_app()
    with TestClient(app) as cliente:
        r = cliente.post("/api/noticias", json={"limite": 5})
    assert r.status_code == 200
    datos = r.json()["noticias"]
    assert datos["de_hoy"] == 1 and datos["noticias"][0]["es_hoy"] is True
