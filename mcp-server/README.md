# Servidor MCP del chatbot académico

Servidor FastMCP (Python) que expone 14 herramientas de consulta sobre PostgreSQL (Supabase) por HTTP streamable. Las herramientas solo leen; la única escritura del servidor es el alta automática descrita abajo.
Lo consume el agente académico del flujo 03 de n8n (nodo MCP Client Tool) y cualquier cliente MCP con HTTP streamable.

- Endpoint: `http://<host>:9000/mcp` (transporte HTTP streamable)
- Autenticación: encabezado `X-API-Key: <MCP_API_KEY>` (sin clave, 401). `GET /health` no la exige.
- Todas las respuestas son JSON. Los errores de validación llegan como `{"error": "..."}`.
- Endpoints REST para la app (n8n los llama en las acciones directas): `POST /api/perfil` con `{"estudiante_codigo"}` y
  `POST /api/noticias` con `{"limite", "categoria"}` (opcionales). Exigen la misma `X-API-Key`.
- **Única escritura:** si llega un código válido que no existe, `app/registro.py` crea un estudiante sintético (siempre el mismo para ese código) con su matrícula, historial del CCD, resultados de competencias y horas libres. Por eso el servidor no es estrictamente de solo lectura; no modifica ni borra datos existentes.

## Herramientas

| Herramienta | Argumentos |
|---|---|
| `perfil_estudiante` | `estudiante_codigo` (ficha con horario, avance, competencias y horas libres) |
| `estado_matricula` | `estudiante_codigo` |
| `avance_plan` | `estudiante_codigo` |
| `proyeccion_semestres` | `estudiante_codigo`, `creditos_por_semestre=18` |
| `requisitos_pendientes` | `estudiante_codigo` |
| `cursos_ccd` | `estudiante_codigo` |
| `competencias_digitales` | `estudiante_codigo` (pilares aprobados y faltantes de la prueba) |
| `horas_libres` | `estudiante_codigo` (horas acumuladas frente a las 96 requeridas) |
| `recomendaciones` | `estudiante_codigo` |
| `calendario` | `desde?`, `categoria?` |
| `noticias` | `limite=5`, `categoria?` (las de hoy primero, con `es_hoy`, fuente y fecha) |
| `buscar_documentos` | `pregunta`, `k=5` (embedding Gemini RETRIEVAL_QUERY, 768, y `match_documentos`) |
| `buscar_profesor` | `texto` |
| `info_curso` | `texto` |

Reglas de negocio (`app/logica.py`): avance = créditos aprobados / 151 créditos del plan oficial (aprobar = nota >= 3.0);
la proyección llena cada semestre hasta `creditos_por_semestre` respetando prerrequisitos, prioriza los cursos
reprobados y supone que lo que está en curso se aprueba; las alertas cubren prerrequisitos que bloquean,
Interacción Digital (CCD Ruta 1) sin aprobar, competencias digitales sin aprobar, horas libres pendientes y rezago frente al
semestre esperado; las recomendaciones son por reglas. Competencias digitales: requisito cumplido si se aprueban los 5 pilares;
horas libres: cumplido desde 96 horas (`estado_competencias` y `estado_horas_libres`).
Los prerrequisitos son simulados (la UNAB no los publica) y así se indica en las respuestas.

## Ejecución

```bash
cp .env.example .env     # completar DATABASE_URL, MCP_API_KEY, GEMINI_API_KEY
pip install -r requirements.txt
python -m app.servidor   # escucha en 0.0.0.0:${MCP_PORT:-9000}
```

Docker:

```bash
docker build -t unab-mcp .
docker run --rm -p 9000:9000 --env-file .env unab-mcp
```

## Prueba rápida con el cliente de fastmcp

```python
import asyncio
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

t = StreamableHttpTransport("http://localhost:9000/mcp", headers={"X-API-Key": "..."})
async def main():
    async with Client(t) as c:
        print((await c.call_tool("avance_plan", {"estudiante_codigo": "U00100001"})).data)
asyncio.run(main())
```

Estudiantes de demostración fijos: `U00100001` (semestre 5, regular), `U00100002` (rezagado),
`U00100003` (adelantado), `U00100004` (nuevo, primer semestre).

## Clientes MCP externos

Cualquier cliente MCP con transporte HTTP streamable puede usar el mismo `/mcp` enviando `X-API-Key`. Para revisarlo a mano:
`npx @modelcontextprotocol/inspector` con la URL `http://IP:9000/mcp` y el encabezado. Desde este repositorio:
`python infra/probar_mcp.py U00179961` lista las herramientas y llama algunas en el servidor desplegado.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest                                   # 37 pasan (lógica y herramientas con repositorio simulado); 6 de integración se omiten
TEST_DATABASE_URL=postgresql://... pytest   # 43 pruebas: se suman 6 de integración contra la base con el seed
```
