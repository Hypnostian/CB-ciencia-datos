"""Se conecta a la base (Supabase) y muestra las tablas con datos: conteos y ejemplos del modelo académico.

Uso (desde la raíz del proyecto; lee DATABASE_URL del .env sin imprimirla):
    python db/ver_tablas.py                 # conteos, plan por semestre, prerrequisitos y un estudiante de ejemplo
    python db/ver_tablas.py U00179961       # el mismo resumen con otro estudiante
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TABLAS = ["programas", "cursos", "prerrequisitos", "periodos", "secciones", "estudiantes", "matriculas", "profesores",
          "cursos_ccd", "historial_ccd", "competencias_digitales", "resultados_competencias", "horas_libres",
          "calendario_academico", "noticias", "documentos", "documentos_fragmentos", "n8n_chat_histories"]


def cargar_env() -> None:
    for linea in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in linea and not linea.strip().startswith("#"):
            k, v = linea.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def tabla(filas: list[tuple], encabezados: list[str]) -> str:
    textos = [[("" if v is None else str(v)) for v in f] for f in filas]
    anchos = [max(len(h), *(len(f[i]) for f in textos)) if textos else len(h) for i, h in enumerate(encabezados)]
    linea = " | ".join(h.ljust(a) for h, a in zip(encabezados, anchos))
    sep = "-+-".join("-" * a for a in anchos)
    return "\n".join([linea, sep] + [" | ".join(v.ljust(a) for v, a in zip(f, anchos)) for f in textos])


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    codigo = (sys.argv[1] if len(sys.argv) > 1 else "U00179961").upper()
    cargar_env()
    import psycopg

    with psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None) as c:
        version = c.execute("select split_part(version(), ' on ', 1)").fetchone()[0]
        print(f"Conectado a {version} (Supabase)\n")
        print(tabla([(t, c.execute(f"select count(*) from {t}").fetchone()[0]) for t in TABLAS], ["tabla", "filas"]))

        print("\nPlan de estudios (cursos por semestre):")
        filas = c.execute("""select semestre_plan, count(*), sum(creditos),
                                    string_agg(nombre, ', ' order by codigo) from cursos group by 1 order by 1""").fetchall()
        print(tabla([(s, n, cr, (txt[:78] + "...") if len(txt) > 80 else txt) for s, n, cr, txt in filas],
                    ["sem", "cursos", "créditos", "cursos"]))

        print("\nPrerrequisitos (simulados) de ejemplo:")
        print(tabla(c.execute("""select c.codigo, c.nombre, r.nombre from prerrequisitos p join cursos c on c.id = p.curso_id
                                 join cursos r on r.id = p.requisito_id where c.semestre_plan between 4 and 9
                                 order by c.codigo limit 6""").fetchall(), ["código", "curso", "requiere"]))

        e = c.execute("select codigo, nombres || ' ' || apellidos, semestre_actual, estado, fecha_ingreso from estudiantes "
                      "where codigo = %s", (codigo,)).fetchone()
        print(f"\nEstudiante {e[0]}: {e[1]}, semestre {e[2]}, {e[3]}, ingreso {e[4]}")
        print(tabla(c.execute("""select m.periodo_id, s.nrc, cu.nombre, cu.creditos, m.estado, m.nota_final
                                 from matriculas m join secciones s on s.nrc = m.nrc join cursos cu on cu.id = s.curso_id
                                 where m.estudiante_codigo = %s order by m.periodo_id desc, cu.codigo limit 9""",
                              (codigo,)).fetchall(), ["periodo", "nrc", "curso", "cr", "estado", "nota"]))
        a = c.execute("select creditos_aprobados, total_creditos, porcentaje_avance, semestre_real from v_avance_plan "
                      "where estudiante_codigo = %s", (codigo,)).fetchone()
        print(f"Avance (vista v_avance_plan): {a[0]} de {a[1]} créditos ({a[2]}%), semestre real {a[3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
