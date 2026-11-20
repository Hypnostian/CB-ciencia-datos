# Pertinencia pedagógica

## 1. El problema

Un estudiante de Ingeniería de Sistemas tiene que cruzar varias fuentes para saber dónde está y qué hacer: su historial en el portal,
el plan de estudios de 151 créditos, los prerrequisitos, el reglamento (prueba académica, cancelaciones, habilitaciones), los requisitos
de grado (competencias digitales, horas libres) y el calendario. Cuando no lo hace a tiempo aparecen el rezago, los cursos bloqueados
y los requisitos de grado pendientes al final de la carrera.

## 2. Enfoque

**Educación de precisión.** Hart (2016) propone llevar a la educación la idea de la medicina de precisión: ajustar la intervención a las
características de cada estudiante. Yang (2021) la define, en el contexto de la IA en educación, como identificar a tiempo a los
estudiantes en riesgo y actuar con base en sus datos de aprendizaje. El asistente aplica esta idea: cada respuesta se calcula con los
datos del propio estudiante y no con una regla general.

**Autoaprendizaje y autorregulación.** Zimmerman (2002) describe al estudiante autorregulado como el que planea, monitorea su avance y
ajusta sus estrategias. El asistente le da al estudiante las tres piezas para hacerlo solo y en el momento que quiera: dónde está
(estado académico), a dónde va (proyección) y qué hacer ahora (recomendaciones y requisitos).

**Alertas tempranas con analítica del aprendizaje.** Sistemas como Course Signals (Arnold y Pistilli, 2012) mostraron que avisar a tiempo
al estudiante sobre su riesgo, con acciones concretas, mejora el rendimiento. Las alertas de `requisitos_pendientes` (cursos
bloqueados, rezago, requisitos de grado) siguen esa línea.

**Respuestas ancladas a fuentes (RAG).** Lewis et al. (2020) muestran que recuperar documentos antes de generar reduce las respuestas
inventadas y permite citar la fuente. Para dudas de reglamento esto es clave: el estudiante recibe la regla oficial y el enlace para
verificarla. Zawacki-Richter et al. (2019) señalan que la IA en educación superior se ha usado sobre todo en perfiles del estudiante,
evaluación y sistemas adaptativos, y piden más reflexión pedagógica; por eso aquí cada respuesta busca una acción del estudiante y no
solo información.

## 3. Cómo se ve en las respuestas

| Necesidad | Lo que responde el asistente (ejemplo real) | Por qué es personalizado y accionable |
|---|---|---|
| Estado académico | "Tienes un avance del 56.3 %: 85 créditos de 151 y 32 cursos aprobados de 51" | Cifras del propio estudiante, no del plan en general |
| Proyección | "Te faltan 4 semestres, graduación estimada en 2028-2; tienes pendientes 51 créditos" | Calculada respetando prerrequisitos y la carga del estudiante |
| Recomendaciones | "Para 2027-1, una carga de 18 créditos: Ingeniería de software II, Ciencias de datos, ...; Ciencias de datos depende de que apruebes Base de datos II" | Dice qué inscribir y qué condición cumplir antes |
| Estudiante en riesgo | A José (rezagado, 22 créditos en semestre 8): "carga moderada de 14 créditos y prioriza los cursos pendientes de semestres anteriores; inscribe los pilares de competencias digitales que te faltan" | La carga y las prioridades cambian según el rendimiento |
| Requisitos de grado | "Aprobaste MS Word y MS PowerPoint; te faltan Vida en línea, MS Excel y Cultura digital: debes inscribir el curso de cada pilar" | Dice exactamente qué falta y qué hacer, con la fuente oficial |
| Horas libres | "Tienes 11 de 96 horas; te faltan 85" o "ya completaste las 96 horas necesarias para graduarte" | Número exacto y si el requisito está cumplido |
| Reglamento | "Quedas en prueba académica cuando por segunda vez consecutiva tu PGA está entre 3.00 y 3.20, o si por primera vez es menor que 3.00" (fuente: Reglamento Estudiantil) | Regla oficial citada, verificable |
| Noticias del día | Titulares de hoy de educación, tecnología e ingeniería de sistemas con fuente y fecha | Mantiene al estudiante al día con su campo profesional |

Las capturas de estas respuestas están en `docs/capturas/` (22 a 33) y en el README.

## 4. Cuidado del estudiante

- **Privacidad:** solo responde sobre el código del estudiante; los guardrails bloquean pedidos de datos de otros.
- **Honestidad:** si no hay información en los documentos lo dice y remite a un canal oficial; marca los prerrequisitos simulados y las
  fechas sin verificar.
- **Tono:** breve, amable y en español; saluda por el nombre.
- **Continuidad:** la memoria por sesión permite preguntas de seguimiento sin repetir el contexto.

## 5. Limitaciones

- Los datos académicos son sintéticos: en producción se conectaría a la base real (Banner) con los mismos contratos del servidor MCP.
- Los prerrequisitos son simulados porque la UNAB no los publica.
- No se midió el impacto con estudiantes reales; el siguiente paso sería una prueba piloto con encuesta de utilidad y seguimiento del
  rendimiento.

## Referencias

- Arnold, K. E., y Pistilli, M. D. (2012). Course signals at Purdue: Using learning analytics to increase student success. En
  *Proceedings of the 2nd International Conference on Learning Analytics and Knowledge (LAK '12)*. ACM.
  https://doi.org/10.1145/2330601.2330666
- Hart, S. A. (2016). Precision education initiative: Moving toward personalized education. *Mind, Brain, and Education, 10*(4),
  209-211. https://doi.org/10.1111/mbe.12109
- Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., et al. (2020). Retrieval-augmented generation for
  knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems, 33*. https://arxiv.org/abs/2005.11401
- Yang, S. J. H. (2021). Guest editorial: Precision education, a new challenge for AI in education. *Educational Technology & Society,
  24*(1), 105-108.
- Zawacki-Richter, O., Marín, V. I., Bond, M., y Gouverneur, F. (2019). Systematic review of research on artificial intelligence
  applications in higher education: Where are the educators? *International Journal of Educational Technology in Higher Education,
  16*, 39. https://doi.org/10.1186/s41239-019-0171-0
- Zimmerman, B. J. (2002). Becoming a self-regulated learner: An overview. *Theory Into Practice, 41*(2), 64-70.
  https://doi.org/10.1207/s15430421tip4102_2
- Universidad Autónoma de Bucaramanga. Reglamento Estudiantil de Pregrado y publicaciones del Centro de Competencias Digitales
  (URLs en `data/oficial/docs/`).
