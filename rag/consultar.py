"""Demostración de la recuperación del RAG: hace lo mismo que el subflujo 01 de n8n con una o varias preguntas.

1. Calcula el embedding de la pregunta con Gemini (gemini-embedding-001, 768 dimensiones, taskType RETRIEVAL_QUERY).
2. Llama a la función match_documentos de Supabase (similitud coseno sobre pgvector).
3. Muestra los k fragmentos más parecidos con su similitud, el documento y la URL de la fuente, y marca los que
   superan el umbral de 0.35 que usa n8n para armar el contexto del agente.

Uso (desde la raíz del proyecto; lee GEMINI_API_KEY y DATABASE_URL del .env sin imprimirlos):
    python rag/consultar.py "¿Cuándo un estudiante queda en prueba académica?" "¿Cuántos créditos tiene el plan?"
    python rag/consultar.py -k 3 "¿Puedo homologar los cursos de competencias digitales?"
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import textwrap
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingesta  # noqa: E402

UMBRAL = 0.35  # mismo umbral del nodo "Armar prompt" del subflujo 01


def embedding_consulta(texto: str) -> list[float]:
    modelo = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    dim = int(os.environ.get("EMBED_DIM", "768"))
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:embedContent"
    cuerpo = json.dumps({"model": f"models/{modelo}", "content": {"parts": [{"text": texto}]},
                         "taskType": "RETRIEVAL_QUERY", "outputDimensionality": dim}).encode()
    req = urllib.request.Request(url, data=cuerpo, method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=60) as r:
        vec = json.load(r)["embedding"]["values"]
    norma = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norma for x in vec]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("preguntas", nargs="+")
    ap.add_argument("-k", type=int, default=5, help="fragmentos a recuperar (n8n usa 5)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    ingesta.cargar_env()
    import psycopg

    with psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None) as conn:
        total = conn.execute("select count(*) from documentos_fragmentos").fetchone()[0]
        print(f"Índice: {total} fragmentos con embedding (pgvector, 768 dimensiones)\n")
        for p in args.preguntas:
            vec = embedding_consulta(p)
            filas = conn.execute(
                "select titulo, fuente_url, contenido, similitud from match_documentos(%s::vector, %s)",
                ("[" + ",".join(f"{x:.7f}" for x in vec) + "]", args.k)).fetchall()
            print(f"Pregunta: {p}")
            for i, (titulo, url, contenido, sim) in enumerate(filas, 1):
                marca = "usa" if sim >= UMBRAL else "descarta"
                texto = " ".join(contenido.split())
                print(f"  {i}. similitud {sim:.3f} ({marca})  {titulo}")
                print(f"     fuente: {url}")
                print(textwrap.indent(textwrap.fill(texto[:230] + ("..." if len(texto) > 230 else ""), 100), "     "))
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
