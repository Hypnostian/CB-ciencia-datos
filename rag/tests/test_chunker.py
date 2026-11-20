import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingesta  # noqa: E402


def texto_largo(n=120):
    return "\n".join(["ARTÍCULO 5:"] + [f"Párrafo {i}: " + "el estudiante debe cumplir los requisitos del reglamento " * 4 for i in range(n)])


def test_fragmentos_no_exceden_tokens_y_conservan_encabezado():
    chunks = ingesta.fragmentar(texto_largo())
    assert len(chunks) > 2
    for c in chunks:
        assert c["tokens_aprox"] <= ingesta.MAX_TOKENS + 5
        assert c["contenido"].startswith("ARTÍCULO 5:")


def test_hay_solape_entre_fragmentos_consecutivos():
    chunks = ingesta.fragmentar(texto_largo())
    ultima = chunks[0]["contenido"].splitlines()[-1]
    assert ultima in chunks[1]["contenido"]


def test_plan_de_estudios_incluye_creditos():
    d = ingesta.doc_plan()
    assert "151" in d["texto"] and "Semestre 9" in d["texto"]
