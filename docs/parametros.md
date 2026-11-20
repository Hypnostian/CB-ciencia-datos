# Parámetros y por qué

Cada valor numérico del sistema, dónde está y por qué se eligió. La columna **Base** dice qué tipo de sustento tiene: *reglamento* (texto
oficial en `data/oficial/docs/`), *plan* (el plan oficial de 151 créditos), *medido* (una prueba del repositorio) o *decisión de diseño*
(una elección de ingeniería sin fuente externa; en ese caso se dice así y se da la razón). No hay citas inventadas: lo que no se pudo
sustentar con una fuente o una medición está marcado y recopilado al final.

Documentos relacionados: [`rag.md`](rag.md) (experimentos del RAG), [`pruebas.md`](pruebas.md) (mediciones del 2026-11-20) y
[`arquitectura.md`](arquitectura.md).

## 1. Modelo de lenguaje y agentes

| Valor | Dónde | Por qué | Base |
|---|---|---|---|
| Modelo `gemini-3.5-flash-lite` | Los 4 agentes y el clasificador (flujos 00 a 04) | Responde en cerca de 1 s según lo observado al desplegar ([`despliegue.md`](despliegue.md), sección 10), y `gemini-2.5-flash` ya no está disponible para claves nuevas. Un modelo "lite" basta porque la respuesta se arma con datos que entregan el flujo o las herramientas, no con conocimiento propio del modelo | Medido (observación) y disponibilidad de la API |
| Temperatura **0.2** en los agentes | `options.temperature` de los 4 agentes | Las respuestas deben repetir cifras exactas de las herramientas o del contexto; una temperatura baja reduce la variación entre ejecuciones. Se dejó en 0.2 y no en 0 para que la redacción no suene idéntica en cada respuesta. No se comparó con otros valores | Decisión de diseño |
| Temperatura **0** en el clasificador | Flujo 00, nodo *Clasificar intencion* | La salida es una sola etiqueta de un `enum` de 6; se quiere que el mismo mensaje dé siempre la misma etiqueta | Decisión de diseño |
| `thinkingLevel: minimal` y sin `maxOutputTokens` en el clasificador | Flujo 00, nodo *Clasificar intencion* | El modelo nuevo rechazó `thinkingBudget: 0` ([`despliegue.md`](despliegue.md), sección 10); la salida es una etiqueta corta, así que el esquema JSON ya limita su tamaño | Compatibilidad de la API |
| `maxOutputTokens` **1024** | Modelo de los 4 agentes | El prompt pide como máximo 180 palabras, que en español son unos 1100 caracteres y en el orden de 300 tokens; 1024 deja un margen de unas tres veces para que una respuesta nunca se corte a la mitad | Decisión de diseño (el margen es una estimación, no una medición de tokens) |
| Ventana de memoria de **8** mensajes | *Postgres Chat Memory*, clave `codigo:session_id` | Son unos 4 intercambios (pregunta y respuesta), suficientes para preguntas de seguimiento ("¿y el siguiente semestre?") sin inflar el prompt ni el costo de cada llamada. No se probó con otros valores | Decisión de diseño |
| `maxIterations` **6** | Los 4 agentes | Solo importa en el flujo 03, el único con herramientas (11); una consulta típica usa 1 a 3 llamadas (en la reprueba de [`pruebas.md`](pruebas.md), la pregunta de recomendaciones llamó `recomendaciones`, `avance_plan` y `requisitos_pendientes`). 6 deja margen y corta un ciclo de herramientas que no converge. En los flujos 01, 02 y 04 el agente no tiene herramientas y responde en una iteración | Decisión de diseño |
| Respuesta de máximo **1800** caracteres | Flujo 00, *Guardrails de salida* | Red de seguridad sobre el límite de 180 palabras del prompt (unos 1100 caracteres): en una pantalla de teléfono una respuesta mucho más larga no se lee. Casi nunca actúa; existe para el caso de que el modelo ignore el prompt | Decisión de diseño |
| Mensaje de entrada de máximo **1000** caracteres y `session_id` de máximo **100** | Flujo 00, *Guardrails de entrada* | Evita que un solo mensaje consuma el contexto del modelo o se use para inyectar texto largo; un `session_id` normal de la app es un UUID de 36 caracteres | Decisión de diseño |

## 2. RAG

