package co.edu.unab.cbdatos.data

import kotlinx.coroutines.flow.Flow
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Petición de una acción directa ("perfil" o "noticias") al mismo webhook del chat (no lleva "mensaje"). */
@Serializable
data class PerfilRequest(
    val accion: String,
    @SerialName("estudiante_codigo") val estudianteCodigo: String,
    @SerialName("session_id") val sessionId: String,
)

/** Curso inscrito en el periodo actual, con su NRC, horario y profesor. */
@Serializable
data class CursoHorario(
    val nrc: String = "",
    @SerialName("curso_codigo") val cursoCodigo: String = "",
    val curso: String = "",
    val creditos: Int = 0,
    val profesor: String = "",
    val horario: String = "",
)

/** Avance en el plan de estudios. */
@Serializable
data class AvanceAcademico(
    @SerialName("creditos_aprobados") val creditosAprobados: Int = 0,
    @SerialName("creditos_totales") val creditosTotales: Int = 0,
    @SerialName("porcentaje_avance") val porcentajeAvance: Double = 0.0,
    @SerialName("cursos_aprobados") val cursosAprobados: Int = 0,
    @SerialName("cursos_plan") val cursosPlan: Int = 0,
)

/** Resultado de la prueba en un pilar del requisito Competencias Digitales R2025. */
@Serializable
data class CompetenciaDigital(
    val competencia: String = "",
    val estado: String = "",
    @SerialName("cumplida_con") val cumplidaCon: String? = null,
) {
    val aprobada: Boolean get() = estado.trim().lowercase() == "aprobada"
}

/** Requisito de grado Competencias Digitales R2025 (pilares aprobados y faltantes). */
@Serializable
data class CompetenciasDigitales(
    val requisito: String = "Competencias Digitales R2025",
    @SerialName("fecha_prueba") val fechaPrueba: String? = null,
    val competencias: List<CompetenciaDigital> = emptyList(),
    val faltantes: List<String> = emptyList(),
    @SerialName("total_aprobadas") val totalAprobadas: Int = 0,
    @SerialName("total_pilares") val totalPilares: Int = 0,
    val cumplido: Boolean = false,
)

/** Horas libres acumuladas frente a las requeridas para el grado (96). */
@Serializable
data class HorasLibres(
    @SerialName("horas_cumplidas") val horasCumplidas: Int = 0,
    @SerialName("horas_requeridas") val horasRequeridas: Int = 96,
    @SerialName("horas_faltantes") val horasFaltantes: Int = 0,
    val completo: Boolean = false,
)

/** Perfil del estudiante. Solo [codigo] y [nombre] son obligatorios; lo demás toma valores por defecto. */
@Serializable
data class PerfilEstudiante(
    val codigo: String,
    val nombre: String,
    val nombres: String = "",
    val apellidos: String = "",
    val correo: String = "",
    val programa: String = "",
    @SerialName("semestre_actual") val semestreActual: Int? = null,
    val estado: String = "",
    @SerialName("periodo_actual") val periodoActual: String = "",
    val horario: List<CursoHorario> = emptyList(),
    @SerialName("creditos_inscritos") val creditosInscritos: Int = 0,
    val avance: AvanceAcademico? = null,
    @SerialName("competencias_digitales") val competenciasDigitales: CompetenciasDigitales? = null,
    @SerialName("horas_libres") val horasLibres: HorasLibres? = null,
    val nuevo: Boolean = false,
)

/** Envoltorio de la respuesta 200: {"perfil": {...}}. */
@Serializable
data class PerfilResponse(val perfil: PerfilEstudiante? = null)

/** Textos derivados del perfil para el encabezado, el saludo y la pantalla de perfil. */
object PerfilFormato {
    private const val LIMITE_NOMBRE = 24

