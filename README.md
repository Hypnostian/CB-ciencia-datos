# Asistente Académico UNAB (n8n + MCP + RAG)

Trabajo final del curso **Ciencia de Datos** (segundo corte). Es un modelo en **n8n** que apoya al estudiante de
**Ingeniería de Sistemas** de la UNAB con su matrícula, su estado académico actual y su proyección, los requisitos que le faltan y
recomendaciones para tener éxito en el programa, con el enfoque de **educación de precisión** y **autoaprendizaje**.

Componentes: base de datos **PostgreSQL** (Supabase con pgvector), **n8n** con agentes de IA (Gemini), **RAG** sobre documentos
oficiales de la UNAB, **servidor MCP** en AWS con herramientas que consultan la base, **scraper** de noticias del día, **webhook** de n8n
y una **app Android** nativa conectada al webhook. Las capturas de este README son ejecuciones reales y los resultados de las pruebas de
extremo a extremo (23 de 25 en la primera ejecución; los dos fallos se corrigieron y pasaron en la reprueba) están en [`docs/pruebas.md`](docs/pruebas.md).

Enlaces rápidos: [manual de usuario](docs/manual_usuario.md), [arquitectura](docs/arquitectura.md), [parámetros y por qué](docs/parametros.md),
[pruebas y evidencia](docs/pruebas.md), [RAG](docs/rag.md) y [seguridad de la instancia](infra/SECURITY_GROUPS.md).

<table>
<tr>
<td><img src="docs/capturas/21_app_inicio.jpg" width="230" alt="Inicio del chat con avance, competencias y horas libres"></td>
<td><img src="docs/capturas/25_app_recomendaciones.jpg" width="230" alt="Recomendaciones personalizadas"></td>
<td><img src="docs/capturas/30_app_noticias_del_dia.jpg" width="230" alt="Noticias del día con fuente y fecha"></td>
<td><img src="docs/capturas/31_app_perfil.jpg" width="230" alt="Perfil con avance y competencias digitales"></td>
</tr>
</table>

> **Datos.** El plan de estudios (documento oficial de 151 créditos), los documentos del RAG, los profesores, el calendario y las
> noticias son **oficiales** y guardan su URL. Los estudiantes, matrículas, notas, NRC, resultados de la prueba de competencias
> digitales, horas libres y prerrequisitos son **sintéticos** (la UNAB no publica prerrequisitos) y están marcados como tales.