| Valor | Dónde | Por qué | Base |
|---|---|---|---|
| Fragmentos de **800 tokens** con solape de **120** (15 %) | `rag/ingesta.py`; flujo 05 con 3200 y 480 caracteres | Con 800 solo 3 secciones se parten; con 300 serían 21. El solape es un seguro barato para las 3 que se parten. El experimento no discrimina (las 4 configuraciones empatan en 1.00), así que se eligió por estructura. Detalle y limitaciones en [`rag.md`](rag.md) | Medido (estructura de fragmentos) y decisión de diseño |
| Modelo de embeddings `gemini-embedding-001` | `ingesta.py`, flujos 01 y 05, herramienta `buscar_documentos` | Multilingüe, con tipo de tarea distinto para documento y pregunta, en la misma API del LLM y disponible sin costo en el plan gratuito. No se comparó con otros modelos | Decisión de diseño |
| **768** dimensiones | `outputDimensionality` en todos los llamados; columna `vector(768)` | El modelo produce 3072 por defecto y su entrenamiento permite truncar el vector (truncamiento tipo Matryoshka): con 768 el índice ocupa la cuarta parte del espacio (768 de 3072). La similitud coseno no depende de la longitud del vector, así que el operador `<=>` de pgvector funciona igual con o sin normalizar; las rutas de Python normalizan por costumbre y no es necesario. En las 25 preguntas de producción el acierto@1 es 1.00. **No se comparó contra 3072**, así que "sin pérdida de calidad" vale solo para esas pruebas | Medido (25 preguntas) y cálculo de almacenamiento |
| Los embeddings **no tienen temperatura** | (ningún nodo de embedding) | El modelo de embeddings es determinista: el mismo texto da el mismo vector. Sus parámetros son el modelo, las dimensiones y el tipo de tarea (`RETRIEVAL_DOCUMENT` al indexar y `RETRIEVAL_QUERY` al preguntar) | Documentación del modelo |
| **top-k = 5** | `match_documentos(vector, 5)`, flujo 01 y `rag/consultar.py` | El peor caso de contexto con fragmentos de 800 tokens es 3561 tokens, muy por debajo del límite del modelo, y deja espacio para el prompt y la memoria | Medido (contexto top 5 en [`rag.md`](rag.md)) |
| Umbral de similitud **0.35** | Flujo 01, nodo *Armar prompt*, y `rag/consultar.py` | Es un filtro de ruido, no una barrera de tema: en [`rag.md`](rag.md), sección 5, las 15 preguntas ajenas al dominio (similitud máxima 0.611) y las 15 del dominio (mínimo 0.705) superaron 0.35. Se recomienda 0.65 (no aplicado) | Medido |
| Índice HNSW sin parámetros propios | `002_esquema.sql` | Se usan los valores por defecto de pgvector (`m` y `ef_construction`); no se ajustaron ni se midió su efecto con 434 fragmentos | Decisión de diseño |
| Pausa de **700 ms** entre embeddings | `batchInterval` en los flujos 01 y 05, `sleep(0.7)` en `ingesta.py` | 0.7 s equivale a unas 85 solicitudes por minuto, por debajo del límite por minuto del plan gratuito de Gemini | Decisión de diseño según el límite del plan |

## 3. Resiliencia y tiempos

| Valor | Dónde | Por qué | Base |
|---|---|---|---|
| `retryOnFail`: **3** intentos con **5 s** (agentes), **3** con **2 s** (embeddings), **2** (clasificador, descargas del scraper) | Nodos de los flujos 00 a 05 | El plan gratuito de Gemini limita las llamadas por minuto (error 429). Los reintentos cortos absorben ráfagas; **no** absorben un exceso sostenido, porque 3 intentos con 5 s suman unos 10 s y la ventana del límite es de un minuto. Por eso en las pruebas aparecieron ejecuciones fallidas por 429 (ver el README, sección de n8n), mitigadas con `continueRegularOutput` para que el estudiante reciba un mensaje y no un error | Decisión de diseño según el límite del plan |
| Tiempo de espera de **30 s** en n8n y de **15 s / 60 s / 30 s** (conexión, lectura, escritura) en la app | Nodos HTTP y `ChatRepository.kt` | La lectura de la app (60 s) cubre el peor caso de un agente con herramientas: las respuestas del 2026-11-20 tardaron entre 1.9 y 6.7 s ([`pruebas.md`](pruebas.md)), y la ejecución del flujo 03 de la captura 18 tardó 18.2 s | Medido |
| Scraper cada **6 horas** | Flujo 04, `scheduleTrigger` | Son 4 corridas al día: las fuentes (blog de la UNAB y RSS de prensa) publican unas pocas noticias por día, y consultar menos seguido es cortés con los sitios. La verificación del 2026-11-20 mostró que la noticia más reciente tenía unas 2 horas de antigüedad, coherente con el ciclo | Decisión de diseño; consistencia verificada |
| Máximo 10 noticias por fuente, resumen de 500 caracteres, 7 fuentes | Flujo 04 y `scraper_noticias.py` | Limita el tamaño de la tabla y del prompt del agente de noticias | Decisión de diseño |

