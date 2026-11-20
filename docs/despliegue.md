# Guía de despliegue de extremo a extremo

Orden recomendado: **Supabase, EC2 + MCP, n8n Cloud, Google Sheets, Android**. Tiempo estimado: 1 a 2 horas.

## 0. Requisitos
- Cuenta gratuita de Supabase, AWS (EC2), n8n Cloud (prueba o plan de estudiante) y Google.
- Clave gratuita de Gemini en https://aistudio.google.com/apikey.
- Valores propios (no se suben a git): `GEMINI_API_KEY`, `MCP_API_KEY` y `CHAT_TOKEN` (genere con `openssl rand -hex 32`).

## 1. Supabase (base de datos y pgvector)
Seguir `infra/supabase_setup.md`: crear proyecto, copiar la cadena del *pooler* como `DATABASE_URL` en el `.env` y ejecutar
`python db/seed/cargar.py --migrar --regenerar` (migraciones 001 a 006, datos con el plan oficial de 151 créditos y estudiantes fijos).
Comprobar con `python db/ver_tablas.py`.

## 2. Documentos para el RAG (embeddings)
Opción A, desde el computador: `rag/` (ver su README) con `DATABASE_URL` y `GEMINI_API_KEY`.
Opción B, desde n8n: workflow `05_ingesta_embeddings.json` (paso 4), con límites equivalentes pero sin fragmentación por estructura (ver `docs/rag.md`). El índice de producción (145 documentos, 434 fragmentos) se construyó con la opción A.
Verificar: `select count(*) from documentos_fragmentos;` mayor que 0.

## 3. EC2 + servidor MCP
1. Crear la instancia (Ubuntu 24.04; el proyecto usó una `t2.large` compartida del laboratorio de AWS Academy) con el Security Group de `infra/SECURITY_GROUPS.md` (en una instancia propia, 22 solo desde su IP y 9000 abierto con `X-API-Key`; lo que quedó abierto en la compartida y sus riesgos están en ese documento).
2. Copiar el proyecto: `scp -i clave.pem -r CB-ciencia-datos ubuntu@IP:~/` (o `git clone`).
3. En una instancia **propia** se puede usar `cd CB-ciencia-datos/infra && cp .env.example .env && nano .env && sudo bash ec2_setup.sh`
   (Docker y ufw). En la instancia compartida de AWS Academy se usó en su lugar un entorno virtual de Python y el servicio
   `infra/cb-mcp.service` (ver sección 10), porque `ec2_setup.sh` activa ufw y bloquearía los otros proyectos.
4. Probar desde su computador: `curl -i http://IP:9000/mcp` (sin clave responde 401) y con `X-API-Key` según `SECURITY_GROUPS.md`.
5. Anotar `MCP_URL = http://IP:9000`.

## 4. n8n Cloud
Seguir `infra/n8n_cloud_setup.md`: crear credenciales (`Gemini API`, `Supabase Postgres`, `Google Sheets`, `MCP API Key`), importar 01 a 05 y por último 00, editar el nodo **Config** (`MCP_URL`, `CHAT_TOKEN`, `GOOGLE_SHEET_ID`), ejecutar 04 una vez (noticias), ejecutar 05 solo para agregar o refrescar documentos (el índice de producción se construyó con `rag/ingesta.py`, ver `docs/rag.md`) y publicar los seis flujos (00 a 05).

## 5. Google Sheets (calendario)
Seguir `infra/google_sheets.md`: subir `data/calendario_academico.csv`, pestaña `calendario_academico`, copiar el ID de la hoja al nodo *Config*.

## 6. Prueba del webhook
```bash
curl -X POST "https://TU-INSTANCIA.app.n8n.cloud/webhook/unab-chat" \
  -H "Content-Type: application/json" -H "X-Chat-Token: $CHAT_TOKEN" \
  -d '{"estudiante_codigo":"U00123456","session_id":"prueba-1","mensaje":"¿Qué cursos debo tomar?"}'
```
Respuesta esperada: `{"respuesta": "...", "intencion": "cursos", "fuentes": [...]}`. Use un código existente en el seed.