## Contenido
1. [Qué hace](#qué-hace)
2. [Arquitectura](#arquitectura)
3. [Cómo cumple la rúbrica y dónde está cada criterio](#cómo-cumple-la-rúbrica)
4. [Instalación](#instalación)
5. [Paso a paso de cómo se construyó](#paso-a-paso-de-cómo-se-construyó)
6. [Códigos de prueba](#códigos-de-prueba)
7. [Pertinencia pedagógica](#pertinencia-pedagógica)
8. [Contrato del webhook](#contrato-del-webhook)
9. [Estructura del repositorio](#estructura-del-repositorio)
10. [Pruebas](#pruebas)
11. [Seguridad](#seguridad)
12. [Documentación](#documentación)

## Qué hace

| Consulta del estudiante | Ejemplo | Cómo se responde |
|---|---|---|
| **Matrícula** | ¿En qué materias estoy matriculado y con qué profesores? | Agente 03 con la herramienta MCP `estado_matricula` (NRC, horario, docente) |
| **Estado académico** | ¿Cómo voy en mi plan de estudios? | `avance_plan`: créditos aprobados frente a los 151 del plan, semestre real |
| **Proyección** | ¿Cuántos semestres me faltan? | `proyeccion_semestres`: llena los semestres futuros respetando prerrequisitos |
| **Recomendaciones** | ¿Qué cursos debo tomar? | `recomendaciones` y `requisitos_pendientes`: carga sugerida, cursos y alertas |
| **Requisitos de grado** | ¿Qué competencias digitales me faltan? ¿Cuántas horas libres llevo? | `competencias_digitales` (5 pilares R2025) y `horas_libres` (96 requeridas) |
| **Reglamento y procesos** | ¿Cuándo un estudiante queda en prueba académica? | **RAG**: embeddings en pgvector y respuesta citando la fuente oficial |
| **Calendario** | ¿Cuándo son las inscripciones? | Google Sheets con las fechas del calendario académico |
| **Noticias del día** | ¿Qué noticias de tecnología hay hoy? | **Scraper** cada 6 horas (UNAB, El Tiempo, Google Noticias) |

La app tiene además una pantalla de **Noticias del día** y la ficha **Mi perfil y horario**, que llegan por el mismo webhook.

## Arquitectura

![Arquitectura del sistema](docs/capturas/00_arquitectura.png)

```mermaid
sequenceDiagram
  participant A as App Android
  participant W as n8n 00 (webhook)
  participant G as Gemini
  participant S as Subflujo 01 a 04
  participant M as Servidor MCP (AWS)
  participant D as Supabase (PostgreSQL + pgvector)
  A->>W: POST /webhook/unab-chat {estudiante_codigo, session_id, mensaje} + X-Chat-Token
  W->>W: guardrails de entrada (token, formato, inyección, credenciales, datos ajenos)
  W->>G: clasificar intención (JSON con 6 etiquetas)
  W->>S: Execute Workflow según la intención
  alt cursos o matrícula (03)
    S->>M: herramientas MCP con X-API-Key
    M->>D: SQL parametrizado
  else general (01, RAG)
    S->>G: embedding de la pregunta
    S->>D: match_documentos(vector, 5)
  end
  S->>G: agente con contexto y memoria (n8n_chat_histories)
  S-->>W: {respuesta, intencion, fuentes}
  W->>W: guardrails de salida
  W-->>A: JSON del contrato
```

| Componente | Carpeta | Dónde corre | Para qué |
|---|---|---|---|
| App Android | `android/` | Emulador o teléfono | Ingreso con el código, chat, perfil, noticias del día |
| Orquestación y agentes | `n8n/workflows/` | n8n Cloud | Webhook, guardrails, clasificación, 4 agentes con memoria, scraper programado |
| LLM y embeddings | (API) | Google Gemini | `gemini-3.5-flash-lite` y `gemini-embedding-001` (768 dimensiones) |
| Servidor MCP | `mcp-server/` | AWS EC2 (AWS Academy), puerto 9000 | 14 herramientas de consulta sobre la base (la única escritura es el alta automática de un estudiante sintético) y 2 endpoints REST para la app |
| Base de datos | `db/` | Supabase | Modelo académico (simula Banner), requisitos, RAG, noticias y memoria |
| RAG | `rag/` | Equipo local o flujo 05 | Fragmentos de documentos oficiales con embeddings en pgvector |
| Scraper | `scraper/` y flujo 04 | n8n cada 6 horas | Noticias del día de educación, tecnología e ingeniería de sistemas |

Modelo de datos y pipeline RAG:

![Modelo de datos](docs/capturas/00b_modelo_datos.png)

![Pipeline RAG](docs/capturas/00c_pipeline_rag.png)

### Decisiones de diseño

| Decisión | Por qué |
|---|---|
| n8n como orquestador con **subflujos** (Execute Workflow) | Cada capacidad (RAG, calendario, agente académico, noticias) se prueba, se ve y se cambia por separado |
| **Clasificador de intención** con salida JSON restringida | Una llamada barata (temperatura 0) decide el camino; si falla se usa el RAG. Cada valor numérico (temperaturas, memoria, k, umbral, reintentos) está justificado en [`docs/parametros.md`](docs/parametros.md) |
| Datos del estudiante por un **servidor MCP** y no con SQL dentro de n8n | El agente solo puede usar herramientas de consulta validadas; la lógica (avance, proyección, alertas) se prueba con 43 pruebas (37 sin base y 6 de integración); el mismo servidor sirve a cualquier cliente MCP |
| **Supabase** con pgvector | Una sola base para el modelo relacional, los vectores (índice HNSW) y la memoria del chat; plan gratuito |
| Embeddings de **768 dimensiones** | `gemini-embedding-001` permite reducir la dimensión (por defecto 3072): el índice ocupa la cuarta parte y, con 768, las 25 preguntas de prueba recuperan el documento correcto de primero (no se comparó contra 3072) |
| Fragmentos de **800 tokens con solape de 120** | Medido: casi todos los artículos del reglamento caben enteros (solo 3 secciones se parten) y el contexto top 5 queda por debajo de 3600 tokens ([detalle](docs/rag.md)) |
| **Guardrails en código** (nodos Code) | Reglas determinísticas y auditables, sin gastar llamadas al LLM |
| Fuentes calculadas por el flujo, no por el LLM | El modelo no puede inventar enlaces: el guardrail de salida quita cualquier URL que no venga de los datos |
| Memoria por `codigo:session_id` en Postgres | Persiste entre sesiones y queda aislada por estudiante |
| **Acciones directas** sin LLM (`perfil`, `noticias`) | La app pinta su ficha y las noticias rápido (menos de 3 s) y sin costo de tokens |
| Plan oficial de **151 créditos** también en el RAG | El avance que calcula la base y el plan que cita el RAG son el mismo |
| AWS EC2 con **IP elástica** y systemd | El laboratorio de AWS Academy apaga la instancia; con la IP fija y el servicio habilitado vuelve solo |

Más detalle en [`docs/arquitectura.md`](docs/arquitectura.md).

## Cómo cumple la rúbrica

| Criterio (peso) | Evidencia en este repositorio |
|---|---|
| Arquitectura del sistema (10 %) | [Diagrama completo](docs/capturas/00_arquitectura.png) con n8n, PostgreSQL, agente/LLM, RAG, servidor MCP, app Android y scraper, flujo de datos numerado y [decisiones de diseño](#decisiones-de-diseño) |
| Implementación de RAG (15 %) | [Pipeline](docs/capturas/00c_pipeline_rag.png), documentos usados (reglamento, plan de estudios, requisitos del CCD), justificación de tamaño de fragmento, solape y modelo de embeddings con [experimento medido](docs/rag.md) [recuperación con consultas reales](docs/capturas/05_rag_recuperacion.png) y [evidencia del umbral de similitud](docs/rag.md#5-umbral-de-similitud-evidencia-medida) (código en [`rag/`](rag/)) |
| Base de datos PostgreSQL (10 %) | [Scripts SQL](db/migrations/) de creación e [inserción](db/seed/seed.sql), [modelo coherente](docs/capturas/00b_modelo_datos.png) (estudiantes, matrícula, materias, notas, prerrequisitos), [acceso al servidor con tablas y datos](docs/capturas/03_bd_tablas_con_datos.png) |
| Workflows de n8n (15 %) | [6 flujos](n8n/workflows/) con agente, modelo Gemini, memoria, herramientas MCP y guardrails; [diagramas](docs/capturas/50_n8n_flujo_00_chat_principal.png) y [una ejecución exitosa nodo por nodo](docs/capturas/18_n8n_ejecucion_exitosa.png) y [parámetros justificados](docs/parametros.md) |
| Servidor MCP y webhook (10 %) | [14 herramientas documentadas](mcp-server/README.md) que consultan la base, [pruebas](docs/capturas/07_servidor_mcp_pruebas.png), webhook probado con [curl](docs/capturas/12_webhook_curl_matricula.png), [colección de Postman](docs/postman/Asistente_UNAB.postman_collection.json), la app y la [verificación de extremo a extremo](docs/pruebas.md) |
| Scraper de noticias (10 %) | [Scraper automático cada 6 horas](docs/capturas/53_n8n_flujo_04_noticias.png) con las [noticias del día con fuente y fecha](docs/capturas/10_scraper_noticias_hoy.png), integrado al [agente](docs/capturas/29_app_noticias_chat.jpg) y a la [app](docs/capturas/30_app_noticias_del_dia.jpg) |
| Aplicación Android (15 %) | App en el emulador con [matrícula](docs/capturas/22_app_matricula.jpg), [estado académico](docs/capturas/23_app_estado_academico.jpg), [proyección](docs/capturas/24_app_proyeccion.jpg) y [recomendaciones](docs/capturas/25_app_recomendaciones.jpg), conectada al webhook |
| Documentación técnica (10 %) | Este README (descripción, arquitectura, instalación, imágenes), el [manual de usuario](docs/manual_usuario.md), la [documentación técnica](docs/documentacion_tecnica.md), los [parámetros y por qué](docs/parametros.md) y las [pruebas](docs/pruebas.md) |
| Pertinencia pedagógica (5 %) | [Respuestas personalizadas y accionables](docs/pertinencia_pedagogica.md), [prompts usados](docs/prompts.md) y evidencia de investigación (educación de precisión, autorregulación, analítica del aprendizaje) |

### Dónde está cada criterio

| Criterio | Dónde mirar primero |
|---|---|
| Arquitectura | [Arquitectura](#arquitectura), [`docs/arquitectura.md`](docs/arquitectura.md), [Decisiones de diseño](#decisiones-de-diseño) |
| RAG | [Paso 3](#paso-3-rag-con-documentos-oficiales), [`docs/rag.md`](docs/rag.md), [`rag/`](rag/), [`rag/evaluacion_umbral.json`](rag/evaluacion_umbral.json) |
| PostgreSQL | [Paso 2](#paso-2-base-de-datos-postgresql-supabase), [`db/migrations/`](db/migrations/), [`db/seed/`](db/seed/) y la equivalencia de nombres de abajo |
| Workflows n8n | [Paso 6](#paso-6-flujos-de-n8n), [`n8n/workflows/`](n8n/workflows/), [`docs/prompts.md`](docs/prompts.md) |
| MCP y webhook | [Paso 4](#paso-4-servidor-mcp-fastmcp-python), [Paso 8](#paso-8-webhook-probado-curl-postman-y-la-app), [`mcp-server/README.md`](mcp-server/README.md), [`docs/CONTRATO.md`](docs/CONTRATO.md) |
| Scraper | [Paso 7](#paso-7-scraper-de-noticias-del-día), [`scraper/`](scraper/) y el flujo 04 |
| App Android | [Paso 9](#paso-9-app-android), [`android/README.md`](android/README.md), [`docs/manual_usuario.md`](docs/manual_usuario.md) |
| Documentación | Este README, [`docs/`](docs/), [`docs/parametros.md`](docs/parametros.md), [`docs/pruebas.md`](docs/pruebas.md) |
| Pertinencia pedagógica | [`docs/pertinencia_pedagogica.md`](docs/pertinencia_pedagogica.md), [`docs/prompts.md`](docs/prompts.md) |

Equivalencia entre los nombres de la rúbrica y las tablas de la base: **materias** = `cursos` (plan) y `secciones` (oferta con NRC, docente y
horario); **matrícula** = `matriculas`; **notas** = `matriculas.nota_final` (no hay una tabla `notas` aparte); **prerrequisitos** =
`prerrequisitos`; **estudiantes** = `estudiantes`.

## Instalación

**Requisitos:** Python 3.12 o superior, una cuenta de Supabase, n8n Cloud, una clave de la API de Gemini, una instancia Ubuntu en AWS
(o cualquier servidor con el puerto 9000 abierto), Android Studio con un JDK de 17 a 23 (el proyecto fija el 23; ver [`android/README.md`](android/README.md)) y Git.

1. Clonar el repositorio y crear el `.env` de la raíz a partir de [`.env.example`](.env.example) (el `.env` nunca se sube a git):

   | Variable | Para qué |
   |---|---|
   | `DATABASE_URL` | Cadena de conexión de Supabase (Session pooler, puerto 5432) |
   | `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_EMBED_MODEL`, `EMBED_DIM` | API de Gemini (`gemini-3.5-flash-lite`, `gemini-embedding-001`, 768) |
   | `MCP_API_KEY`, `MCP_URL`, `MCP_PORT` | Clave del servidor MCP y su dirección (`http://IP:9000`) |
   | `CHAT_TOKEN`, `N8N_WEBHOOK_URL` | Token del webhook y su URL (los usa la app) |
   | `N8N_URL`, `N8N_API_KEY` | Instancia de n8n y token de su MCP (opcionales; los flujos se importan a mano con **Import from File**) |
   | `GOOGLE_SHEET_ID` | Hoja del calendario académico |

2. Base de datos (Supabase): `pip install "psycopg[binary]" faker` y luego
   ```bash
   python db/seed/cargar.py --migrar --regenerar
   ```
3. RAG: `python rag/ingesta.py` (calcula los embeddings y los guarda en pgvector; el flujo 05 de n8n sirve para agregar o refrescar documentos).
4. Servidor MCP: en la instancia, `pip install -r mcp-server/requirements.txt` y el servicio [`infra/cb-mcp.service`](infra/cb-mcp.service)
   (detalle en [`docs/despliegue.md`](docs/despliegue.md)).
5. n8n: crear las credenciales (Gemini API, Supabase Postgres, Google Sheets, MCP API Key) e importar los flujos desde la interfaz de n8n
   (**Workflows > Import from File**, primero 01 a 05 y al final 00; en los nodos *Execute Workflow* del flujo 00 elegir el subflujo
   correspondiente de la lista); asignar las credenciales, poner `CHAT_TOKEN` en el nodo Config del flujo 00 y publicar los seis flujos.
6. App: abrir `android/` en Android Studio, ejecutar en el emulador y escribir la URL del webhook y el token en **Ajustes del webhook**. El APK lo compila
   cada persona: si `android/local.properties` trae la URL y el token, quedan dentro del APK, así que nunca se publica un APK compilado con valores reales.

Comprobación rápida: `python n8n/herramientas/probar_webhook.py "U00179961|¿Cómo voy en mi plan de estudios?"`.

## Paso a paso de cómo se construyó

El orden real fue: datos, base de datos, RAG, servidor MCP, AWS, n8n, scraper, prueba del webhook y app. Cada paso deja algo que el
siguiente usa. Los comandos completos están en [`docs/despliegue.md`](docs/despliegue.md) y el detalle técnico en
[`docs/documentacion_tecnica.md`](docs/documentacion_tecnica.md).

### Paso 1. Datos oficiales y sintéticos

- **Plan de estudios oficial**: el documento de la página del programa de Ingeniería de Sistemas (151 créditos, 8 semestres más la
  práctica). `db/seed/planes.py` lo lee de `data/oficial/unab_planes_estudio.json`, numera las electivas repetidas (I, II, III, IV) y
  agrega 43 prerrequisitos **simulados** (UNAB no los publica).
- **Estudiantes sintéticos**: 120 estudiantes fijos en `db/seed/estudiantes_base.csv` (código, nombre, perfil regular, rezagado,
  adelantado o irregular, periodo de ingreso). `db/seed/generar_datos.py` simula su historia académica periodo a periodo sobre el plan
  oficial: matrícula, notas, cancelaciones, prerrequisitos, historial del Centro de Competencias Digitales, prueba de competencias y
  horas libres. Con la misma semilla produce siempre los mismos datos.

![Generación de los datos con el plan oficial](docs/capturas/01_datos_generar_plan.png)

### Paso 2. Base de datos PostgreSQL (Supabase)

Scripts en [`db/migrations/`](db/migrations/), en orden: extensiones (`vector`), esquema, vistas analíticas, funciones
(`match_documentos`), competencias digitales y horas libres, y seguridad de las vistas (`security_invoker`). El seed con los INSERT
está en [`db/seed/seed.sql`](db/seed/seed.sql). Row Level Security está activo en las 18 tablas.

```bash
python db/seed/cargar.py --migrar        # migraciones 001 a 006 y seed
python db/ver_tablas.py                 # solo lectura: conteo de cada tabla, plan por semestre y un estudiante de ejemplo
```

![Consola con `python db/ver_tablas.py`: filas de cada tabla de la base viva, plan por semestre, prerrequisitos y la matrícula de un estudiante](docs/capturas/02_supabase_cargar_seed.png)

![Tablas con datos, plan por semestre, prerrequisitos y la matrícula con notas de un estudiante](docs/capturas/03_bd_tablas_con_datos.png)

En el panel de Supabase (la dirección del proyecto está oculta):

![Proyecto en Supabase con la base de datos activa en us-east-1](docs/capturas/40_supabase_proyecto.jpg)

![Editor de tablas con los 51 cursos del plan de 151 créditos](docs/capturas/41_supabase_tablas.jpg)

![SQL Editor: competencias digitales y horas libres de una estudiante](docs/capturas/42_supabase_sql_competencias.jpg)

### Paso 3. RAG con documentos oficiales

| Parámetro | Valor | Justificación |
|---|---|---|
| Documentos | 145: Reglamento Estudiantil de Pregrado, plan de estudios de Ingeniería de Sistemas (y los 133 planes de la UNAB), requisitos y cursos del Centro de Competencias Digitales, matrícula, página del programa y profesores | Son las fuentes que responden las dudas de reglamento, plan y requisitos |
| Fragmentación | Por estructura (artículo, capítulo, semestre) y máximo **800 tokens** con `rag/ingesta.py` (el flujo 05 de n8n, para agregar o refrescar documentos, usa límites equivalentes de 3200 caracteres) | Mantiene cada artículo completo: solo 3 secciones necesitan partirse (con 300 tokens serían 21) |
| Solape | **120 tokens** (15 %; 480 caracteres en el flujo 05) | Si un artículo largo se parte, la idea que cruza el corte queda en los dos fragmentos |
| Embeddings | `gemini-embedding-001`, **768 dimensiones**, `RETRIEVAL_DOCUMENT` y `RETRIEVAL_QUERY` | Multilingüe (español), gratuito, con tipos de tarea distintos para documento y pregunta |
| Búsqueda | `match_documentos` (coseno, índice HNSW), **top 5**, umbral **0.35** | El contexto cabe holgado en el modelo. El 0.35 es un filtro de ruido: las preguntas ajenas al dominio también lo superan (0.55 a 0.61), así que la protección de tema la da el clasificador; los datos respaldan 0.65 ([`docs/rag.md`](docs/rag.md)) |
| Resultado medido | 25 preguntas contra el índice real: acierto@1 = 1.00, evidencia en el top 3 = 1.00, similitud promedio 0.76. La comparación de tamaños (17 preguntas) empata en las 4 configuraciones, y 30 preguntas del dominio y ajenas miden el umbral | [docs/rag.md](docs/rag.md) |

```bash
python rag/ingesta.py --dry-run                  # fragmentos sin llamar a la API
python rag/ingesta.py                            # embeddings y carga en pgvector
python rag/consultar.py "¿Cuándo un estudiante queda en prueba académica?"
python rag/evaluar_chunks.py                     # experimento de tamaño de fragmento
python rag/evaluar_umbral.py                     # similitud de preguntas del dominio y ajenas (umbral)
```

![Fragmentación y pruebas del RAG](docs/capturas/04_rag_fragmentacion.png)

![Recuperación con consultas reales](docs/capturas/05_rag_recuperacion.png)

![`rag/evaluar_chunks.py` con los embeddings en caché: experimento de tamaño de fragmento y evaluación del índice (secciones 1 a 3)](docs/capturas/06_rag_evaluacion_chunks.png)

### Paso 4. Servidor MCP (FastMCP, Python)

`mcp-server/` expone **14 herramientas** por HTTP streamable en `:9000/mcp` y exige `X-API-Key` en cada solicitud. Todas consultan la
base con SQL parametrizado; la única escritura del servidor es el alta automática de un estudiante sintético cuando llega un código válido que no existe. Tiene también dos endpoints REST para la app (vía n8n): `/api/perfil` y `/api/noticias`.

| Herramienta | Qué devuelve |
|---|---|
| `perfil_estudiante` | Nombre, programa, semestre, horario del periodo (NRC, curso, docente) y avance |
| `estado_matricula` | Cursos inscritos en el periodo actual con NRC, créditos, profesor y horario |
| `avance_plan` | Créditos aprobados y totales, porcentaje, semestre real y cursos por semestre |
| `proyeccion_semestres` | Semestres futuros llenados respetando prerrequisitos y tope de créditos |
| `requisitos_pendientes` | Alertas: prerrequisitos, CCD obligatorio, competencias digitales, horas libres, rezago |
| `recomendaciones` | Carga sugerida, cursos para el próximo periodo y acciones con prioridad |
| `competencias_digitales` | Resultado de la prueba por pilar, aprobadas y faltantes |
| `horas_libres` | Horas acumuladas frente a las 96 requeridas |
| `cursos_ccd` | Cursos del Centro de Competencias Digitales y rutas de la insignia |
| `info_curso` | Créditos, semestre y prerrequisitos de un curso |
| `buscar_profesor` | Profesores de APOLO por nombre o unidad |
| `calendario` | Eventos del calendario académico |
| `noticias` | Noticias del día con fuente y fecha |
| `buscar_documentos` | Búsqueda semántica en el RAG |

![pytest del servidor MCP: 43 passed con la base de pruebas configurada (37 unitarias y 6 de integración)](docs/capturas/07_servidor_mcp_pruebas.png)

La captura se tomó con la base conectada (43 pruebas). Sin `TEST_DATABASE_URL`, 37 pasan y 6 de integración se omiten; el resultado del 2026-11-20 está en [`docs/pruebas.md`](docs/pruebas.md).

### Paso 5. AWS EC2 (AWS Academy Learner Lab)

La instancia Ubuntu (t2.large, us-east-1) es una instancia **compartida** del laboratorio de AWS Academy, con IP elástica; el servidor corre como
servicio systemd `cb-mcp`. Para este proyecto el Security Group necesita el puerto 9000 abierto a internet (n8n Cloud no tiene IP de salida fija) y
la protección es la `X-API-Key`. La captura muestra además los puertos 22, 80, 443, 8000 y 8080, que pertenecen a otros proyectos de la misma
instancia: qué implica y cómo se endurecería en producción está en [`infra/SECURITY_GROUPS.md`](infra/SECURITY_GROUPS.md). Los identificadores del grupo y de la VPC están difuminados.

![Instancia EC2 en ejecución con sus comprobaciones de estado](docs/capturas/43_aws_ec2_instancia.jpg)

![Reglas de entrada del Security Group de la instancia compartida, con el puerto 9000 del servidor MCP](docs/capturas/44_aws_security_group.jpg)

![Comprobación del servidor MCP desplegado: `curl` a `/health` responde {"estado":"ok"} con HTTP 200](docs/capturas/08_aws_servicio_mcp.png)

![`python infra/probar_mcp.py` con dos estudiantes: lista las 14 herramientas del servidor de AWS y las llama](docs/capturas/09_mcp_herramientas_remotas.png)

### Paso 6. Flujos de n8n

| Flujo | Qué hace | Agente, modelo, memoria y herramientas |
|---|---|---|
| 00 Chat principal | Webhook, guardrails de entrada, acciones directas, clasificación con Gemini, ruteo, guardrails de salida | Clasificador Gemini (JSON) |
| 01 Consulta general (RAG) | Embedding de la pregunta, `match_documentos`, umbral, respuesta con fuentes | Agente + Gemini + memoria |
| 02 Calendario | Lee Google Sheets y responde fechas | Agente + Gemini + memoria |
| 03 Agente académico | Matrícula, estado, proyección, requisitos y recomendaciones | Agente + Gemini + memoria + herramientas MCP |
| 04 Noticias | Scraper cada 6 horas y respuesta con las noticias de hoy | Agente + Gemini + memoria |
| 05 Ingesta de embeddings | Agrega o refresca documentos desde n8n (manual): fragmenta con 3200/480 caracteres, embeddings de 768 dimensiones e inserta en pgvector | Sin agente |

| Guardrail | Dónde | Qué hace |
|---|---|---|
| Token | Entrada | Sin `X-Chat-Token` válido responde 401 |
| Formato | Entrada | Código `U00` + 6 dígitos, `session_id` y mensaje de máximo 1000 caracteres |
| Inyección de prompt | Entrada | Patrones en español e inglés ("ignora las instrucciones", "muestra el prompt", `<system>`) |
| Credenciales | Entrada | No gestiona contraseñas, claves ni variables de entorno |
| Datos ajenos | Entrada y salida | Solo información del propio código; la respuesta no puede mencionar otro código |
| Fuera de tema | Clasificador (etiqueta `fuera_de_tema`) | Respuesta de alcance sin gastar el agente |
| Enlaces | Salida | Solo URLs de las fuentes recuperadas; el resto se omite |
| Fugas y longitud | Salida | Sin instrucciones internas ni claves; máximo 1800 caracteres |
| Resiliencia | Agentes y subflujos | Los agentes reintentan 3 veces; si un subflujo falla, el estudiante recibe un mensaje claro en vez de un error |

![Flujo 00](docs/capturas/50_n8n_flujo_00_chat_principal.png)

![Flujo 03: agente con modelo, memoria y herramientas MCP](docs/capturas/52_n8n_flujo_03_agente_mcp.png)

![Flujo 01: RAG](docs/capturas/51_n8n_flujo_01_rag.png)

Ejecución real del flujo 03 «Cursos realizados» con el nodo **Agente académico** abierto: a la izquierda, la entrada que arma el nodo *Armar
prompt* (mensaje, código, clave de memoria `codigo:session_id`, intención y el prompt del sistema) y a la derecha la respuesta personalizada:

![Ejecución real del flujo 03 con el nodo Agente académico abierto: entrada del nodo Armar prompt y respuesta personalizada](docs/capturas/18_n8n_ejecucion_exitosa.png)

En el panel de n8n:

![Overview de n8n con las estadísticas de ejecución y la lista de flujos (el 05 se ejecuta a mano)](docs/capturas/45_n8n_flujos.jpg)

![Ejecuciones del flujo 00 con la ruta seguida en verde](docs/capturas/46_n8n_ejecuciones_00.jpg)

![Flujo 03 en el editor](docs/capturas/47_n8n_flujo_03_agente.jpg)

![Ejecución exitosa del flujo 00 Chat principal en la vista de ejecuciones, con la ruta seguida en verde](docs/capturas/48_n8n_ejecuciones_03.jpg)

![Credenciales de n8n: Google Sheets, Postgres, Header Auth y Google Gemini, sin advertencias](docs/capturas/49_n8n_herramienta_mcp.jpg)

![Ejecución exitosa del flujo 02 Calendario académico](docs/capturas/54_n8n_ejecucion_calendario.jpg)

![Flujo 04: ejecuciones programadas cada 6 horas y el lienzo del flujo](docs/capturas/55_n8n_noticias_programadas.jpg)

![Flujo 05 Ingesta de embeddings: lienzo (no se ejecuta solo, se lanza a mano)](docs/capturas/56_n8n_flujo_ingesta.jpg)

**Ejecuciones fallidas en el panel.** El Overview de n8n (captura de los flujos) muestra 16 ejecuciones de producción fallidas de 168 (9.5 %). Se atribuyen al límite por
minuto del plan gratuito de Gemini (HTTP 429), que se supera cuando se hacen muchas preguntas seguidas durante las pruebas; no se
inspeccionó cada una. Está mitigado con `retryOnFail` (3 intentos en los agentes y los embeddings) y con `continueRegularOutput` en los
subflujos, de modo que el estudiante recibe un mensaje claro y no un error. Un exceso sostenido de llamadas sigue agotando los reintentos
(detalle en [`docs/parametros.md`](docs/parametros.md) y [`docs/pruebas.md`](docs/pruebas.md)).

Los JSON de `n8n/workflows/` son la fuente de verdad. Los cambios se llevan a n8n a mano: **Workflows > Import from File** (primero 01 a 05
y al final 00), volver a elegir los subflujos en los nodos *Execute Workflow* del 00, asignar las credenciales y publicar.

### Paso 7. Scraper de noticias del día

El flujo 04 corre solo cada 6 horas: descarga 7 fuentes (UNAB por la API de WordPress, El Tiempo Educación y Tecnósfera por RSS, y Google
Noticias para ingeniería de sistemas y desarrollo de software), normaliza título, URL, fecha, categoría, resumen y fuente, y hace upsert
en la tabla `noticias`. El agente y la pantalla de la app muestran primero las de hoy (hora de Colombia). `scraper/scraper_noticias.py`
hace lo mismo desde la terminal.

![Flujo 04: scraper y agente de noticias](docs/capturas/53_n8n_flujo_04_noticias.png)

![Noticias del día con categoría, fuente y fecha](docs/capturas/10_scraper_noticias_hoy.png)

### Paso 8. Webhook probado (curl, Postman y la app)

```bash
curl -s -X POST "$N8N_WEBHOOK_URL" -H "Content-Type: application/json" -H "X-Chat-Token: $CHAT_TOKEN" \
  -d '{"estudiante_codigo":"U00179961","session_id":"demo","mensaje":"¿En qué materias estoy matriculada?"}'
```

![`curl` POST al webhook de producción con la pregunta de matrícula](docs/capturas/12_webhook_curl_matricula.png)

![Estado académico y proyección](docs/capturas/13_webhook_estado_proyeccion.png)

![Recomendaciones](docs/capturas/14_webhook_recomendaciones.png)

![Consulta general con RAG y noticias del día](docs/capturas/15_webhook_rag_y_noticias.png)

![Guardrails: inyección de prompt, datos de otro estudiante y fuera de tema, y token incorrecto con 401](docs/capturas/16_guardrails.png)

La colección [`docs/postman/Asistente_UNAB.postman_collection.json`](docs/postman/Asistente_UNAB.postman_collection.json) trae las 12
peticiones con sus pruebas automáticas; solo hay que poner la URL del webhook y el token en las variables de la colección.

### Paso 9. App Android

App nativa en Kotlin con Jetpack Compose (paquete `co.edu.unab.cbdatos`), sin claves en el código. El botón del encabezado del chat es un lápiz
"Nueva conversación" (con confirmación y aviso) y la conversación visible se conserva al reiniciar (últimos 40 mensajes). Detalles en
[`android/README.md`](android/README.md) y uso en el [manual de usuario](docs/manual_usuario.md).

![Informe HTML real de Gradle: 48 pruebas, 0 fallos](docs/capturas/17_android_compilar_y_probar.png)

![Consola con la ejecución de las pruebas de la app con Gradle](docs/capturas/17b_android_consola_gradle.png)

<table>
<tr>
<td><img src="docs/capturas/20_app_ingreso.jpg" width="200" alt="Ingreso"><br>Ingreso</td>
<td><img src="docs/capturas/22_app_matricula.jpg" width="200" alt="Matrícula"><br>Matrícula</td>
<td><img src="docs/capturas/23_app_estado_academico.jpg" width="200" alt="Estado académico"><br>Estado académico</td>
<td><img src="docs/capturas/24_app_proyeccion.jpg" width="200" alt="Proyección"><br>Proyección</td>
</tr>
<tr>
<td><img src="docs/capturas/25_app_recomendaciones.jpg" width="200" alt="Recomendaciones"><br>Recomendaciones</td>
<td><img src="docs/capturas/26_app_competencias_digitales.jpg" width="200" alt="Competencias digitales"><br>Competencias digitales</td>
<td><img src="docs/capturas/27_app_horas_libres.jpg" width="200" alt="Horas libres"><br>Horas libres</td>
<td><img src="docs/capturas/28_app_consulta_general_rag.jpg" width="200" alt="Consulta con RAG"><br>Reglamento (RAG)</td>
</tr>
<tr>
<td><img src="docs/capturas/29_app_noticias_chat.jpg" width="200" alt="Noticias en el chat"><br>Noticias en el chat</td>
<td><img src="docs/capturas/30b_app_noticias_filtro.jpg" width="200" alt="Noticias por categoría"><br>Noticias por categoría</td>
<td><img src="docs/capturas/31b_app_perfil_requisitos.jpg" width="200" alt="Requisitos de grado"><br>Requisitos de grado</td>
<td><img src="docs/capturas/31c_app_perfil_horario.jpg" width="200" alt="Horario"><br>Horario</td>
</tr>
<tr>
<td><img src="docs/capturas/32_app_calendario.jpg" width="200" alt="Calendario"><br>Calendario</td>
<td><img src="docs/capturas/33_app_nueva_conversacion.jpg" width="200" alt="Nueva conversación"><br>Nueva conversación (lápiz)</td>
</tr>
</table>

## Códigos de prueba

Cualquier código `U00` + 6 dígitos funciona: si no existe, el servidor crea un estudiante sintético (siempre el mismo para ese código).

| Código | Estudiante | Semestre | Avance (de 151 créditos) | Competencias digitales | Horas libres |
|---|---|---|---|---|---|
| `U00100001` | Manuela Daniela Rodríguez Uribe | 5 | 62 (41 %) | 5 de 5, cumplido | 10 |
| `U00100002` | Jesús Daza Durán (rezagado) | 7 | 60 (40 %) | 5 de 5, cumplido | 113, cumplido |
| `U00100003` | Juan Maldonado Jiménez (adelantado) | 7 | 112 (74 %) | le falta Cultura digital | 24 |
| `U00100004` | Milena María Gómez Silva (primer semestre) | 1 | 0 | le falta MS PowerPoint | 112, cumplido |
| `U00134229` | José Gaviria Bravo (rezagado) | 8 | 22 (15 %) | le faltan Vida en línea, MS PowerPoint y Cultura digital | 97, cumplido |
| `U00179961` | Angie Katherine Suarez Ortiz | 6 | 85 (56 %) | le faltan Vida en línea, MS Excel y Cultura digital | 11 |
| `U00179643` | Juan Sebastián Lizcano Jaimes | 7 | 91 (60 %) | 5 de 5, cumplido | 53 |

En los dos últimos solo el nombre es real; los datos académicos son sintéticos.

## Pertinencia pedagógica

El asistente aplica la **educación de precisión** (Hart, 2016; Yang, 2021): en vez de respuestas generales, cada respuesta se calcula con
los datos del propio estudiante (créditos, notas, prerrequisitos, requisitos de grado) y termina en una acción concreta: qué inscribir,
qué pilar presentar, cuántas horas faltan, qué riesgo atender. Eso apoya el **autoaprendizaje y la autorregulación** (Zimmerman, 2002):
el estudiante ve dónde está, a dónde va y qué hacer, y puede volver a preguntar cuando quiera. Las alertas tempranas siguen la línea
de la analítica del aprendizaje (Arnold y Pistilli, 2012). Detalle, ejemplos y referencias en
[`docs/pertinencia_pedagogica.md`](docs/pertinencia_pedagogica.md); los prompts completos en [`docs/prompts.md`](docs/prompts.md).

## Contrato del webhook

```
POST {N8N_WEBHOOK_URL}     Content-Type: application/json, X-Chat-Token: {CHAT_TOKEN}

{"estudiante_codigo": "U00179961", "session_id": "uuid", "mensaje": "¿Cómo voy en mi plan de estudios?"}
200 {"respuesta": "...", "intencion": "cursos", "fuentes": [{"titulo": "...", "url": "..."}]}

{"accion": "perfil", "estudiante_codigo": "U00179961", "session_id": "uuid"}
200 {"perfil": {"nombre", "programa", "semestre_actual", "horario": [...], "avance": {...}, "competencias_digitales": {...}, "horas_libres": {...}}}

{"accion": "noticias", "estudiante_codigo": "U00179961", "session_id": "uuid"}
200 {"noticias": {"fecha_consulta", "de_hoy", "categorias", "noticias": [{"titulo", "url", "fecha", "categoria", "fuente", "es_hoy"}]}}

401 sin token válido; 400 si el cuerpo no cumple el formato.
```

`intencion` puede ser `general`, `calendario`, `cursos`, `matricula`, `noticias` o `fuera_de_tema`. Detalle en [`docs/CONTRATO.md`](docs/CONTRATO.md).

## Estructura del repositorio

```
README.md
android/          app Android (Kotlin, Jetpack Compose)
data/             oficial/ (planes, documentos, profesores) y sintetica/ (CSV generados)
db/               migrations/ (001 a 006), seed/ (planes.py, estudiantes_base.csv, generar_datos.py, cargar.py, seed.sql), ver_tablas.py
docs/             arquitectura, documentación técnica, parámetros, pruebas, RAG, manual de usuario, pertinencia, prompts,
                  contrato, despliegue, capturas/, diagramas/ (HTML) y postman/
infra/            servicio systemd, Security Groups, guías de Supabase, n8n y Google Sheets, probar_mcp.py
mcp-server/       servidor FastMCP, pruebas y Dockerfile
n8n/              workflows/ (00 a 05, se importan a mano) y herramientas/ (probar el webhook)
rag/              ingesta, consulta, evaluación de fragmentos y evaluación del umbral del RAG
scraper/          scraper de noticias del día
```

## Pruebas

| Parte | Comando | Resultado |
|---|---|---|
| Servidor MCP | `cd mcp-server && TEST_DATABASE_URL=$DATABASE_URL python -m pytest` | 43 pasan: 37 unitarias y 6 de integración contra Supabase (sin la variable, 37 pasan y 6 se omiten) |
| RAG | `python -m pytest -q rag/tests`, `python rag/evaluar_chunks.py` y `python rag/evaluar_umbral.py` | 3 pruebas; 25 preguntas con acierto@1 = 1.00; 30 preguntas del umbral |
| App Android | `cd android && ./gradlew testDebugUnitTest` | 48 pruebas |
| Webhook | `python n8n/herramientas/probar_webhook.py "U00179961\|¿Qué cursos debo tomar?"` | Respuesta del webhook de producción |
| Postman | Colección `docs/postman/` | 12 peticiones con pruebas |

La verificación de extremo a extremo del 2026-11-20 (conteos de la base, 14 herramientas MCP, 401 sin clave, consultas del RAG, preguntas al
webhook con su latencia y el token inválido) está en [`docs/pruebas.md`](docs/pruebas.md): 23 de 25 verificaciones pasaron y los 2 fallos
(recomendaciones de rendimiento y pregunta de memoria) se corrigieron en el clasificador y pasaron en la reprueba de 8 preguntas (8 de 8).

## Seguridad

- Ninguna clave en el repositorio: todo va en `.env` (fuera de git) y en las credenciales de n8n. Los scripts leen el `.env` y no
  imprimen las claves. La llave `.pem` de la instancia también está fuera de git.
- Webhook con `X-Chat-Token`, servidor MCP con `X-API-Key` y guardrails de entrada y salida.
- El Security Group de la instancia compartida del laboratorio tiene varios puertos abiertos a internet (el 9000 es de este proyecto); el riesgo y
  el endurecimiento recomendado están en [`infra/SECURITY_GROUPS.md`](infra/SECURITY_GROUPS.md).
- Un APK compilado con `android/local.properties` lleva dentro la URL del webhook y el token: compile el suyo y no publique APK con valores reales.
- Row Level Security en las 18 tablas y vistas con `security_invoker`: la API REST pública de Supabase no expone datos.
- Las capturas ocultan la cuenta de AWS, el correo, la IP pública, los identificadores del Security Group y de la VPC, el host de n8n y la URL del proyecto de Supabase.

## Documentación

- [`docs/manual_usuario.md`](docs/manual_usuario.md): manual de usuario de la app.
- [`docs/arquitectura.md`](docs/arquitectura.md): componentes, secuencia, ruteo y decisiones de diseño.
- [`docs/documentacion_tecnica.md`](docs/documentacion_tecnica.md): modelo de datos, flujos, guardrails, memoria, MCP y scraper.
- [`docs/rag.md`](docs/rag.md): pipeline RAG, parámetros, experimento de tamaño de fragmento y evidencia del umbral.
- [`docs/parametros.md`](docs/parametros.md): cada valor numérico, dónde está y por qué.
- [`docs/pruebas.md`](docs/pruebas.md): verificación de extremo a extremo del 2026-11-20.
- [`docs/pertinencia_pedagogica.md`](docs/pertinencia_pedagogica.md) y [`docs/prompts.md`](docs/prompts.md).
- [`docs/CONTRATO.md`](docs/CONTRATO.md) y [`docs/despliegue.md`](docs/despliegue.md).
- [`android/README.md`](android/README.md), [`mcp-server/README.md`](mcp-server/README.md) e [`infra/`](infra/) (incluye [`SECURITY_GROUPS.md`](infra/SECURITY_GROUPS.md)).
