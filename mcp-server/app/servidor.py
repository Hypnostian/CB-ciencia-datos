"""Servidor MCP (FastMCP) del chatbot académico: HTTP streamable en 0.0.0.0:${MCP_PORT:-9000}/mcp.

Cada solicitud debe traer el encabezado X-API-Key igual a MCP_API_KEY (excepto GET /health).
"""

import asyncio
import hmac
import json
import os
from typing import Annotated, Callable

from fastmcp import FastMCP
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import servicio as sv


class ClaveApiMiddleware:
    """Middleware ASGI: exige X-API-Key. Deja pasar los eventos de ciclo de vida y /health."""

    def __init__(self, app, clave: str, rutas_libres: tuple[str, ...] = ("/health",)):
        if not clave:
            raise ValueError("MCP_API_KEY es obligatoria")
        self.app, self.clave, self.libres = app, clave.encode(), rutas_libres

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] not in self.libres:
            enviada = dict(scope["headers"]).get(b"x-api-key", b"")
            if not hmac.compare_digest(enviada, self.clave):
                cuerpo = json.dumps({"error": "X-API-Key inválida o ausente"}).encode()
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(cuerpo)).encode())]})
                await send({"type": "http.response.body", "body": cuerpo})
                return
        await self.app(scope, receive, send)