## 7. App Android
1. Compilar e instalar: `cd android && ./gradlew assembleDebug` y `adb install -r app/build/outputs/apk/debug/app-debug.apk`. El APK debe compilarlo cada persona con su propio `android/local.properties`. Si ese archivo trae `N8N_WEBHOOK_URL` y `CHAT_TOKEN`, ambos valores quedan **dentro del APK** (`BuildConfig`): nunca publique ni comparta un APK compilado con valores reales. Para repartir un APK, compile sin esas dos claves en `local.properties` y entregue la URL y el token por otro canal.
2. En la app, **Ajustes del webhook**: pegar `N8N_WEBHOOK_URL` y `CHAT_TOKEN` (se guardan solo en el dispositivo, nunca en el código del repositorio).
3. Ingresar con un código de demostración y probar las consultas del manual de usuario (`docs/manual_usuario.md`).

## 8. Lista de verificación
- [ ] `select count(*) from estudiantes;` devuelve datos sintéticos.
- [ ] `documentos_fragmentos` tiene filas y `match_documentos` devuelve resultados.
- [ ] El puerto 9000 responde 401 sin clave (en una instancia propia, solo 22 y 9000 abiertos; en la compartida, ver `infra/SECURITY_GROUPS.md`).
- [ ] Workflow 04 ejecutado: `select count(*) from noticias;` mayor que 0.
- [ ] Workflow 00 publicado; webhook sin token devuelve 401.
- [ ] La app muestra respuesta con fuentes.

## 9. Problemas frecuentes
| Síntoma | Causa y solución |
|---|---|
| El workflow 00 falla al llamar subflujos | Los subflujos no están importados o publicados; reseleccione el workflow en el nodo *Subflujo ...* |
| `dimension mismatch` en pgvector | Embeddings no son de 768; confirmar `outputDimensionality: 768` |
| Nodo MCP: error 401 | Credencial `MCP API Key` con nombre `X-API-Key` y valor igual a `MCP_API_KEY` |
| Nodo MCP: timeout | Puerto 9000 cerrado en el Security Group o servicio caído (`systemctl status cb-mcp`) |
| Gemini 429 | Límite por minuto del plan gratuito: los agentes reintentan 3 veces y, si aun así falla, la app recibe un mensaje claro; esperar un minuto. Estos 429 explican las ejecuciones fallidas del panel de n8n (ver el README) |
| Hoja no encontrada | Compartir la hoja con la cuenta de la credencial y nombrar la pestaña `calendario_academico` |

## 10. Ajustes aplicados en el despliegue real (13-nov-2026)
Lo que se cambió respecto a los pasos anteriores al desplegar el proyecto, y por qué:

- **Supabase:** se usa el *Session pooler* (puerto 5432, IPv4) en lugar del *Transaction pooler*. Si la contraseña de la
  base tiene símbolos (`# $ % & /`), en `DATABASE_URL` deben ir codificados (`%23 %24 %25 %26 %2F`).
  Los scripts (`cargar.py`, `rag/ingesta.py`, `scraper/`) abren la conexión con `prepare_threshold=None`, compatible con el pooler.
- **Gemini:** `gemini-2.5-flash` ya no está disponible para claves nuevas. Se usa `gemini-3.5-flash-lite` (responde en ~1 s).
  En el clasificador del flujo 00, `thinkingBudget: 0` se reemplazó por `thinkingLevel: 'minimal'` (el modelo nuevo rechaza el primero).
  El plan gratuito limita las peticiones por minuto: si aparece *429 Too Many Requests*, espere un minuto.
- **EC2:** la instancia (`t2.large`, compartida del laboratorio) ya alojaba otros servicios, así que no se ejecutó `ec2_setup.sh` (activa `ufw` y bloquearía sus puertos).
  El servidor MCP corre como servicio systemd (`infra/cb-mcp.service`) con un entorno virtual de Python, sin Docker.
  El Security Group debe permitir el puerto 9000 desde `0.0.0.0/0`: si solo permite "My IP", n8n Cloud responde
  *Could not connect to your MCP server*. Los riesgos de esa decisión y cómo endurecerla están en `infra/SECURITY_GROUPS.md`.
