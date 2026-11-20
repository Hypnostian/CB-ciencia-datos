"""Pruebas del alta automática de estudiantes sintéticos (sin base de datos)."""
from datetime import date

from app import registro

PERIODOS = [f"{a}-{s}" for a in (2025, 2026) for s in (1, 2)]
HORARIOS = ["Lun-Mié 07:00-09:00", "Mar-Jue 07:00-09:00", "Vie 07:00-11:00", "Lun-Mié 09:00-11:00"]


def catalogo():
    cursos = [dict(id=i, creditos=3, semestre_plan=(i - 1) // 4 + 1) for i in range(1, 17)]
    secciones = {}
    nrc = 10000
    for c in cursos:
        for p in PERIODOS:
            for h in HORARIOS[:2]:
                nrc += 1
                secciones.setdefault((c["id"], p), []).append(dict(nrc=str(nrc), curso_id=c["id"], periodo_id=p, horario=h))
    periodos = [dict(id=p, fecha_inicio=date(int(p[:4]), 1 if p.endswith("1") else 8, 1),
                     fecha_fin=date(int(p[:4]), 5 if p.endswith("1") else 12, 1), actual=(p == "2026-2")) for p in PERIODOS]
    return dict(periodos=periodos, programa_id=1, cursos=cursos, reqs={5: [1], 9: [5]}, secciones=secciones,
                ccd={1: [1], 2: [2, 3, 4], 3: [5, 6, 7]})


def test_mismo_codigo_mismo_estudiante():
    cat = catalogo()
    assert registro.generar("U00123456", cat) == registro.generar("U00123456", cat)
    assert registro.generar("U00123456", cat)["estudiante"]["nombres"] != ""


def test_nombre_fijo_y_correo_demo():
    f = registro.generar("U00179643", catalogo(), {"nombres": "Juan Sebastián", "apellidos": "Lizcano Jaimes", "ingreso": "2025-1"})
    e = f["estudiante"]
    assert (e["nombres"], e["apellidos"]) == ("Juan Sebastián", "Lizcano Jaimes")
    assert e["correo"] == "u00179643@demo.unab.local"
    assert e["fecha_ingreso"] == date(2025, 1, 1)


def test_requisitos_deterministicos_y_en_rango():
    for cod in ("U00100001", "U00179643", "U00999999"):
        r = registro.requisitos(cod, date(2023, 1, 26))
        assert r == registro.requisitos(cod, "2023-01-26")
        assert [x["pilar"] for x in r["resultados"]] == registro.PILARES
        assert 0 <= r["horas_libres"] <= registro.HORAS_MAXIMAS
        assert len({x["fecha_prueba"] for x in r["resultados"]}) == 1
    # la prueba se presenta después del ingreso
    assert registro.requisitos("U00100004", date(2026, 8, 3))["resultados"][0]["fecha_prueba"] >= date(2026, 9, 1)


def test_sin_cruces_y_con_prerrequisitos():
    cat = catalogo()
    nrc_curso = {s["nrc"]: (k[0], s["horario"]) for k, v in cat["secciones"].items() for s in v}
    for cod in ("U00100100", "U00200200", "U00300300", "U00999999"):
        f = registro.generar(cod, cat)
        por_periodo = {}
        for m in f["matriculas"]:
            por_periodo.setdefault(m["periodo_id"], []).append(nrc_curso[m["nrc"]])
        for lista in por_periodo.values():
            horarios = [h for _, h in lista]
            assert len(horarios) == len(set(horarios)), "dos cursos con el mismo horario en un periodo"
        aprobados_antes = set()
        for p in PERIODOS:
            for curso, _ in por_periodo.get(p, []):
                assert all(r in aprobados_antes for r in cat["reqs"].get(curso, [])), "curso sin su prerrequisito"
            aprobados_antes |= {nrc_curso[m["nrc"]][0] for m in f["matriculas"]
                                if m["periodo_id"] == p and m["estado"] == "finalizada" and m["nota_final"] >= 3.0}
        assert 1 <= f["estudiante"]["semestre_actual"] <= 8
        assert all(m["estado"] == "inscrita" for m in f["matriculas"] if m["periodo_id"] == "2026-2")
