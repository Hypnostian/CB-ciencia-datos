-- 003_vistas.sql
-- Vistas analíticas sobre el esquema que simula Banner-Cosmos.
-- Regla de aprobación: nota_final >= 3.0 en una matrícula finalizada (escala 0.0 a 5.0).

-- Auxiliar: estado de cada curso del plan para cada estudiante.
create or replace view v_cursos_estudiante as
select
  e.codigo                         as estudiante_codigo,
  c.id                             as curso_id,
  c.codigo                         as curso_codigo,
  c.nombre                         as curso,
  c.creditos,
  c.semestre_plan,
  c.tipo,
  coalesce(h.aprobado, false)      as aprobado,
  coalesce(h.en_curso, false)      as en_curso,
  coalesce(h.intentos_reprobados, 0)::int as intentos_reprobados,
  h.mejor_nota,
  case
    when coalesce(h.aprobado, false)              then 'aprobado'
    when coalesce(h.en_curso, false)              then 'en_curso'
    when coalesce(h.intentos_reprobados, 0) > 0   then 'reprobado'
    else 'pendiente'
  end                              as estado
from estudiantes e
join cursos c on c.programa_id = e.programa_id
left join lateral (
  select
    bool_or(m.estado = 'finalizada' and m.nota_final >= 3.0)         as aprobado,
    bool_or(m.estado = 'inscrita')                                   as en_curso,
    count(*) filter (where m.estado = 'finalizada' and m.nota_final < 3.0) as intentos_reprobados,
    max(m.nota_final)                                                as mejor_nota
  from matriculas m
  join secciones s on s.nrc = m.nrc
  where m.estudiante_codigo = e.codigo and s.curso_id = c.id
) h on true;

-- Cursos inscritos en el periodo actual.
create or replace view v_estado_matricula as
select
  e.codigo                    as estudiante_codigo,
  e.nombres || ' ' || e.apellidos as estudiante,
  e.semestre_actual,
  p.id                        as periodo_id,
  s.nrc,
  c.codigo                    as curso_codigo,
  c.nombre                    as curso,
  c.creditos,
  s.docente                   as profesor,
  s.horario,
  m.estado                    as estado_matricula
from matriculas m
join estudiantes e on e.codigo = m.estudiante_codigo
join secciones s   on s.nrc = m.nrc
join cursos c      on c.id = s.curso_id
join periodos p    on p.id = m.periodo_id and p.actual
where m.estado = 'inscrita';

-- Avance de créditos frente al plan.
create or replace view v_avance_plan as
select
  e.codigo                                         as estudiante_codigo,
  pr.codigo                                        as programa_codigo,
  pr.nombre                                        as programa,
  pr.total_creditos,
  coalesce(sum(v.creditos) filter (where v.aprobado), 0)::int  as creditos_aprobados,
  coalesce(sum(v.creditos) filter (where v.en_curso and not v.aprobado), 0)::int as creditos_en_curso,
  round(100.0 * coalesce(sum(v.creditos) filter (where v.aprobado), 0) / pr.total_creditos, 1) as porcentaje_avance,
  count(*) filter (where v.aprobado)::int          as cursos_aprobados,
  count(*)::int                                    as cursos_plan,
  -- Semestre real = 1 + semestres completos del plan que cubren los créditos aprobados.
  1 + (
    select count(*) from (
      select sum(sum(cc.creditos)) over (order by cc.semestre_plan) as acumulado
      from cursos cc where cc.programa_id = pr.id group by cc.semestre_plan
    ) t
    where t.acumulado <= coalesce(sum(v.creditos) filter (where v.aprobado), 0)
  )::int                                           as semestre_real,
  e.semestre_actual                                as semestre_nominal
from estudiantes e
join programas pr on pr.id = e.programa_id
join v_cursos_estudiante v on v.estudiante_codigo = e.codigo
group by e.codigo, e.semestre_actual, pr.id, pr.codigo, pr.nombre, pr.total_creditos;

-- Estimación gruesa (cota inferior) de semestres restantes, a 18 créditos por semestre.
-- La proyección exacta con prerrequisitos la calcula la herramienta proyeccion_semestres.
create or replace view v_proyeccion_semestres as
select
  a.estudiante_codigo,
  a.total_creditos - a.creditos_aprobados                       as creditos_pendientes,
  a.creditos_en_curso,
  greatest(a.total_creditos - a.creditos_aprobados - a.creditos_en_curso, 0) as creditos_por_cursar,
  18                                                            as creditos_por_semestre_ref,
  ceil(greatest(a.total_creditos - a.creditos_aprobados - a.creditos_en_curso, 0) / 18.0)::int
                                                                as semestres_restantes_minimos,
  (select count(*) from v_cursos_estudiante v
     where v.estudiante_codigo = a.estudiante_codigo and v.estado = 'reprobado')::int
                                                                as cursos_reprobados_pendientes
from v_avance_plan a;

-- Una fila por cada prerrequisito sin cumplir de un curso que el estudiante aún no aprueba.
create or replace view v_requisitos_pendientes as
select
  v.estudiante_codigo,
  v.curso_id,
  v.curso_codigo,
  v.curso,
  v.semestre_plan,
  v.estado                 as estado_curso,
  r.id                     as requisito_id,
  r.codigo                 as requisito_codigo,
  r.nombre                 as requisito,
  vr.estado                as estado_requisito,
  pq.es_simulado
from v_cursos_estudiante v
join prerrequisitos pq on pq.curso_id = v.curso_id
join cursos r          on r.id = pq.requisito_id
join v_cursos_estudiante vr on vr.estudiante_codigo = v.estudiante_codigo and vr.curso_id = r.id
where not v.aprobado
  and not vr.aprobado;

create or replace view v_historial_ccd as
select
  h.estudiante_codigo,
  c.id          as curso_ccd_id,
  c.ruta,
  c.nombre      as curso_ccd,
  c.obligatorio,
  h.estado,
  h.periodo_id,
  h.fecha
from historial_ccd h
join cursos_ccd c on c.id = h.curso_ccd_id;
