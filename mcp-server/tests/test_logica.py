from app import logica
from tests.datos_falsos import CCD, REQS, plan

APROB = {"A": "aprobado", "D": "aprobado"}


def test_siguiente_periodo():
    assert logica.siguiente_periodo("2026-2") == "2027-1"
    assert logica.siguiente_periodo("2026-1") == "2026-2"


def test_avance_porcentaje():
    r = logica.resumen_avance(plan(APROB), 28)
    assert r["creditos_aprobados"] == 7
    assert r["porcentaje_avance"] == 25.0
    assert r["por_semestre"][0]["semestre"] == 1


def test_semestre_real():
    assert logica.semestre_real(plan({})) == 1
    assert logica.semestre_real(plan({"A": "aprobado", "D": "aprobado"})) == 2  # 7 créditos = semestre 1 completo


def test_proyeccion_respeta_prerrequisitos():
    p = logica.proyectar(plan(APROB), REQS, "2026-2", 18)
    pos = {c["codigo"]: s["semestre_futuro"] for s in p["plan"] for c in s["cursos"]}
    assert pos["B"] < pos["C"] < pos["F"]
    assert pos["E"] < pos["F"]
    assert p["graduacion_estimada"] is not None
    assert p["cursos_sin_ubicar"] == []


def test_proyeccion_respeta_tope_de_creditos():
    p = logica.proyectar(plan({}), REQS, "2026-2", 6)
    for s in p["plan"]:
        # solo un curso puede exceder el tope y únicamente si va solo (Práctica, 12 créditos)
        assert s["creditos"] <= 6 or len(s["cursos"]) == 1


def test_proyeccion_prioriza_reprobados_y_marca_motivo():
    est = {"A": "reprobado", "D": "aprobado"}
    p = logica.proyectar(plan(est), REQS, "2026-2", 3)
    primero = p["plan"][0]["cursos"][0]
    assert primero["codigo"] == "A" and "reprobado" in primero["motivo"]


def test_en_curso_cuenta_como_aprobado_en_la_proyeccion():
    p = logica.proyectar(plan({"A": "en_curso", "D": "aprobado"}), REQS, "2026-2", 18)
    codigos = [c["codigo"] for s in p["plan"] for c in s["cursos"]]
    assert "A" not in codigos and "B" in codigos


def test_alertas_bloqueo_ccd_y_rezago():
    cursos = plan({"A": "reprobado", "D": "aprobado"})
    al = logica.alertas(cursos, REQS, semestre_actual=3, ccd_ruta1="pendiente")
    tipos = {a["tipo"] for a in al}
    assert {"prerrequisito_bloqueado", "ccd_obligatorio", "rezago"} <= tipos
    bloqueo = next(a for a in al if a["tipo"] == "prerrequisito_bloqueado" and a["curso_codigo"] == "B")
    assert bloqueo["severidad"] == "alta" and bloqueo["prerrequisito_simulado"]
    assert al[0]["severidad"] == "alta"  # ordenadas por severidad


def test_sin_alertas_si_va_al_dia():
    cursos = plan({"A": "aprobado", "D": "aprobado"})
    al = logica.alertas(cursos, REQS, semestre_actual=2, ccd_ruta1="aprobado")
    assert [a for a in al if a["tipo"] in ("ccd_obligatorio", "rezago")] == []


def test_estado_competencias_y_horas():
    from tests.datos_falsos import resultados
    c = logica.estado_competencias(resultados(["Vida en línea"]))
    assert c["faltantes"] == ["MS Word", "MS Excel", "MS PowerPoint", "Cultura digital"]
    assert c["competencias"][1] == {"competencia": "MS Word", "estado": "no aprobada", "cumplida_con": None}
    assert logica.estado_competencias([])["prueba_presentada"] is False
    assert logica.estado_horas_libres(0)["horas_faltantes"] == 96
    assert logica.estado_horas_libres(96)["completo"] is True
    assert logica.estado_horas_libres(130)["porcentaje"] == 100.0
    al = logica.alertas_requisitos(c, logica.estado_horas_libres(10), semestre_actual=7)
    assert [a["severidad"] for a in al] == ["alta", "media"]


def test_ccd_insignia():
    hist = [dict(curso_ccd_id=1, estado="aprobado"), dict(curso_ccd_id=2, estado="aprobado")]
    r = logica.estado_ccd(CCD, hist)
    assert r["rutas_cumplidas"] == [1, 2] and not r["insignia_completa"]
    assert r["rutas_faltantes"][0]["ruta"] == 3
    r = logica.estado_ccd(CCD, hist + [dict(curso_ccd_id=3, estado="aprobado")])
    assert r["insignia_completa"]


def test_recomendaciones_carga_segun_rezago():
    ccd = logica.estado_ccd(CCD, [])
    rec = logica.recomendar(plan({"A": "reprobado"}), REQS, 4, "2026-2", ccd, [])
    assert rec["carga_sugerida_creditos"] <= 16
    assert any(r["tipo"] == "repetir" for r in rec["recomendaciones"])
    assert any(r["tipo"] == "ccd" for r in rec["recomendaciones"])