def crear_servidor(repo, embedder: Callable[[str], list[float]]) -> FastMCP:
    mcp = FastMCP(
        "unab-academico",
        instructions=("Herramientas de consulta académica para estudiantes de Ingeniería de Sistemas (datos sintéticos que "
                      "simulan Banner-Cosmos, más documentos oficiales de la UNAB). Todas devuelven JSON."),
    )
    Cod = Annotated[str, Field(description="Código del estudiante, formato U00 + 6 dígitos (ej. U00123456)")]

    @mcp.custom_route("/health", methods=["GET"])
    async def salud(_: Request) -> JSONResponse:
        return JSONResponse({"estado": "ok"})

    @mcp.custom_route("/api/perfil", methods=["POST"])
    async def perfil_http(request: Request) -> JSONResponse:
        """Ficha del estudiante para la app (vía n8n). Protegida por X-API-Key como /mcp."""
        try:
            cuerpo = await request.json()
        except Exception:
            return JSONResponse({"error": "El cuerpo debe ser JSON con estudiante_codigo."}, status_code=400)
        try:
            perfil = await asyncio.to_thread(sv.perfil_estudiante, repo, str(cuerpo.get("estudiante_codigo", "")))
        except sv.ErrorEstudiante as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        return JSONResponse({"perfil": perfil})

    @mcp.custom_route("/api/noticias", methods=["POST"])
    async def noticias_http(request: Request) -> JSONResponse:
        """Noticias del día para la pantalla de noticias de la app (vía n8n). Protegida por X-API-Key."""
        try:
            cuerpo = await request.json()
        except Exception:
            cuerpo = {}
        try:
            limite = int((cuerpo or {}).get("limite") or 20)
        except (TypeError, ValueError):
            limite = 20
        datos = await asyncio.to_thread(sv.noticias, repo, limite, (cuerpo or {}).get("categoria"))
        return JSONResponse({"noticias": datos})

    @mcp.tool
    @sv.con_errores
    def perfil_estudiante(estudiante_codigo: Cod) -> dict:
        """Nombre del estudiante, programa, semestre, horario del periodo actual (NRC, curso, docente, horario) y avance."""
        return sv.perfil_estudiante(repo, estudiante_codigo)

    @mcp.tool
    @sv.con_errores
    def estado_matricula(estudiante_codigo: Cod) -> dict:
        """Periodo actual, cursos inscritos (NRC, curso, créditos, profesor, horario) y créditos inscritos."""
        return sv.estado_matricula(repo, estudiante_codigo)

    @mcp.tool
    @sv.con_errores
    def avance_plan(estudiante_codigo: Cod) -> dict:
        """Créditos aprobados y totales, porcentaje de avance, y cursos aprobados y pendientes por semestre."""
        return sv.avance_plan(repo, estudiante_codigo)

    @mcp.tool
    @sv.con_errores
    def proyeccion_semestres(estudiante_codigo: Cod,
                             creditos_por_semestre: Annotated[int, Field(description="Créditos máximos por semestre", ge=6, le=24)] = 18) -> dict:
        """Semestres restantes estimados y propuesta de cursos por semestre respetando prerrequisitos."""
        return sv.proyeccion_semestres(repo, estudiante_codigo, creditos_por_semestre)

    @mcp.tool
    @sv.con_errores
    def requisitos_pendientes(estudiante_codigo: Cod) -> dict:
        """Alertas: cursos bloqueados por prerrequisito, CCD obligatorio sin aprobar, competencias digitales y horas libres
        pendientes, y rezago frente al semestre esperado."""
        return sv.requisitos_pendientes(repo, estudiante_codigo)

    @mcp.tool
    @sv.con_errores
    def cursos_ccd(estudiante_codigo: Cod) -> dict:
        """Cursos del Centro de Competencias Digitales tomados, rutas cumplidas y faltantes para la insignia digital."""
        return sv.cursos_ccd(repo, estudiante_codigo)

    @mcp.tool
    @sv.con_errores
    def competencias_digitales(estudiante_codigo: Cod) -> dict:
        """Requisito de grado Competencias Digitales R2025: resultado de la prueba en cada pilar (Vida en línea, MS Word,
        MS Excel, MS PowerPoint, Cultura digital), cuáles aprobó, cuáles le faltan y si el requisito está cumplido."""
        return sv.competencias_digitales(repo, estudiante_codigo)

    @mcp.tool
    @sv.con_errores
    def horas_libres(estudiante_codigo: Cod) -> dict:
        """Horas libres acumuladas, las 96 requeridas para graduarse, cuántas faltan y si ya completó el requisito."""
        return sv.horas_libres(repo, estudiante_codigo)

    @mcp.tool
    @sv.con_errores
    def recomendaciones(estudiante_codigo: Cod) -> dict:
        """Recomendaciones personalizadas: carga sugerida, cursos sugeridos y alertas a atender."""
        return sv.recomendaciones(repo, estudiante_codigo)

    @mcp.tool
    @sv.con_errores
    def calendario(desde: Annotated[str | None, Field(description="Fecha AAAA-MM-DD; por defecto hoy")] = None,
                   categoria: Annotated[str | None, Field(description="Filtro por categoría, ej. ccd")] = None) -> dict:
        """Eventos del calendario académico desde una fecha."""
        return sv.calendario(repo, desde, categoria)

    @mcp.tool
    @sv.con_errores
    def noticias(limite: Annotated[int, Field(ge=1, le=30)] = 5,
                 categoria: Annotated[str | None, Field(description="Educación, Tecnología, Ingeniería de Sistemas o Vida UNAB")] = None) -> dict:
        """Noticias del día (educación, tecnología, ingeniería de sistemas y vida UNAB), cada una con fuente, fecha y es_hoy."""
        return sv.noticias(repo, limite, categoria)

    @mcp.tool
    @sv.con_errores
    def buscar_documentos(pregunta: Annotated[str, Field(description="Pregunta en lenguaje natural")],
                          k: Annotated[int, Field(ge=1, le=10)] = 5) -> dict:
        """Búsqueda semántica (RAG) en documentos institucionales: devuelve fragmentos con título y URL de fuente."""
        return sv.buscar_documentos(repo, embedder, pregunta, k)

    @mcp.tool
    @sv.con_errores
    def buscar_profesor(texto: Annotated[str, Field(description="Parte del nombre o de la unidad académica")]) -> dict:
        """Profesores de APOLO por nombre o unidad, con el enlace a su perfil público."""
        return sv.buscar_profesor(repo, texto)

    @mcp.tool
    @sv.con_errores
    def info_curso(texto: Annotated[str, Field(description="Nombre o código del curso")]) -> dict:
        """Curso del plan: créditos, semestre y prerrequisitos (los simulados vienen marcados)."""
        return sv.info_curso(repo, texto)

    return mcp


def crear_app(mcp: FastMCP, clave: str):
    """App ASGI con ruta /mcp (HTTP streamable) protegida por X-API-Key."""
    return ClaveApiMiddleware(mcp.http_app(path="/mcp", transport="streamable-http"), clave)


def main() -> None:
    import uvicorn

    from .embeddings import embedding_consulta
    from .repo import RepoPG

    clave = os.environ.get("MCP_API_KEY", "")
    if not clave:
        raise SystemExit("Falta MCP_API_KEY: el servidor no arranca sin clave.")
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("Falta DATABASE_URL.")
    app = crear_app(crear_servidor(RepoPG(), embedding_consulta), clave)
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("MCP_PORT", "9000")), log_level="info")


if __name__ == "__main__":
    main()
