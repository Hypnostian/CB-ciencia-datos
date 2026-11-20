"""Plan de estudios de Ingeniería de Sistemas (UNAB) y sus prerrequisitos simulados.

Fuente oficial del plan: documento "Plan de estudios" que publica la página del programa
(https://unab.edu.co/programas/ingenieria-de-sistemas/): 151 créditos, 8 semestres más la práctica
(9 bloques en total). Se lee de data/oficial/unab_planes_estudio.json (el mismo dato que usa el RAG);
si no está, se usa la copia de PLAN_RESPALDO, transcrita del mismo documento.

Ajustes sobre el texto del documento, solo para que cada curso sea una fila única en la base:
  - Las electivas repetidas se numeran: "Electiva de profundización I" a "IV", "Electiva sociohumanística I"
    y "II", "Electiva de contexto I" y "II" (el documento las lista con el mismo nombre en varios semestres).
  - "Infrastructure tecnológica" (así aparece en el documento) se escribe "Infraestructura tecnológica".

UNAB no publica prerrequisitos: los de PRERREQ_SIMULADOS son inventados (plausibles)
y se cargan siempre con es_simulado = true.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
RUTA_JSON_OFICIAL = RAIZ / "data" / "oficial" / "unab_planes_estudio.json"
SLUG_OFICIAL = "ingenieria-de-sistemas"
PLAN_FUENTE_URL = "https://unab.edu.co/programas/ingenieria-de-sistemas/"
PLAN_DOCUMENTO_URL = "https://drive.google.com/file/d/1yQjou2XygQM2jO8OznywP2s3ZWhnxJDW/view"
PROGRAMA_CODIGO = "ISIS"
PROGRAMA_NOMBRE = "Ingeniería de Sistemas"
TOTAL_CREDITOS = 151
SEMESTRES_PLAN = 9  # 8 semestres más el de la práctica en ingeniería de sistemas

# (semestre, nombre, créditos). Copia del documento oficial del plan (página del programa).
PLAN_RESPALDO: list[tuple[int, str, int]] = [
    (1, "Álgebra lineal", 3),
    (1, "Cálculo diferencial", 4),
    (1, "Expresión", 4),
    (1, "Fundamentos de programación", 3),
    (1, "Seminario de ingeniería I", 2),
    (2, "Cálculo integral", 4),
    (2, "Diseño de interfaces de usuario", 3),
    (2, "Identidad", 3),
    (2, "Laboratorio de mecánica", 0),
    (2, "Mecánica y laboratorio", 3),
    (2, "Programación de computadores", 3),
    (2, "Taller de deportes, recreación y cultura", 1),
    (2, "Taller de desarrollo humano", 1),
    (3, "Cálculo en varias variables", 3),
    (3, "Creatividad", 3),
    (3, "Electromagnetismo y laboratorio", 3),
    (3, "Estructura de datos y análisis de algoritmos", 3),
    (3, "Laboratorio de electromagnetismo", 0),
    (3, "Matemáticas computacionales", 3),
    (3, "Seminario de ingeniería II", 2),
    (4, "Base de datos I", 3),
    (4, "Desarrollo multimedia", 3),
    (4, "Ecuaciones diferenciales", 3),
    (4, "Estadística general", 3),
    (4, "Inteligencia artificial", 3),
    (4, "Tecnologías móviles", 3),
    (5, "Actividades libres de recreación, deporte y cultura y de desarrollo humano", 2),
    (5, "Arquitectura de software", 3),
    (5, "Base de datos II", 3),
    (5, "Electiva de profundización", 3),
    (5, "Infrastructure tecnológica", 3),
    (5, "Ingeniería de software I", 3),
    (6, "Ciencias de datos", 3),
    (6, "Electiva de profundización", 3),
    (6, "Ética de la ingeniería de sistemas", 2),
    (6, "Ingeniería de software II", 3),
    (6, "Internet de las cosas", 3),
    (6, "Teoría de sistemas y organizaciones", 3),
    (7, "Ciberseguridad", 3),
    (7, "Electiva sociohumanística", 3),
    (7, "Electiva de contexto", 3),
    (7, "Electiva de profundización", 3),
    (7, "Investigación de operaciones I", 3),
    (7, "Proyectos en ingeniería de sistemas I", 2),
    (8, "Dinámica de sistemas", 3),
    (8, "Electiva sociohumanística", 3),
    (8, "Electiva de profundización", 3),
    (8, "Investigación de operaciones II", 3),
    (8, "Proyectos en ingeniería de sistemas II", 4),
    (9, "Electiva de contexto", 3),
    (9, "Práctica en ingeniería de sistemas", 12),
]

# Correcciones de escritura del documento (clave sin tildes en minúscula -> nombre usado en la base).
CORRECCIONES = {"infrastructure tecnologica": "Infraestructura tecnológica"}

# Prerrequisitos SIMULADOS (curso -> requisitos), por nombre. Cadenas dentro de la misma área entre semestres,
# como Cálculo diferencial -> Cálculo integral o Base de datos I -> Base de datos II.
PRERREQ_SIMULADOS: dict[str, list[str]] = {
    "Cálculo integral": ["Cálculo diferencial"],
    "Diseño de interfaces de usuario": ["Fundamentos de programación"],
    "Mecánica y laboratorio": ["Cálculo diferencial"],
    "Programación de computadores": ["Fundamentos de programación"],
    "Cálculo en varias variables": ["Cálculo integral"],
    "Electromagnetismo y laboratorio": ["Mecánica y laboratorio", "Cálculo integral"],
    "Laboratorio de electromagnetismo": ["Laboratorio de mecánica"],
    "Estructura de datos y análisis de algoritmos": ["Programación de computadores"],
    "Matemáticas computacionales": ["Álgebra lineal"],
    "Seminario de ingeniería II": ["Seminario de ingeniería I"],
    "Base de datos I": ["Estructura de datos y análisis de algoritmos"],
    "Desarrollo multimedia": ["Diseño de interfaces de usuario"],
    "Ecuaciones diferenciales": ["Cálculo en varias variables"],
    "Estadística general": ["Cálculo integral"],
    "Inteligencia artificial": ["Estructura de datos y análisis de algoritmos", "Matemáticas computacionales"],
    "Tecnologías móviles": ["Programación de computadores", "Diseño de interfaces de usuario"],
    "Actividades libres de recreación, deporte y cultura y de desarrollo humano":
        ["Taller de deportes, recreación y cultura", "Taller de desarrollo humano"],
    "Arquitectura de software": ["Estructura de datos y análisis de algoritmos"],
    "Base de datos II": ["Base de datos I"],
    "Infraestructura tecnológica": ["Programación de computadores"],
    "Ingeniería de software I": ["Base de datos I"],
    "Ciencias de datos": ["Estadística general", "Base de datos II"],
    "Electiva de profundización II": ["Electiva de profundización I"],
    "Ética de la ingeniería de sistemas": ["Seminario de ingeniería II"],
    "Ingeniería de software II": ["Ingeniería de software I"],
    "Internet de las cosas": ["Infraestructura tecnológica"],
    "Ciberseguridad": ["Infraestructura tecnológica"],
    "Electiva de profundización III": ["Electiva de profundización II"],
    "Investigación de operaciones I": ["Estadística general", "Álgebra lineal"],
    "Proyectos en ingeniería de sistemas I": ["Ingeniería de software II"],
    "Dinámica de sistemas": ["Teoría de sistemas y organizaciones", "Ecuaciones diferenciales"],
    "Electiva de profundización IV": ["Electiva de profundización III"],
    "Investigación de operaciones II": ["Investigación de operaciones I"],
    "Proyectos en ingeniería de sistemas II": ["Proyectos en ingeniería de sistemas I"],
    "Práctica en ingeniería de sistemas": ["Proyectos en ingeniería de sistemas II", "Ingeniería de software II"],
}

ROMANOS = ["I", "II", "III", "IV", "V", "VI"]


def sin_tildes(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def clave(t: str) -> str:
    return re.sub(r"\s+", " ", sin_tildes(t).lower()).strip()


def _tipo(nombre: str) -> str:
    return "electivo" if clave(nombre).startswith("electiva") else "obligatorio"


def _desde_json_oficial() -> list[tuple[int, str, int]] | None:
    """Plan de Ingeniería de Sistemas (presencial) del JSON oficial. None si no está o no suma 151 créditos."""
    if not RUTA_JSON_OFICIAL.exists():
        return None
    try:
        datos = json.loads(RUTA_JSON_OFICIAL.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    programa = next((p for p in datos.get("programas", []) if p.get("slug") == SLUG_OFICIAL), None)
    if not programa or not programa.get("semestres"):
        return None
    cursos = [(int(s["numero"]), c["nombre"].strip(), int(c["creditos"]))
              for s in programa["semestres"] for c in s.get("cursos", [])]
    if sum(c[2] for c in cursos) != TOTAL_CREDITOS:
        return None
    return cursos


def _normalizar(cursos: list[tuple[int, str, int]]) -> list[tuple[int, str, int, str]]:
    """Corrige la escritura y numera las electivas que se repiten con el mismo nombre (I, II, ...)."""
    total_por_nombre: dict[str, int] = {}
    for _, n, _ in cursos:
        total_por_nombre[clave(n)] = total_por_nombre.get(clave(n), 0) + 1
    vistos: dict[str, int] = {}
    salida = []
    for sem, nombre, cred in sorted(cursos, key=lambda x: x[0]):
        nombre = CORRECCIONES.get(clave(nombre), nombre)
        k = clave(nombre)
        if total_por_nombre.get(k, 1) > 1:
            vistos[k] = vistos.get(k, 0) + 1
            nombre = f"{nombre} {ROMANOS[vistos[k] - 1]}"
        salida.append((sem, nombre, cred, _tipo(nombre)))
    return salida


def cargar_plan() -> tuple[list[tuple[int, str, int, str]], str]:
    """Devuelve (cursos, origen). Cursos: (semestre, nombre, créditos, tipo)."""
    oficial = _desde_json_oficial()
    if oficial:
        return _normalizar(oficial), "data/oficial/unab_planes_estudio.json (documento del plan, 151 créditos)"
    return _normalizar(PLAN_RESPALDO), "copia incluida en db/seed/planes.py (documento oficial del plan, 151 créditos)"


def prerrequisitos_para(cursos: list[tuple[int, str, int, str]]) -> list[tuple[str, str]]:
    """Pares (curso, requisito) por nombre, resueltos por clave sin tildes. Ignora los que no existan."""
    por_clave = {clave(n): n for _, n, _, _ in cursos}
    pares = []
    for curso, reqs in PRERREQ_SIMULADOS.items():
        if clave(curso) not in por_clave:
            continue
        for r in reqs:
            if clave(r) in por_clave:
                pares.append((por_clave[clave(curso)], por_clave[clave(r)]))
    return pares


def codigo_curso(semestre: int, indice: int) -> str:
    """Código del curso en el plan (simulado, formato propio del demo): ISIS + semestre + índice."""
    return f"ISIS{semestre}{indice:02d}"
