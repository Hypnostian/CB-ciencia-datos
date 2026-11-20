-- 002_esquema.sql
-- Esquema public que simula Banner-Cosmos (datos sintéticos de estudiantes) más
-- las tablas del chatbot (documentos RAG, noticias, memoria de n8n).
-- Es idempotente: se puede ejecutar varias veces.

create table if not exists programas (
  id             serial primary key,
  codigo         text not null unique,
  nombre         text not null,
  total_creditos int  not null check (total_creditos > 0),
  fuente_url     text
);

create table if not exists cursos (
  id            serial primary key,
  programa_id   int  not null references programas(id) on delete cascade,
  codigo        text not null unique,
  nombre        text not null,
  creditos      int  not null check (creditos >= 0),
  semestre_plan int  not null check (semestre_plan between 1 and 12),
  tipo          text not null default 'obligatorio' check (tipo in ('obligatorio','electivo')),
  es_oficial    boolean not null default true
);
create index if not exists idx_cursos_programa on cursos(programa_id, semestre_plan);

-- UNAB no publica prerrequisitos: los generados llevan es_simulado = true.
create table if not exists prerrequisitos (
  curso_id     int not null references cursos(id) on delete cascade,
  requisito_id int not null references cursos(id) on delete cascade,
  es_simulado  boolean not null default true,
  primary key (curso_id, requisito_id),
  check (curso_id <> requisito_id)
);
create index if not exists idx_prerreq_requisito on prerrequisitos(requisito_id);

create table if not exists periodos (
  id           text primary key check (id ~ '^[0-9]{4}-[12]$'),
  nombre       text not null,
  fecha_inicio date not null,
  fecha_fin    date not null,
  actual       boolean not null default false,
  check (fecha_fin > fecha_inicio)
);
-- A lo sumo un periodo actual.
create unique index if not exists uq_periodo_actual on periodos(actual) where actual;

-- Datos públicos de APOLO (solo para buscar_profesor; nunca se asignan a secciones).
create table if not exists profesores (
  id         serial primary key,
  nombre     text not null,
  unidad     text,
  cargo      text,
  apolo_url  text unique,
  cvlac_url  text
);

-- Secciones simuladas con docentes sintéticos.
create table if not exists secciones (
  nrc        char(5) primary key check (nrc ~ '^[0-9]{5}$'),
  curso_id   int  not null references cursos(id) on delete cascade,
  periodo_id text not null references periodos(id) on delete cascade,
  docente    text,
  horario    text,
  cupo       int  not null default 35 check (cupo > 0)
);
create index if not exists idx_secciones_curso_periodo on secciones(curso_id, periodo_id);

create table if not exists estudiantes (
  codigo          text primary key check (codigo ~ '^U00[0-9]{6}$'),
  nombres         text not null,
  apellidos       text not null,
  correo          text not null,
  programa_id     int  not null references programas(id),
  semestre_actual int  not null check (semestre_actual between 1 and 12),
  estado          text not null default 'activo' check (estado in ('activo','inactivo','graduado')),
  fecha_ingreso   date not null
);
create index if not exists idx_estudiantes_programa on estudiantes(programa_id);

create table if not exists matriculas (
  id                serial primary key,
  estudiante_codigo text not null references estudiantes(codigo) on delete cascade,
  nrc               char(5) not null references secciones(nrc) on delete cascade,
  periodo_id        text not null references periodos(id),
  estado            text not null check (estado in ('inscrita','cancelada','finalizada')),
  nota_final        numeric(2,1) check (nota_final is null or nota_final between 0 and 5),
  unique (estudiante_codigo, nrc)
);
create index if not exists idx_matriculas_estudiante on matriculas(estudiante_codigo, periodo_id);
create index if not exists idx_matriculas_nrc on matriculas(nrc);

create table if not exists cursos_ccd (
  id          serial primary key,
  ruta        int  not null check (ruta between 1 and 3),
  nombre      text not null,
  obligatorio boolean not null default false,
  descripcion text,
  fuente_url  text
);

create table if not exists historial_ccd (
  id                serial primary key,
  estudiante_codigo text not null references estudiantes(codigo) on delete cascade,
  curso_ccd_id      int  not null references cursos_ccd(id) on delete cascade,
  periodo_id        text not null references periodos(id),
  estado            text not null check (estado in ('aprobado','en_curso','reprobado')),
  fecha             date,
  unique (estudiante_codigo, curso_ccd_id, periodo_id)
);
create index if not exists idx_hist_ccd_estudiante on historial_ccd(estudiante_codigo);

-- Espejo de la hoja de Google del calendario académico.
create table if not exists calendario_academico (
  id           serial primary key,
  evento       text not null,
  categoria    text,
  fecha_inicio date,
  fecha_fin    date,
  verificado   boolean not null default false,
  fuente_url   text
);
create index if not exists idx_calendario_fecha on calendario_academico(fecha_inicio);

create table if not exists noticias (
  id        serial primary key,
  titulo    text not null,
  url       text not null unique,
  fecha     timestamptz,
  categoria text,
  resumen   text,
  fuente    text,
  creado_en timestamptz not null default now()
);
create index if not exists idx_noticias_fecha on noticias(fecha desc);

-- RAG: documentos institucionales y sus fragmentos con embeddings (Gemini, 768 dim).
create table if not exists documentos (
  id         serial primary key,
  titulo     text not null,
  fuente_url text not null unique,
  tipo       text
);

create table if not exists documentos_fragmentos (
  id           bigserial primary key,
  documento_id int not null references documentos(id) on delete cascade,
  contenido    text not null,
  metadata     jsonb not null default '{}'::jsonb,
  embedding    vector(768)
);
create index if not exists idx_fragmentos_documento on documentos_fragmentos(documento_id);
create index if not exists idx_fragmentos_embedding
  on documentos_fragmentos using hnsw (embedding vector_cosine_ops);

-- Memoria persistente del nodo Postgres Chat Memory de n8n.
create table if not exists n8n_chat_histories (
  id         serial primary key,
  session_id varchar(255) not null,
  message    jsonb not null
);
create index if not exists idx_n8n_chat_session on n8n_chat_histories(session_id);

-- En Supabase las tablas de public quedan expuestas por la API REST. Se activa RLS
-- sin políticas: el acceso anónimo queda cerrado; el servidor MCP y n8n usan la
-- conexión directa de PostgreSQL (rol dueño de las tablas), que no se ve afectada.
alter table programas             enable row level security;
alter table cursos                enable row level security;
alter table prerrequisitos        enable row level security;
alter table periodos              enable row level security;
alter table profesores            enable row level security;
alter table secciones             enable row level security;
alter table estudiantes           enable row level security;
alter table matriculas            enable row level security;
alter table cursos_ccd            enable row level security;
alter table historial_ccd         enable row level security;
alter table calendario_academico  enable row level security;
alter table noticias              enable row level security;
alter table documentos            enable row level security;
alter table documentos_fragmentos enable row level security;
alter table n8n_chat_histories    enable row level security;
