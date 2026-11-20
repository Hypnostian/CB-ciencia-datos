"""Carga el seed sintético en PostgreSQL (Supabase o local) usando DATABASE_URL.

Uso (desde la raíz del proyecto):
    python db/seed/cargar.py              # ejecuta db/seed/seed.sql
    python db/seed/cargar.py --migrar     # aplica antes db/migrations/*.sql
    python db/seed/cargar.py --regenerar  # vuelve a generar CSV y seed.sql antes de cargar
    python db/seed/cargar.py --requisitos # solo aplica la migración 005 y completa competencias digitales y horas
                                          # libres de los estudiantes que no las tengan (no recarga el seed)

Requiere: pip install "psycopg[binary]" faker
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))


def cargar_env() -> None:
    """Lee un .env simple (CLAVE=valor) de la raíz del proyecto si existe; no pisa variables ya definidas."""
    ruta = RAIZ / ".env"
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            k, v = linea.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--migrar", action="store_true", help="aplica db/migrations/*.sql antes de cargar")
    ap.add_argument("--regenerar", action="store_true", help="regenera CSV y seed.sql antes de cargar")
    ap.add_argument("--requisitos", action="store_true",
                    help="solo migración 005 + competencias digitales y horas libres faltantes (sin recargar el seed)")
    args = ap.parse_args()

    cargar_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("Falta la variable de entorno DATABASE_URL.", file=sys.stderr)
        return 2

    if args.requisitos:
        return completar_requisitos(url)

    seed_sql = RAIZ / "db" / "seed" / "seed.sql"
    if args.regenerar or not seed_sql.exists():
        import generar_datos
        generar_datos.main()

    with psycopg.connect(url, autocommit=True, prepare_threshold=None) as conn:
        if args.migrar:
            for f in sorted((RAIZ / "db" / "migrations").glob("*.sql")):
                print(f"Migración {f.name}")
                conn.execute(f.read_text(encoding="utf-8"))
        print("Cargando seed.sql ...")
        conn.execute(seed_sql.read_text(encoding="utf-8"))
        for t in ["programas", "cursos", "prerrequisitos", "periodos", "profesores", "secciones", "estudiantes",
                  "matriculas", "cursos_ccd", "historial_ccd", "calendario_academico", "competencias_digitales",
                  "resultados_competencias", "horas_libres"]:
            n = conn.execute(f"select count(*) from {t}").fetchone()[0]
            print(f"  {t}: {n}")

    # Estudiantes con nombre fijo (mcp-server/app/estudiantes_fijos.json): se crean con las mismas reglas que usa el
    # servidor MCP al recibir un código nuevo, para que existan desde el principio y no cambien al recargar el seed.
    sys.path.insert(0, str(RAIZ / "mcp-server"))
    from psycopg.rows import dict_row
    from app import registro
    with psycopg.connect(url, autocommit=True, prepare_threshold=None, row_factory=dict_row) as conn:
        for codigo in registro.estudiantes_fijos():
            creado = registro.asegurar(conn, codigo)
            print(f"  estudiante fijo {codigo}: {'creado' if creado else 'ya existía'}")
        # Estudiantes creados en vivo por el servidor (códigos nuevos): competencias y horas libres si les faltan.
        faltan = conn.execute("select codigo from estudiantes e where not exists "
                              "(select 1 from horas_libres h where h.estudiante_codigo = e.codigo)").fetchall()
        for f in faltan:
            registro.asegurar_requisitos(conn, f["codigo"])
        if faltan:
            print(f"  competencias y horas libres completadas para {len(faltan)} estudiante(s)")
    print("Listo.")
    return 0


def completar_requisitos(url: str) -> int:
    """Aplica 005_competencias_horas.sql y genera los resultados de la prueba y las horas libres que falten."""
    sys.path.insert(0, str(RAIZ / "mcp-server"))
    from psycopg.rows import dict_row
    from app import registro
    with psycopg.connect(url, autocommit=True, prepare_threshold=None, row_factory=dict_row) as conn:
        print("Migración 005_competencias_horas.sql")
        conn.execute((RAIZ / "db" / "migrations" / "005_competencias_horas.sql").read_text(encoding="utf-8"))
        codigos = [r["codigo"] for r in conn.execute("select codigo from estudiantes order by codigo").fetchall()]
        creados = 0
        for codigo in codigos:
            with conn.transaction():
                creados += registro.asegurar_requisitos(conn, codigo)
        print(f"  estudiantes: {len(codigos)}, con requisitos nuevos: {creados}")
        for t in ["competencias_digitales", "resultados_competencias", "horas_libres"]:
            print(f"  {t}: {conn.execute(f'select count(*) as n from {t}').fetchone()['n']}")
        r = conn.execute("""select count(*) filter (where horas_cumplidas >= horas_requeridas) as completas,
                                   round(avg(horas_cumplidas)) as promedio from horas_libres""").fetchone()
        print(f"  horas libres: {r['completas']} estudiantes ya cumplen las 96 horas, promedio {r['promedio']}")
    print("Listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
