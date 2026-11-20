"""Embedding de la pregunta con Gemini (REST embedContent, RETRIEVAL_QUERY, 768 dimensiones)."""
from __future__ import annotations

import math
import os
import time

import httpx


def embedding_consulta(texto: str) -> list[float]:
    clave = os.environ.get("GEMINI_API_KEY")
    if not clave:
        raise RuntimeError("GEMINI_API_KEY no está configurada: no se puede buscar en los documentos.")
    modelo = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    dim = int(os.environ.get("EMBED_DIM", "768"))
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:embedContent"
    cuerpo = {"model": f"models/{modelo}", "content": {"parts": [{"text": texto}]},
              "taskType": "RETRIEVAL_QUERY", "outputDimensionality": dim}
    for intento in range(4):
        r = httpx.post(url, json=cuerpo, headers={"x-goog-api-key": clave}, timeout=30)
        if r.status_code in (429, 500, 503) and intento < 3:
            time.sleep(2 ** intento)
            continue
        r.raise_for_status()
        vec = r.json()["embedding"]["values"]
        norma = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norma for x in vec]
    raise RuntimeError("Gemini no respondió")
