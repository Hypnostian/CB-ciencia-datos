-- 004_funciones.sql
-- Funciones auxiliares y búsqueda semántica (RPC).

-- Normaliza texto para búsquedas sin tildes ni mayúsculas (sin depender de la extensión unaccent).
create or replace function norm_texto(t text) returns text
language sql immutable parallel safe as $$
  select lower(translate(coalesce(t, ''), 'áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunaeiouun'))
$$;

-- Búsqueda por similitud coseno sobre los fragmentos del RAG.
create or replace function match_documentos(
  query_embedding vector(768),
  match_count int default 5
)
returns table (
  id           bigint,
  documento_id int,
  titulo       text,
  fuente_url   text,
  contenido    text,
  similitud    float
)
language sql stable as $$
  select
    f.id,
    f.documento_id,
    d.titulo,
    d.fuente_url,
    f.contenido,
    1 - (f.embedding <=> query_embedding) as similitud
  from documentos_fragmentos f
  join documentos d on d.id = f.documento_id
  where f.embedding is not null
  order by f.embedding <=> query_embedding
  limit greatest(match_count, 1)
$$;
