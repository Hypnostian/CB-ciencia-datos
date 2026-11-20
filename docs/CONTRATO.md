# Contrato técnico compartido (CB-ciencia-datos)

Proyecto aparte para Ciencia de Datos (Ingeniería de Sistemas, UNAB), trabajo final: **asistente académico con n8n**. Es independiente de la app oficial UNAB GO!: no usa su servidor, sus claves, su
proyecto de Firebase ni su paquete. Todos los componentes deben respetar este contrato para encajar.

## Reglas
- Español en documentación, mensajes y nombres de tablas.
- **Datos sintéticos solo aquí** (estudiantes, matrículas, notas, NRC, historial CCD): nunca en la app oficial.
  - Código de estudiante: `U00` + 6 dígitos (ej. `U00123456`).
  - NRC: 5 dígitos aleatorios, únicos (ej. `48213`).
  - Correos sintéticos: `<codigo>@demo.unab.local` (dominio inexistente, para no parecer reales).
- **Datos oficiales** (planes de estudio, profesores de APOLO, CCD, reglamento, noticias): solo lo publicado en
  sitios oficiales, con su URL de fuente. Lo que se simula (por ejemplo prerrequisitos) va marcado
  `es_simulado = true`.
- Ninguna clave en el código: todo por variables de entorno (`.env.example`).

## Estructura
```
CB-ciencia-datos/
  README.md
  docs/            CONTRATO.md, arquitectura.md, documentacion_tecnica.md, rag.md, manual_usuario.md, pertinencia_pedagogica.md,
                   prompts.md, despliegue.md, parametros.md, pruebas.md, capturas/, diagramas/, postman/
  data/oficial/    unab_profesores.json, unab_planes_estudio.json, docs/*.txt (copiados de la recolección oficial)
  data/sintetica/  CSV generados por db/seed
  data/calendario_academico.csv   (se sube a Google Sheets)
  db/              migraciones SQL 001 a 006 (Supabase/PostgreSQL + pgvector), seed sintético en Python, ver_tablas.py
  rag/             ingesta (fragmentación + embeddings Gemini + pgvector), consulta y evaluación
  mcp-server/      servidor FastMCP (Python), Dockerfile, pruebas
  n8n/workflows/   workflows en JSON (fuente de verdad); n8n/herramientas/ prueba el webhook (los flujos se importan a mano desde n8n)
  scraper/         scraper de noticias del día (misma lógica del flujo 04)
  infra/           servicio systemd, docker-compose opcional, Security Groups (puerto 9000), guías y probar_mcp.py
  android/         app Android propia del chatbot (paquete co.edu.unab.cbdatos)
```

## Variables de entorno
| Variable | Uso |
|---|---|
| `GEMINI_API_KEY` | Clave gratuita de Google AI Studio (respuestas y embeddings) |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` |
| `GEMINI_EMBED_MODEL` | `gemini-embedding-001` con `outputDimensionality = 768` |
| `EMBED_DIM` | `768` |
| `DATABASE_URL` | Cadena de conexión PostgreSQL de Supabase (pooler, sslmode=require) |
| `MCP_API_KEY` | Clave compartida que el servidor MCP exige en el encabezado `X-API-Key` |
| `MCP_PORT` | `9000` (transporte HTTP streamable, ruta `/mcp`) |
| `N8N_WEBHOOK_URL` | URL del webhook de producción del workflow principal en n8n Cloud |
| `CHAT_TOKEN` | Secreto compartido que la app envía en `X-Chat-Token` |
| `GOOGLE_SHEET_ID` | Hoja de cálculo con el calendario académico |
| `MCP_URL` | Dirección del servidor MCP (`http://IP:9000`), la usan n8n y los scripts |
| `N8N_URL`, `N8N_API_KEY` | Instancia de n8n y token de su MCP (opcionales; los flujos se importan a mano con **Import from File**) |

## Base de datos (esquema `public`, simula Banner-Cosmos)
- `programas(id serial, codigo text unique, nombre text, total_creditos int, fuente_url text)`
- `cursos(id serial, programa_id int, codigo text unique, nombre text, creditos int, semestre_plan int, tipo text check (obligatorio|electivo), es_oficial bool)`
  (51 cursos del plan oficial de Ingeniería de Sistemas: 151 créditos, 9 semestres contando el de la práctica)