## 4. Constantes académicas

Fuentes: el [Reglamento estudiantil de pregrado](../data/oficial/docs/reglamento_estudiantil_pregrado.txt) y el plan oficial de Ingeniería
de Sistemas (151 créditos, 9 semestres contando la práctica; carga por semestre del plan: 16, 18, 17, 18, 17, 17, 17, 16 y 15 créditos,
según `python db/ver_tablas.py`).

| Valor | Dónde | Por qué | Base |
|---|---|---|---|
| Nota de aprobación **3.0** | `NOTA_APROBACION` en `logica.py`, vistas `v_cursos_estudiante` | El Reglamento, artículo 37: la calificación aprobatoria mínima es 3.0 en la escala de 0.0 a 5.0 | Reglamento |
| Total del programa **151** créditos | Tabla `programas`, `avance_plan` | Es el plan oficial publicado en la página del programa | Plan |
| Crédito = 48 horas de trabajo | (contexto de la carga) | Reglamento, artículo 32. Con 18 créditos por periodo son 864 horas; si el periodo dura 16 semanas (supuesto, el reglamento no lo fija) serían unas 54 horas semanales | Reglamento |
| **18** créditos por semestre (por defecto) | `CREDITOS_POR_SEMESTRE_DEFECTO`, `proyeccion_semestres` (rango permitido de 6 a 24) | El semestre más cargado del plan oficial tiene 18 créditos y el promedio es 151 / 9 = 16.8; 18 es el máximo de carga que el propio plan propone en un semestre. En el texto del reglamento no se encontró un mínimo ni un máximo de créditos por periodo, así que no hay tope oficial que citar. El rango de 6 a 24 es solo un límite de validación | Plan y decisión de diseño |
| Cargas sugeridas **14 / 16 / 18 / 20** | `logica.py`, función de recomendaciones | Escala heurística alrededor del 18 del plan: 14 si el rezago es de 12 créditos o más o hay 3 o más cursos reprobados; 16 si el rezago es de 6 créditos o más o hay reprobados; 20 si el estudiante va adelantado; 18 en otro caso. El 20 supera el máximo del plan por 2 créditos y es solo para quien va adelantado. **No hay fuente externa**: el reglamento no habla de carga recomendada. La razón de ingeniería es aliviar la carga de quien ya reprobó o va atrasado; no se cita ninguna norma | Decisión de diseño |
| Umbral de rezago **6** créditos (alerta alta desde 12) | `UMBRAL_REZAGO_CREDITOS` | 6 créditos son dos cursos típicos de 3 créditos: el atraso mínimo que ya cambia el semestre en que el estudiante termina. La cifra coincide con los dos cursos que el artículo 85 permite matricular a un estudiante en recuperación académica, pero es una analogía y no una derivación | Decisión de diseño |
| Horas libres requeridas **96** y **5** pilares de competencias digitales | `HORAS_LIBRES_REQUERIDAS`, tablas de competencias | Son reglas de la UNAB tomadas de las publicaciones oficiales y registradas en [`CONTRATO.md`](CONTRATO.md) | Fuente UNAB |
| Máximo **16** semestres en la proyección | `MAX_SEMESTRES_PROYECCION` | Tope de seguridad para que la proyección termine aunque haya cursos que no se puedan ubicar (el plan tiene 9 semestres) | Decisión de diseño |
| Prerrequisitos (43) | Tabla `prerrequisitos` | La UNAB no los publica; son simulados y se marcan así en todas las respuestas | Simulado, declarado |

## 5. Lo que no se pudo sustentar con una fuente

- Temperaturas 0.2 y 0, ventana de memoria de 8, `maxIterations` 6, `maxOutputTokens` 1024, tope de 1800 caracteres, límites de entrada
  (1000 y 100), frecuencia de 6 horas y reintentos exactos: son decisiones de diseño con una razón de ingeniería, sin experimento que las
  compare con otros valores.
- Cargas 14, 16 y 20 y umbral de rezago 6: heurísticas propias; el reglamento no fija carga mínima, máxima ni recomendada de créditos.
- Dimensión 768 frente a 3072 y modelo de embeddings frente a otros modelos: no se compararon; solo se midió que 768 recupera bien en las
  pruebas del repositorio.
- Umbral 0.35: la evidencia medida lo contradice como barrera de tema (ver [`rag.md`](rag.md)); se recomienda 0.65 y queda pendiente
  validarlo con más preguntas.
