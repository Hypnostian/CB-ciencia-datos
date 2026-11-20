# Calendario académico en Google Sheets

El workflow 02 lee el calendario desde una hoja de Google. El archivo fuente es `data/calendario_academico.csv`.

## Pasos
1. Entrar a https://sheets.google.com con la cuenta que usará n8n y crear una hoja nueva: *Archivo > Importar > Subir* y seleccionar `data/calendario_academico.csv` (separador: coma; *Reemplazar hoja actual*).
2. Renombrar la pestaña a **`calendario_academico`** (es el nombre que busca el nodo *Leer hoja de calendario*).
3. Verificar que la primera fila contiene los encabezados `evento`, `categoria`, `fecha_inicio`, `fecha_fin`, `verificado`, `fuente_url` (mismos nombres que la tabla `calendario_academico`). Fechas en formato `AAAA-MM-DD`. Si el CSV usa otros nombres, ajuste el código del nodo *Armar prompt* del workflow 02.
4. Copiar el **ID de la hoja** desde la URL: `https://docs.google.com/spreadsheets/d/<ID_DE_LA_HOJA>/edit` y pegarlo en el nodo *Config* del workflow 00 (`GOOGLE_SHEET_ID`).
5. En n8n crear la credencial `Google Sheets` (OAuth2) con la misma cuenta y darle acceso a la hoja.

## Notas
- Las filas con `verificado = false` hacen que el chatbot avise que la fecha debe confirmarse en el calendario oficial de la UNAB.
- Para actualizar el calendario basta editar la hoja: el workflow la lee en cada consulta (no hay que reimportar nada).