- `prerrequisitos(curso_id int, requisito_id int, es_simulado bool default true, primary key(curso_id, requisito_id))`
- `periodos(id text primary key /* '2026-2' */, nombre text, fecha_inicio date, fecha_fin date, actual bool)`
- `profesores(id serial, nombre text, unidad text, cargo text, apolo_url text unique, cvlac_url text)` (datos públicos de APOLO)
- `secciones(nrc char(5) primary key, curso_id int, periodo_id text, docente text /* nombre sintético */, horario text, cupo int)`
  (las secciones son simuladas: no se asignan profesores reales de APOLO a cursos inventados)
- `estudiantes(codigo text primary key check (codigo ~ '^U00[0-9]{6}$'), nombres text, apellidos text, correo text, programa_id int, semestre_actual int, estado text, fecha_ingreso date)`
- `matriculas(id serial, estudiante_codigo text, nrc char(5), periodo_id text, estado text check (inscrita|cancelada|finalizada), nota_final numeric(2,1) null)`
- `cursos_ccd(id serial, ruta int check (1..3), nombre text, obligatorio bool, descripcion text, fuente_url text)` (nombres oficiales)
- `historial_ccd(id serial, estudiante_codigo text, curso_ccd_id int, periodo_id text, estado text check (aprobado|en_curso|reprobado), fecha date)`
- `competencias_digitales(id serial, orden int, nombre text, materia text, requisito text default 'Competencias Digitales R2025', fuente_url text)`
  (los 5 pilares del portal: Vida en línea, MS Word, MS Excel, MS PowerPoint, Cultura digital) y
  `resultados_competencias(estudiante_codigo text, competencia_id int, aprobada bool, fecha_prueba date)` (resultado sintético de la prueba, una vez por pilar)
- `horas_libres(estudiante_codigo text primary key, horas_cumplidas int, horas_requeridas int default 96, actualizado date)` (sintéticas, de 0 a 120)
- `calendario_academico(id serial, evento text, categoria text, fecha_inicio date, fecha_fin date, verificado bool, fuente_url text)` (espejo de la hoja de Google)
- `noticias(id serial, titulo text, url text unique, fecha timestamptz, categoria text, resumen text, fuente text, creado_en timestamptz default now())`
- `documentos(id serial, titulo text, fuente_url text unique, tipo text)` y
  `documentos_fragmentos(id bigserial, documento_id int, contenido text, metadata jsonb, embedding vector(768))`
- `n8n_chat_histories(id serial, session_id varchar(255), message jsonb)` (memoria persistente del nodo Postgres Chat Memory de n8n)
- Vistas analíticas: `v_cursos_estudiante`, `v_estado_matricula`, `v_avance_plan`, `v_proyeccion_semestres`, `v_requisitos_pendientes`,
  `v_historial_ccd`, `v_competencias_estudiante`; todas con `security_invoker = true` (migraciones 005 y 006)
- Función RPC: `match_documentos(query_embedding vector(768), match_count int default 5)` → `(id, documento_id, titulo, fuente_url, contenido, similitud)`

