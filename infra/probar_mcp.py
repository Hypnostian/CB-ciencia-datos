"""
Llama las herramientas del servidor MCP desplegado en EC2 (lista de herramientas, competencias digitales y horas libres).

Lee MCP_URL y MCP_API_KEY del .env de la raíz y no los imprime. Requiere: pip install fastmcp

Uso (desde la raíz del proyecto):
    python infra/probar_mcp.py U00134229 U00100003
"""
import asyncio
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def leer_env() -> dict:
    datos = {}
    for linea in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in linea and not linea.strip().startswith("#"):
            k, v = linea.split("=", 1)
            datos[k.strip()] = v.strip()
    return datos


async def main() -> None:
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport
    env = leer_env()
    transporte = StreamableHttpTransport(env["MCP_URL"].rstrip("/") + "/mcp", headers={"X-API-Key": env["MCP_API_KEY"]})
    async with Client(transporte) as c:
        nombres = sorted(h.name for h in await c.list_tools())
        print(f"herramientas ({len(nombres)}):", nombres)
        for codigo in sys.argv[1:]:
            comp = (await c.call_tool("competencias_digitales", {"estudiante_codigo": codigo})).structured_content
            horas = (await c.call_tool("horas_libres", {"estudiante_codigo": codigo})).structured_content
            print(codigo, comp["estudiante"]["nombre"], "| aprobadas:", comp["aprobadas"], "| faltan:", comp["faltantes"],
                  "| horas:", horas["horas_cumplidas"], "completo:", horas["completo"])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
