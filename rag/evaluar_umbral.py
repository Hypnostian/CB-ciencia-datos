"""Evidencia del umbral de similitud 0.35 del RAG: compara la similitud top 1 de preguntas del dominio contra la de preguntas ajenas.

Para cada pregunta calcula el embedding (gemini-embedding-001, 768 dimensiones, taskType RETRIEVAL_QUERY), consulta el índice real con
match_documentos (la misma función que usan rag/consultar.py y el subflujo 01) y guarda la similitud del fragmento más cercano.
Escribe rag/evaluacion_umbral.json con las dos distribuciones (mínimo, promedio, máximo) y cuántas preguntas quedan sobre el umbral.

Uso (desde la raíz del proyecto; lee GEMINI_API_KEY y DATABASE_URL del .env sin imprimirlos):
    python rag/evaluar_umbral.py
Pausa 4 s entre embeddings para respetar el límite por minuto del plan gratuito y, si Gemini responde 429, espera 60 s y reintenta.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consultar  # noqa: E402
import ingesta  # noqa: E402

UMBRAL = consultar.UMBRAL
PAUSA_S = 4
ESPERA_429_S = 60
SALIDA = Path(__file__).resolve().parent / "evaluacion_umbral.json"

EN_DOMINIO = [
    "¿Cuántas veces puedo cancelar una asignatura?",
    "¿Cuándo un estudiante queda en prueba académica?",
    "¿Qué promedio necesito para estudiar dos carreras al tiempo?",
    "¿Cuánto equivale un crédito académico en horas de trabajo?",
    "¿Qué requisitos hay para homologar cursos de otra universidad?",
    "¿Cuáles son los cursos del primer semestre de Ingeniería de Sistemas?",
    "¿Cuántos créditos tiene el plan de Ingeniería de Sistemas?",
    "¿Cómo es el proceso de matrícula de pregrado?",
    "¿Cuándo son las inscripciones de los cursos vacacionales de competencias digitales?",
    "¿Qué es la insignia de competencias digitales del CCD?",
    "¿Qué pasa si pierdo el derecho a renovar la matrícula?",
    "¿Cuál es la calificación mínima para aprobar una prueba?",
    "¿Qué requisitos hay para obtener el título de pregrado?",
    "¿Cuándo se presenta la prueba de competencias digitales desde sexto semestre?",
    "¿Qué es el Programa de Recuperación Académica?",
]

FUERA_DE_DOMINIO = [
    "¿Quién ganó el último mundial de fútbol?",
    "Dame una receta de arepas con queso.",
    "¿Cuántos goles marcó Messi en su carrera?",
    "¿Cómo se hace un sancocho de gallina?",
    "¿Quién es la cantante más famosa del pop latino?",
    "¿Cuál es la edad de Shakira?",
    "¿Cómo invierto una lista en Python?",
    "¿Qué diferencia hay entre una lista y una tupla en Python?",
    "Escríbeme un poema sobre el mar.",
    "¿Cuál es la capital de Australia?",
    "¿Cómo se prepara una pizza napolitana?",
    "¿Quién ganó el Tour de Francia el año pasado?",
    "Cuéntame un chiste de programadores.",
    "¿Qué película ganó el Óscar a mejor película el año pasado?",
    "¿Cómo cambio la llanta de una bicicleta?",
]


def top1(conn, pregunta: str) -> tuple[float, str]:
    while True:
        try:
            vec = consultar.embedding_consulta(pregunta)
            break
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            print(f"  429, espera {ESPERA_429_S} s y reintenta", flush=True)
            time.sleep(ESPERA_429_S)
    fila = conn.execute(
        "select titulo, similitud from match_documentos(%s::vector, 1)",
        ("[" + ",".join(f"{x:.7f}" for x in vec) + "]",)).fetchone()
    return float(fila[1]), fila[0]


def resumen(valores: list[float]) -> dict:
    return {"preguntas": len(valores), "minimo": round(min(valores), 3), "promedio": round(sum(valores) / len(valores), 3),
            "maximo": round(max(valores), 3), f"sobre_{UMBRAL}": sum(1 for v in valores if v >= UMBRAL)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ingesta.cargar_env()
    import psycopg

    detalle = {"en_dominio": [], "fuera_de_dominio": []}
    with psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None) as conn:
        for grupo, preguntas in (("en_dominio", EN_DOMINIO), ("fuera_de_dominio", FUERA_DE_DOMINIO)):
            for p in preguntas:
                sim, titulo = top1(conn, p)
                detalle[grupo].append({"pregunta": p, "similitud_top1": round(sim, 3), "documento": titulo})
                print(f"{grupo:16s} {sim:.3f}  {p}", flush=True)
                time.sleep(PAUSA_S)
    res = {"umbral": UMBRAL, "modelo": "gemini-embedding-001", "dimensiones": 768, "tarea": "RETRIEVAL_QUERY"}
    for grupo in detalle:
        res[grupo] = {"resumen": resumen([d["similitud_top1"] for d in detalle[grupo]]), "detalle": detalle[grupo]}
    SALIDA.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({g: res[g]["resumen"] for g in detalle}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
