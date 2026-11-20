package co.edu.unab.cbdatos.data

import kotlinx.serialization.EncodeDefault
import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/** Cuerpo de la petición al webhook de n8n (ver docs/CONTRATO.md). */
@Serializable
data class ChatRequest(
    @SerialName("estudiante_codigo") val estudianteCodigo: String,
    @SerialName("session_id") val sessionId: String,
    val mensaje: String,
)

/** Fuente citada en una respuesta. */
@Serializable
data class Fuente(
    val titulo: String = "",
    val url: String = "",
)

/** Respuesta 200 del webhook. Los campos son tolerantes: lo que falte toma un valor por defecto. */
@OptIn(ExperimentalSerializationApi::class)
@Serializable
data class ChatResponse(
    val respuesta: String = "",
    @EncodeDefault val intencion: String = Intenciones.GENERAL,
    val fuentes: List<Fuente> = emptyList(),
)

object Intenciones {
    const val GENERAL = "general"
    const val CALENDARIO = "calendario"
    const val CURSOS = "cursos"
    const val MATRICULA = "matricula"
    const val NOTICIAS = "noticias"
    const val FUERA_DE_TEMA = "fuera_de_tema"

    /** Texto corto para la insignia de cada respuesta. */
    fun etiqueta(intencion: String): String = when (intencion.trim().lowercase()) {
        CALENDARIO -> "Calendario"
        CURSOS -> "Cursos"
        MATRICULA -> "Matrícula"
        NOTICIAS -> "Noticias"
        FUERA_DE_TEMA -> "Fuera de tema"
        else -> "General"
    }
}

/** Configuración JSON tolerante: ignora campos desconocidos y nulos en campos con valor por defecto. */
val ChatJson = Json {
    ignoreUnknownKeys = true
    coerceInputValues = true
    isLenient = true
}