## Servidor MCP (FastMCP, `mcp-server/`)
Transporte HTTP streamable en `0.0.0.0:9000/mcp`, encabezado `X-API-Key`. Endpoints REST para la app (vía n8n): `POST /api/perfil`
`{estudiante_codigo}` y `POST /api/noticias` `{limite?, categoria?}`. Herramientas (devuelven JSON):
| Herramienta | Argumentos | Qué devuelve |
|---|---|---|
| `perfil_estudiante` | `estudiante_codigo` | Ficha: nombre, programa, semestre, horario, avance, competencias digitales y horas libres |
| `estado_matricula` | `estudiante_codigo` | Periodo actual, cursos inscritos (NRC, curso, créditos, profesor, horario), créditos inscritos |
| `avance_plan` | `estudiante_codigo` | Créditos aprobados/totales, % de avance, cursos aprobados y pendientes por semestre |
| `proyeccion_semestres` | `estudiante_codigo`, `creditos_por_semestre=18` | Semestres restantes estimados y propuesta de cursos por semestre respetando prerrequisitos |
| `requisitos_pendientes` | `estudiante_codigo` | Alertas: cursos bloqueados por prerrequisito, CCD obligatorio sin aprobar, competencias digitales y horas libres pendientes, rezago |
| `cursos_ccd` | `estudiante_codigo` | Cursos del Centro de Competencias Digitales tomados, rutas cumplidas y faltantes para la insignia |
| `competencias_digitales` | `estudiante_codigo` | Requisito Competencias Digitales R2025: resultado de la prueba por pilar, `aprobadas`, `faltantes`, `cumplido` |
| `horas_libres` | `estudiante_codigo` | `horas_cumplidas`, `horas_requeridas` (96), `horas_faltantes`, `completo` (true desde 96 horas) |
| `recomendaciones` | `estudiante_codigo` | Recomendaciones personalizadas (carga, cursos sugeridos, alertas) |
| `calendario` | `desde?`, `categoria?` | Eventos del calendario académico |
| `noticias` | `limite=5`, `categoria?` | Noticias del día primero (`es_hoy`), con categoría, fuente y fecha |
| `buscar_documentos` | `pregunta`, `k=5` | Fragmentos RAG con título y URL de fuente |
| `buscar_profesor` | `texto` | Profesores de APOLO por nombre o unidad, con su perfil |
| `info_curso` | `texto` | Curso del plan: créditos, semestre, prerrequisitos (marcando los simulados) |

## n8n (workflows en `n8n/workflows/`)
- `00_chat_principal.json`: Webhook `POST /webhook/unab-chat` → validación de `X-Chat-Token` → **guardrails de
  entrada** → **ruteo por intención** (Gemini clasifica en `general | calendario | cursos | matricula | noticias | fuera_de_tema`) →
  subflujo → **guardrails de salida** → respuesta. Memoria persistente con Postgres Chat Memory (`session_id`).
- `01_consulta_general_rag.json`: pregunta → embedding Gemini → `match_documentos` → LLM con contexto → respuesta con fuentes.
- `02_calendario.json`: intención → Google Sheets (`GOOGLE_SHEET_ID`) → respuesta.
- `03_cursos_realizados.json`: agente con 11 herramientas del servidor MCP → respuesta personalizada (matrícula, avance, proyección,
  requisitos, recomendaciones, competencias digitales, horas libres, historial CCD).
- `04_noticias_scraper.json`: programado (cada 6 h) → 7 fuentes (API WordPress de unab.edu.co, RSS de El Tiempo Educación y Tecnósfera,
  Google Noticias) → upsert en `noticias`; y responder con las noticias de hoy primero.
- `05_ingesta_embeddings.json`: documentos → fragmentación → embeddings → `documentos_fragmentos`.

Contrato del webhook (lo usa la app Android):
```
POST {N8N_WEBHOOK_URL}
Headers: Content-Type: application/json, X-Chat-Token: {CHAT_TOKEN}
Body:    {"estudiante_codigo": "U00123456", "session_id": "uuid", "mensaje": "¿Qué cursos debo tomar?"}
200:     {"respuesta": "...", "intencion": "cursos", "fuentes": [{"titulo": "...", "url": "..."}]}

Body:    {"accion": "noticias", "estudiante_codigo": "U00123456", "session_id": "uuid"}
200:     {"noticias": {"fecha_consulta", "total", "de_hoy", "categorias", "noticias": [{"titulo", "url", "fecha", "categoria",
                       "resumen", "fuente", "es_hoy"}]}}
```

## Fuentes oficiales confirmadas
- Plan de estudios de Ingeniería de Sistemas: documento "Plan de estudios" de `https://unab.edu.co/programas/ingenieria-de-sistemas/`
  (151 créditos). Los planes de los 133 programas salen de las páginas de unab.edu.co (`data/oficial/unab_planes_estudio.json`).