    private fun partes(texto: String) = texto.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }

    /** Nombres de pila para el saludo ("Juan Sebastián"); sin el campo nombres, la primera palabra del nombre. */
    fun primerNombre(p: PerfilEstudiante): String =
        if (p.nombres.isNotBlank()) partes(p.nombres).take(2).joinToString(" ")
        else partes(p.nombre).firstOrNull().orEmpty()

    /** Nombre completo si es corto; si no, nombres + primer apellido (o las dos primeras palabras). */
    fun nombreEncabezado(p: PerfilEstudiante): String {
        val completo = p.nombre.trim()
        if (completo.length <= LIMITE_NOMBRE) return completo
        if (p.nombres.isNotBlank()) {
            val apellido = partes(p.apellidos).firstOrNull()
            return (partes(p.nombres) + listOfNotNull(apellido)).joinToString(" ")
        }
        return partes(completo).take(2).joinToString(" ")
    }

    /** Texto de bienvenida del chat vacío. */
    fun saludo(primerNombre: String): String =
        if (primerNombre.isBlank()) "¡Hola! Soy tu asistente académico" else "¡Hola, $primerNombre! Soy tu asistente académico"

    /** "Ingeniería de Sistemas, semestre 7"; si falta algo se omite; si no hay nada, el código. */
    fun subtitulo(p: PerfilEstudiante): String {
        val items = listOfNotNull(
            p.programa.trim().ifEmpty { null },
            p.semestreActual?.let { "semestre $it" },
        )
        return if (items.isEmpty()) p.codigo else items.joinToString(", ")
    }

    /** Iniciales para el avatar ("JL" para Juan Sebastián Lizcano). */
    fun iniciales(p: PerfilEstudiante): String {
        val nombre = partes(p.nombres.ifBlank { p.nombre }).firstOrNull()?.firstOrNull()
        val apellido = partes(p.apellidos).firstOrNull()?.firstOrNull() ?: partes(p.nombre).getOrNull(1)?.firstOrNull()
        return listOfNotNull(nombre, apellido).joinToString("").uppercase().ifEmpty { "U" }
    }

    /** Fracción 0..1 de horas libres (se llena al llegar a las requeridas, aunque tenga más). */
    fun fraccionHoras(h: HorasLibres): Float =
        if (h.horasRequeridas <= 0) 0f else (h.horasCumplidas.toFloat() / h.horasRequeridas).coerceIn(0f, 1f)

    /** Texto corto del estado de las horas libres. */
    fun textoHoras(h: HorasLibres): String =
        if (h.completo || h.horasCumplidas >= h.horasRequeridas) "Requisito cumplido: ya tienes las ${h.horasRequeridas} horas"
        else "Te faltan ${maxOf(0, h.horasRequeridas - h.horasCumplidas)} horas para graduarte"

    /** Horas adicionales con el plural correcto ("1 hora adicional", "8 horas adicionales"). */
    fun horasAdicionales(h: HorasLibres): String {
        val extra = maxOf(0, h.horasCumplidas - h.horasRequeridas)
        return if (extra == 1) "Llevas 1 hora adicional." else "Llevas $extra horas adicionales."
    }

    private val MESES = listOf("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
        "octubre", "noviembre", "diciembre")

    /** "2025-03-22" -> "22 de marzo de 2025"; si no tiene ese formato, se devuelve igual. */
    fun fechaLarga(iso: String): String {
        val m = Regex("""^(\d{4})-(\d{2})-(\d{2})""").find(iso.trim()) ?: return iso
        val (anio, mes, dia) = m.destructured
        val nombreMes = MESES.getOrNull(mes.toInt() - 1) ?: return iso
        return "${dia.toInt()} de $nombreMes de $anio"
    }

    /** Porcentaje entero para mostrar ("36%"), redondeado igual en el chat y en el perfil. */
    fun porcentajeTexto(a: AvanceAcademico): String = "${Math.round(porcentaje(a))}%"

    /** Porcentaje 0..100 del avance, calculado con los créditos si el servidor no lo envía. */
    fun porcentaje(a: AvanceAcademico): Double {
        val valor = when {
            a.porcentajeAvance > 0.0 -> a.porcentajeAvance
            a.creditosTotales > 0 -> a.creditosAprobados * 100.0 / a.creditosTotales
            else -> 0.0
        }
        return valor.coerceIn(0.0, 100.0)
    }
}

interface PerfilRepository {
    /** Pide el perfil del estudiante; lanza [ChatException] si algo falla. */
    suspend fun perfil(estudianteCodigo: String, sessionId: String): PerfilEstudiante
}

/** Sesión guardada: código y perfil en caché. */
interface AlmacenSesion {
    val codigoEstudiante: Flow<String?>
    val perfil: Flow<PerfilEstudiante?>
    suspend fun guardarSesion(codigo: String, perfil: PerfilEstudiante)
    suspend fun guardarPerfil(perfil: PerfilEstudiante)
    suspend fun cerrarSesion()
}
