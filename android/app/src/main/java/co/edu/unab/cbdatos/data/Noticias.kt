package co.edu.unab.cbdatos.data

import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeParseException
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Noticia del scraper (educación, tecnología, ingeniería de sistemas o vida UNAB) con su fuente y su fecha. */
@Serializable
data class Noticia(
    val titulo: String = "",
    val url: String = "",
    val fecha: String? = null,
    val categoria: String = "",
    val resumen: String = "",
    val fuente: String = "",
    @SerialName("es_hoy") val esHoy: Boolean = false,
)

/** Respuesta de la acción "noticias": las de hoy primero y, si faltan, las más recientes. */
@Serializable
data class NoticiasDelDia(
    @SerialName("fecha_consulta") val fechaConsulta: String = "",
    val total: Int = 0,
    @SerialName("de_hoy") val deHoy: Int = 0,
    val categorias: List<String> = emptyList(),
    val noticias: List<Noticia> = emptyList(),
)

/** Envoltorio de la respuesta 200: {"noticias": {...}}. */
@Serializable
data class NoticiasResponse(val noticias: NoticiasDelDia? = null)

interface NoticiasRepository {
    /** Pide las noticias del día al webhook (acción "noticias"); lanza [ChatException] si algo falla. */
    suspend fun noticias(estudianteCodigo: String, sessionId: String): NoticiasDelDia
}

/** Igual que [interpretarRespuesta] pero para la acción "noticias". */
fun interpretarNoticias(codigoHttp: Int, cuerpo: String): NoticiasDelDia {
    if (codigoHttp == 401 || codigoHttp == 403) {
        throw ChatException(TipoError.TOKEN, "El token del chat es incorrecto (error $codigoHttp). Revísalo en Ajustes.")
    }
    if (codigoHttp == 404) {
        throw ChatException(TipoError.NO_ENCONTRADO, "No se encontró el webhook (404). Verifica la URL y que el workflow esté activo.")
    }
    if (codigoHttp !in 200..299) {
        throw ChatException(TipoError.SERVIDOR, "No se pudieron cargar las noticias (error $codigoHttp). Intenta de nuevo en un momento.")
    }
    val datos = try {
        ChatJson.decodeFromString<NoticiasResponse>(cuerpo).noticias
    } catch (e: Exception) {
        throw ChatException(TipoError.RESPUESTA_INVALIDA, "El servidor devolvió noticias que no se pudieron leer.", e)
    }
    return datos ?: throw ChatException(TipoError.RESPUESTA_INVALIDA, "El servidor no devolvió noticias.")
}

/** Textos de fecha y fuente de las noticias, en hora de Colombia. */
object NoticiaFormato {
    val ZONA: ZoneId = ZoneId.of("America/Bogota")
    private val MESES = listOf("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")

    private fun instante(fecha: String?): OffsetDateTime? = try {
        fecha?.let { OffsetDateTime.parse(it.trim()).atZoneSameInstant(ZONA).toOffsetDateTime() }
    } catch (e: DateTimeParseException) {
        null
    }

    /** "Hoy, 11:43", "Ayer, 22:26" o "10 nov 2026". */
    fun fecha(fecha: String?, hoy: LocalDate = LocalDate.now(ZONA)): String {
        val d = instante(fecha) ?: return fecha?.take(10).orEmpty()
        val dia = d.toLocalDate()
        val hora = "%02d:%02d".format(d.hour, d.minute)
        return when (dia) {
            hoy -> "Hoy, $hora"
            hoy.minusDays(1) -> "Ayer, $hora"
            else -> "${dia.dayOfMonth} ${MESES[dia.monthValue - 1]} ${dia.year}"
        }
    }

    /** "18 de noviembre de 2026" a partir de la fecha de la consulta. */
    fun encabezado(fechaConsulta: String): String = PerfilFormato.fechaLarga(fechaConsulta)

    /** Medio que publicó la noticia, sin el "(vía Google Noticias)". */
    fun medio(fuente: String): String = fuente.replace(Regex("""\s*\(v[ií]a [^)]*\)$"""), "").trim()

    /** Agregador por el que llegó la noticia, si aplica ("Google Noticias"). */
    fun via(fuente: String): String? = Regex("""\(v[ií]a ([^)]*)\)$""").find(fuente)?.groupValues?.get(1)

    /** Filtra por categoría; "Todas" (o vacío) devuelve la lista completa. */
    fun filtrar(noticias: List<Noticia>, categoria: String?): List<Noticia> =
        if (categoria.isNullOrBlank() || categoria == TODAS) noticias else noticias.filter { it.categoria == categoria }

    const val TODAS = "Todas"
}