- Profesores: `https://apolo.unab.edu.co/sitemap/persons.xml` y los perfiles `/es/persons/{slug}/` (JSON-LD Person). Respetar `Crawl-Delay: 5`. No extraer correos ocultos ni teléfonos: se enlaza el perfil.
- Centro de Competencias Digitales: Ruta 1 Interacción Digital (obligatoria); Ruta 2 Habilidades en Analítica Digital, Marca Personal Digital, Creación de Contenidos Digitales; Ruta 3 IA Generativa, Marco Legal Digital, Cuidado y Bienestar Digital (un curso por ruta). Contacto ccdigital@unab.edu.co.
- Noticias: `https://unab.edu.co/wp-json/wp/v2/posts` (categorías 430, 20, 556 y 232), `https://www.eltiempo.com/rss/vida_educacion.xml`,
  `https://www.eltiempo.com/rss/tecnosfera.xml` y el RSS de búsqueda de Google Noticias (ingeniería de sistemas, desarrollo de software).
- Matrícula: `https://unab.edu.co/matricula-pregrado-profesional/`. Reglamento Estudiantil de Pregrado 2019.

## Acción "perfil" del webhook y alta automática de estudiantes (13-nov-2026)
- **Webhook:** mismo `POST {N8N_WEBHOOK_URL}` y `X-Chat-Token`, cuerpo `{"accion":"perfil","estudiante_codigo":"U00179643","session_id":"..."}`
  (sin `mensaje`). Respuesta `200 {"perfil": {codigo, nombre, nombres, apellidos, correo, programa, semestre_actual, estado,
  periodo_actual, horario: [{nrc, curso_codigo, curso, creditos, profesor, horario}], creditos_inscritos, avance: {...}, nuevo}}`;
  `400 {"error"}` si el código no tiene el formato. El flujo 00 la atiende antes de clasificar la intención y llama a `POST {MCP_URL}/api/perfil`
  (protegido con `X-API-Key`).
- **Servidor MCP:** nueva herramienta `perfil_estudiante`. Si llega un código válido que no está en la base, `app/registro.py` crea un
  estudiante sintético con las reglas del generador (perfil, carga, prerrequisitos, notas, historial CCD, sin cruces de horario). El mismo
  código produce siempre el mismo estudiante. Los nombres fijos van en `mcp-server/app/estudiantes_fijos.json` (por ejemplo `U00179643`,
  el autor del proyecto: solo el nombre es real) y `db/seed/cargar.py` los crea al recargar el seed.

## Competencias digitales y horas libres (17-nov-2026)
- **Perfil:** la acción `perfil` agrega `competencias_digitales: {requisito, fecha_prueba, competencias: [{competencia, estado, cumplida_con}],
  faltantes, total_aprobadas, total_pilares, cumplido}` y `horas_libres: {horas_cumplidas, horas_requeridas, horas_faltantes, completo}`.
  La app los muestra en "Mi perfil y horario" y en el inicio del chat.
- **Regla oficial usada:** la prueba de cada pilar se presenta una sola vez; si no se alcanza el umbral, el estudiante debe inscribir el curso
  correspondiente (unab.edu.co, inscripción a las pruebas de Competencias Digitales). Los resultados por estudiante son sintéticos.
- **Horas libres:** se requieren 96 para el grado; cada estudiante tiene un número al azar entre 0 y 120. Con 96 o más, el requisito queda cumplido.
- Los dos datos salen de `registro.requisitos(codigo, fecha_ingreso)`, con semilla en el código: el seed, el alta automática y la
  carga de requisitos (`cargar.py --requisitos`) producen siempre los mismos valores para el mismo estudiante.

## Plan oficial, noticias del día y seguridad de vistas (18-nov-2026)
- **Plan de estudios:** la base usa el documento oficial de la página del programa (151 créditos, 51 cursos, 9 semestres contando la
  práctica). Las electivas repetidas se numeran (I a IV) y los 43 prerrequisitos siguen siendo simulados. Los 120 estudiantes conservan
  su código y nombre (`db/seed/estudiantes_base.csv`); su historia académica se recalculó sobre el plan oficial.
- **Noticias:** acción `noticias` del webhook y endpoint `POST /api/noticias` del servidor MCP; categorías `Educación`, `Tecnología`,
  `Ingeniería de Sistemas` y `Vida UNAB`.
- **Migración 006:** `security_invoker = true` en las vistas de 003.
- **Flujos:** los agentes reintentan 3 veces y los subflujos continúan si fallan (el guardrail de salida responde con un mensaje claro).

