"""Plan pequeño en memoria para probar la lógica y las herramientas sin base de datos."""
from app.servicio import CODIGO_RE  # noqa: F401


def curso(i, codigo, nombre, cred, sem, estado="pendiente", intentos=0):
    return dict(id=i, codigo=codigo, nombre=nombre, creditos=cred, semestre_plan=sem, tipo="obligatorio",
                estado=estado, intentos_reprobados=intentos, mejor_nota=None)


def plan(estados):
    """Cadena A -> B -> C (sem 1, 2, 3) más D (sem 1) y E (sem 2, requiere D). estados: {codigo: estado}."""
    base = [(1, "A", "Cálculo diferencial", 4, 1), (2, "B", "Cálculo integral", 3, 2), (3, "C", "Cálculo en varias variables", 3, 3),
            (4, "D", "Programación", 3, 1), (5, "E", "Estructura de datos", 3, 2), (6, "F", "Práctica", 12, 4)]
    return [curso(i, c, n, cr, s, estados.get(c, "pendiente"), 1 if estados.get(c) == "reprobado" else 0) for i, c, n, cr, s in base]


REQS = {2: [dict(requisito_id=1, es_simulado=True)], 3: [dict(requisito_id=2, es_simulado=True)],
        5: [dict(requisito_id=4, es_simulado=True)],
        6: [dict(requisito_id=3, es_simulado=True), dict(requisito_id=5, es_simulado=True)]}

CCD = [dict(id=1, ruta=1, nombre="Interacción Digital", obligatorio=True),
       dict(id=2, ruta=2, nombre="Marca Personal Digital", obligatorio=False),
       dict(id=3, ruta=3, nombre="IA Generativa", obligatorio=False)]


PILARES = ["Vida en línea", "MS Word", "MS Excel", "MS PowerPoint", "Cultura digital"]


def resultados(aprobadas):
    """Resultado de la prueba por pilar: aprobadas es la lista de pilares aprobados."""
    return [dict(orden=i + 1, competencia=p, aprobada=p in aprobadas, materia=f"Examen {p}" if p in aprobadas else None,
                 fecha_prueba="2026-03-21") for i, p in enumerate(PILARES)]


class RepoFalso:
    def __init__(self, estados=None, semestre=2, hist_ccd=None, aprobadas=("Vida en línea", "MS Word"), horas=40):
        self.estados = estados or {}
        self.semestre = semestre
        self.hist = hist_ccd or []
        self.aprobadas = list(aprobadas)
        self.horas = horas

    def estudiante(self, codigo):
        if codigo != "U00123456":
            return None
        return dict(codigo=codigo, nombres="Ana", apellidos="Prueba", correo="x@demo.unab.local", semestre_actual=self.semestre,
                    estado="activo", fecha_ingreso="2025-01-26", programa_id=1, programa="Ingeniería de Sistemas", total_creditos=28)

    def periodo_actual(self):
        return dict(id="2026-2", nombre="p", fecha_inicio="2026-08-03", fecha_fin="2026-12-05")

    def matricula_actual(self, codigo):
        return [dict(nrc="12345", curso_codigo="B", curso="Cálculo integral", creditos=3, profesor="Docente Sintético", horario="Lun 7-9")]

    def cursos_estudiante(self, codigo):
        return plan(self.estados)

    def prerrequisitos(self, programa_id):
        return REQS

    def catalogo_ccd(self):
        return CCD

    def historial_ccd(self, codigo):
        return self.hist

    def competencias(self, codigo):
        return resultados(self.aprobadas)

    def horas_libres(self, codigo):
        return None if self.horas is None else dict(horas_cumplidas=self.horas, horas_requeridas=96, actualizado="2026-11-17")

    def calendario(self, desde, categoria):
        return [dict(evento="Cursos vacacionales CCD: inscripción", categoria="ccd", fecha_inicio="2026-11-20", fecha_fin="2026-11-26",
                     verificado=True, fuente_url="x")]

    def noticias(self, limite, categoria):
        filas = [dict(titulo="Hoy", url="u1", fecha="2026-11-18T09:00:00-05:00", categoria="Tecnología", resumen="",
                      fuente="El Tiempo", es_hoy=True),
                 dict(titulo="Antes", url="u2", fecha="2026-11-10T09:00:00-05:00", categoria="Educación", resumen="",
                      fuente="UNAB", es_hoy=False)]
        return [f for f in filas if not categoria or categoria.lower() in f["categoria"].lower()][:limite]

    def buscar_profesor(self, texto, limite=10):
        return [dict(nombre="Profe Real", unidad="Ingeniería", cargo="Docente", apolo_url="https://apolo", cvlac_url=None)]

    def buscar_curso(self, texto, limite=5):
        return [dict(id=2, codigo="B", nombre="Cálculo integral", creditos=3, semestre_plan=2, tipo="obligatorio", es_oficial=True,
                     prerrequisitos=[dict(codigo="A", nombre="Cálculo diferencial", creditos=4, es_simulado=True)], es_requisito_de=[])]

    def match_documentos(self, embedding, k):
        self.ultimo_vector = embedding
        return [dict(id=1, documento_id=1, titulo="Reglamento", fuente_url="https://x", contenido="texto", similitud=0.9)][:k]
