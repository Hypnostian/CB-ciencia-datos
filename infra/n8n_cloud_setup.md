# Configuración de n8n Cloud

## 1. Importar los workflows (en este orden)
Los JSON están en `n8n/workflows/`. En n8n Cloud: *Workflows > menú (...) > Import from file*.

| Orden | Archivo | Rol |
|---|---|---|
| 1 | `01_consulta_general_rag.json` | Subflujo RAG |
| 2 | `02_calendario.json` | Subflujo calendario (Google Sheets) |
| 3 | `03_cursos_realizados.json` | Subflujo personalizado (cliente MCP) |
| 4 | `04_noticias_scraper.json` | Scraper programado + subflujo de noticias |
| 5 | `05_ingesta_embeddings.json` | Ingesta de documentos (manual) |
| 6 | `00_chat_principal.json` | Webhook principal que invoca a 01 a 04 |

Importe **00 al final**: sus nodos *Execute Workflow* apuntan a los subflujos. Si al importar n8n asigna otros identificadores, abra cada nodo *Subflujo ...* del workflow 00 y vuelva a elegir el workflow correspondiente en la lista.

## 2. Crear las credenciales
| Nombre exacto | Tipo en n8n | Datos |
|---|---|---|
| `Gemini API` | *Google Gemini(PaLM) Api* | API key de Google AI Studio (gratuita) |
| `Supabase Postgres` | *Postgres* | Host y usuario del *Session pooler* (puerto 5432), base `postgres`, SSL: require y en *CA Certificate* el certificado `prod-ca-2021.crt` de Supabase |
| `Google Sheets` | *Google Sheets OAuth2 API* | Conectar con la cuenta de Google que posee la hoja |
| `MCP API Key` | *Header Auth* | Name: `X-API-Key`, Value: el `MCP_API_KEY` del servidor |

Después de importar, abra cada nodo con aviso rojo (Gemini, Postgres, Google Sheets, MCP) y seleccione la credencial correspondiente. Los JSON no contienen secretos.

## 3. Variables de configuración
n8n Cloud no permite variables de entorno propias en todos los planes, por eso se usa el nodo **Config** (Set) al inicio del workflow 00:

| Campo | Valor |
|---|---|
| `MCP_URL` | `http://IP_PUBLICA_EC2:9000` (sin `/mcp`) |
| `CHAT_TOKEN` | Secreto compartido; el mismo que lleva la app Android en `X-Chat-Token` |
| `GOOGLE_SHEET_ID` | ID de la hoja (ver `google_sheets.md`) |

Edite esos tres valores en el nodo *Config*. (Si su plan ofrece *Variables*, puede reemplazarlos por `{{ $vars.MCP_URL }}` etc.)

## 4. Cargar los documentos y las noticias
- Workflow **05**: es la vía dentro de n8n para agregar o refrescar documentos (el índice de producción se construyó con `rag/ingesta.py`, ver `docs/rag.md`). Editar la lista del nodo *Documentos (URL)* (textos accesibles por URL) y ejecutar manualmente. En n8n local se usa también la rama que lee `/data/oficial/docs/*.txt`. Alternativa: `rag/` carga los mismos documentos desde el computador.
- Workflow **04**: ejecutarlo una vez a mano (rama *Cada 6 horas*) para llenar `noticias`; después corre solo cada 6 horas.

## 5. Activar
1. Publicar **01, 02, 03, 04** (los subflujos y el programado), **05** (manual) y **00** (botón *Publish*).
2. La URL de producción del webhook es `https://TU-INSTANCIA.app.n8n.cloud/webhook/unab-chat` (nodo *Webhook chat* > *Production URL*). Es el valor `N8N_WEBHOOK_URL` que usa la app.
3. Probar:
```bash
curl -X POST "$N8N_WEBHOOK_URL" -H "Content-Type: application/json" -H "X-Chat-Token: $CHAT_TOKEN" \
  -d '{"estudiante_codigo":"U00123456","session_id":"prueba-1","mensaje":"¿Qué es la insignia de competencias digitales?"}'
```
Sin el encabezado correcto debe responder 401.

## Notas
- Los nodos *Agente* usan Gemini (`gemini-3.5-flash-lite`) y la memoria *Postgres Chat Memory* (tabla `n8n_chat_histories`, clave `codigo:session_id`).
- Plan gratuito de Gemini: límite de peticiones por minuto; la ingesta usa pausas de 700 ms entre embeddings y los agentes reintentan 3 veces.
- Para cambios posteriores, edite los JSON de `n8n/workflows/`, impórtelos de nuevo con **Workflows > Import from File** y publique. La
  pestaña **Executions** de n8n muestra cada ejecución nodo por nodo.
