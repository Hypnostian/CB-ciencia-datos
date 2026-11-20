# Configuración de Supabase (PostgreSQL + pgvector)

Supabase aloja la base de datos que **simula Banner-Cosmos** (estudiantes, matrículas, planes), los documentos con embeddings (pgvector), noticias y la memoria del chat.

## 1. Crear el proyecto
1. En https://supabase.com crear una cuenta y un proyecto (`cb-ciencia-datos`, región cercana, plan gratuito).
2. Guardar la **contraseña de la base de datos** en un gestor de contraseñas.

## 2. Habilitar pgvector
En *SQL Editor* ejecutar:
```sql
create extension if not exists vector with schema extensions;
```
(o *Database > Extensions > vector > Enable*). Las migraciones también la crean si hace falta.

## 3. Ejecutar las migraciones, en orden
Los archivos están en `db/migrations/`. Abrirlos en orden numérico (`001_...`, `002_...`) y pegar cada uno en el *SQL Editor* (o usar `psql`):
```bash
for f in db/migrations/*.sql; do psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"; done
```
Resultado esperado: tablas (`programas`, `cursos`, `estudiantes`, `matriculas`, `documentos`, `documentos_fragmentos`, `noticias`, `n8n_chat_histories`,
`competencias_digitales`, `resultados_competencias`, `horas_libres`, ...), las vistas `v_*` y la función `match_documentos`.

En una base que ya tiene datos, la migración 005 (competencias digitales y horas libres) se aplica sin recargar el seed con
`python db/seed/cargar.py --requisitos`: crea las tablas y genera los resultados de la prueba y las horas libres de cada estudiante.
La 006 activa `security_invoker` en las vistas de la 003 para que respeten el RLS.

Forma corta (migraciones y seed en un paso): `python db/seed/cargar.py --migrar`. Para ver las tablas con datos: `python db/ver_tablas.py`.

## 4. Cargar los datos sintéticos
```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/seed/seed.sql
```
Esto carga estudiantes, matrículas, NRC e historial CCD **sintéticos** junto a los planes de estudio y profesores oficiales.

## 5. Obtener la cadena de conexión (pooler)
1. Botón **Connect** del proyecto > *Connection string* > **Transaction pooler** (puerto 6543).
2. Formato: `postgresql://postgres.PROYECTO:CLAVE@aws-0-REGION.pooler.supabase.com:6543/postgres?sslmode=require`
3. Es el valor de `DATABASE_URL` (servidor MCP, scraper, ingesta RAG). En n8n se usa en la credencial *Supabase Postgres*: host `aws-0-REGION.pooler.supabase.com`, puerto `6543`, base `postgres`, usuario `postgres.PROYECTO`, SSL activado.
4. Para migraciones largas puede usarse el *Session pooler* (5432).

## 6. Verificación
```sql
select count(*) from estudiantes;
select * from v_avance_plan limit 3;
select count(*) from documentos_fragmentos;   -- 0 hasta correr la ingesta (workflow 05 o rag/)
select * from n8n_chat_histories limit 1;      -- debe existir la tabla
select * from v_competencias_estudiante where estudiante_codigo = 'U00134229';
select count(*) filter (where horas_cumplidas >= 96) from horas_libres;
```

## Seguridad
- No subir `DATABASE_URL` ni claves a git. Rotar la contraseña si se expone.
- El acceso es solo desde el servidor MCP, n8n y los scripts con la cadena de conexión; no se exponen las tablas por la API REST pública de Supabase (activar Row Level Security sin políticas si se desea bloquear esa vía).
