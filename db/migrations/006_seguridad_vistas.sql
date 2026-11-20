-- 006_seguridad_vistas.sql
-- Las vistas de 003 se crearon sin security_invoker: en Supabase se ejecutan con los permisos de su dueño y la API
-- REST (rol anon con la clave pública) podría leerlas aunque las tablas tengan RLS ("UNRESTRICTED" en el panel).
-- Con security_invoker = true cada vista respeta el RLS de las tablas que consulta. El servidor MCP y n8n se conectan
-- con el usuario dueño de las tablas, así que siguen leyéndolas igual. Es idempotente.

alter view v_cursos_estudiante     set (security_invoker = true);
alter view v_estado_matricula      set (security_invoker = true);
alter view v_avance_plan           set (security_invoker = true);
alter view v_proyeccion_semestres  set (security_invoker = true);
alter view v_requisitos_pendientes set (security_invoker = true);
alter view v_historial_ccd         set (security_invoker = true);