- **n8n Cloud (plan de prueba):** la API pública no está disponible, así que los flujos se importan desde la interfaz:
  **Workflows > Import from File** con cada JSON de `n8n/workflows/`, primero 01 a 05 y al final 00. En el flujo 00, cada nodo
  *Execute Workflow* (Subflujo 01 RAG, 02 Calendario, 03 Cursos, 03 Matricula, 04 Noticias) se enlaza eligiendo en la lista el subflujo
  importado, porque los IDs cambian al importar. Después se completa el nodo Config (`MCP_URL`, `CHAT_TOKEN`, `GOOGLE_SHEET_ID`), se asignan
  las credenciales (Gemini API en 00, 01, 02, 03, 04 y 05; Postgres en 01, 02, 03, 04 y 05; Google Sheets OAuth2 en 02; Header Auth del MCP
  en 00 y 03) y se publican los seis flujos.
- **Credencial Postgres en n8n:** SSL `Require` y en *CA Certificate* el certificado raíz de Supabase
  (`prod-ca-2021.crt`, se descarga en Supabase > Database > Settings > SSL configuration). Así n8n verifica el
  certificado sin desactivar la validación.
- **Verificación de extremo a extremo:** con el estudiante demo `U00100001` responden las rutas de créditos (cursos),
  cursos inscritos con NRC (matrícula), calendario (Google Sheets), noticias (Supabase) y consultas generales (RAG con fuentes).

## 11. Competencias digitales y horas libres (17-nov-2026)
1. **Supabase:** `python db/seed/cargar.py --requisitos` aplica `005_competencias_horas.sql` y llena `resultados_competencias` y `horas_libres`
   para todos los estudiantes (incluidos los creados en vivo por el servidor), sin recargar el seed.
2. **EC2:** copiar `mcp-server/app/*.py` a `~/cb-ciencia-datos/mcp-server/app/` (con un respaldo previo de la carpeta `app`) y
   `sudo systemctl restart cb-mcp`. Verificar con `python infra/probar_mcp.py U00134229` (14 herramientas).
3. **n8n:** importar de nuevo los flujos que cambiaron (clasificador del flujo 00, prompt y herramientas MCP del flujo 03) con
   **Workflows > Import from File**, reasignar las credenciales, conservar el nodo Config y publicar.
4. **Prueba:** `python n8n/herramientas/probar_webhook.py "U00134229|¿Qué competencias digitales me faltan?"`.
5. **AWS Academy (Learner Lab):** la instancia se apaga al terminar la sesión del laboratorio y arranca al iniciarla. Tiene una IP elástica,
   así que `MCP_URL` no cambia, y el servicio `cb-mcp` está habilitado en systemd, así que vuelve a quedar arriba solo. Si el chat responde
   "error 500" justo al iniciar el laboratorio, espere uno o dos minutos a que la instancia termine de arrancar.

## 12. Plan oficial, noticias del día y documentación final (18-nov-2026)
1. **Plan de estudios:** `db/seed/planes.py` usa el documento oficial de la página del programa (151 créditos). Se regeneraron los datos
   con los mismos 120 estudiantes (`db/seed/estudiantes_base.csv`) y se recargó la base: `python db/seed/cargar.py --migrar --regenerar`.
2. **RAG:** se reemplazó el documento del plan de 134 créditos por el de 151 (`python rag/ingesta.py --solo "plan usado por el asistente"`
   y borrado del documento anterior). `python rag/evaluar_chunks.py` evalúa el índice.
3. **Servidor MCP:** copiar `mcp-server/app/*.py` a la instancia (respaldo previo de `app`) y `sudo systemctl restart cb-mcp`. Nuevo
   endpoint `POST /api/noticias`.
4. **n8n:** importar de nuevo los JSON modificados (**Workflows > Import from File**) y publicar. El flujo 04 corre cada 6 horas con
   7 fuentes; para llenarlo de inmediato se ejecuta una vez a mano con **Execute workflow**.
5. **Supabase:** migración `006_seguridad_vistas.sql` (`security_invoker` en las vistas de 003).
6. **App:** pantalla Noticias del día; compilar e instalar como en la sección 7.
7. **Verificación:** `python n8n/herramientas/probar_webhook.py "U00179961|@perfil" "U00179961|@noticias" "U00179961|¿Qué cursos debo tomar?"`
   y la pestaña **Executions** de n8n.

