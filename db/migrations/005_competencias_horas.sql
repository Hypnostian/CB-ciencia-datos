-- 005_competencias_horas.sql
-- Requisito de grado "Competencias Digitales R2025" (resultado de la prueba por pilar) y horas libres.
-- Los pilares son los que muestra el portal del estudiante; los resultados y las horas de cada estudiante son
-- SINTÉTICOS. Es idempotente: se puede ejecutar varias veces.

-- Pilares del requisito. "materia" es la prueba con la que se cumple el pilar (así aparece en el portal).
create table if not exists competencias_digitales (
  id          serial primary key,
  orden       int  not null unique,
  nombre      text not null unique,
  materia     text not null,
  requisito   text not null default 'Competencias Digitales R2025',
  fuente_url  text
);

-- Un resultado por estudiante y pilar: la prueba se presenta una sola vez por pilar.
-- Si no se aprueba, el estudiante debe inscribir el curso del pilar (regla publicada por la UNAB).
create table if not exists resultados_competencias (
  estudiante_codigo text not null references estudiantes(codigo) on delete cascade,
  competencia_id    int  not null references competencias_digitales(id) on delete cascade,
  aprobada          boolean not null,
  fecha_prueba      date not null,
  primary key (estudiante_codigo, competencia_id)
);
create index if not exists idx_resultados_comp_estudiante on resultados_competencias(estudiante_codigo);

-- Horas libres acumuladas. Para graduarse se requieren 96 (las que pasen de 96 cuentan como requisito cumplido).
create table if not exists horas_libres (
  estudiante_codigo text primary key references estudiantes(codigo) on delete cascade,
  horas_cumplidas   int  not null check (horas_cumplidas >= 0),
  horas_requeridas  int  not null default 96 check (horas_requeridas > 0),
  actualizado       date not null default current_date
);

insert into competencias_digitales (orden, nombre, materia, fuente_url) values
  (1, 'Vida en línea',   'Examen Vida en línea',   'https://unab.edu.co/inscripcion-a-las-pruebas-de-competencias-digitales-estudiantes-desde-sexto-semestre/'),
  (2, 'MS Word',         'Examen MS Word',         'https://unab.edu.co/inscripcion-a-las-pruebas-de-competencias-digitales-estudiantes-desde-sexto-semestre/'),
  (3, 'MS Excel',        'Examen MS Excel',        'https://unab.edu.co/inscripcion-a-las-pruebas-de-competencias-digitales-estudiantes-desde-sexto-semestre/'),
  (4, 'MS PowerPoint',   'Examen MS PowerPoint',   'https://unab.edu.co/inscripcion-a-las-pruebas-de-competencias-digitales-estudiantes-desde-sexto-semestre/'),
  (5, 'Cultura digital', 'Examen Cultura digital', 'https://unab.edu.co/inscripcion-a-las-pruebas-de-competencias-digitales-estudiantes-desde-sexto-semestre/')
on conflict (orden) do nothing;

-- Estado del requisito por estudiante (una fila por pilar).
create or replace view v_competencias_estudiante as
select
  r.estudiante_codigo,
  c.orden,
  c.nombre      as competencia,
  c.requisito,
  r.aprobada,
  case when r.aprobada then c.materia end as materia,
  r.fecha_prueba
from resultados_competencias r
join competencias_digitales c on c.id = r.competencia_id;

-- La vista respeta el RLS de las tablas (sin esto, Supabase la expone por la API REST como "unrestricted").
alter view v_competencias_estudiante set (security_invoker = true);

alter table competencias_digitales  enable row level security;
alter table resultados_competencias enable row level security;
alter table horas_libres            enable row level security;
