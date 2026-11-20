package co.edu.unab.cbdatos.data

import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.Call
import okhttp3.Callback
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response

/** Tipos de fallo que la interfaz sabe explicar al usuario. */
enum class TipoError { CONFIGURACION, SIN_CONEXION, TIEMPO_AGOTADO, TOKEN, NO_ENCONTRADO, SERVIDOR, RESPUESTA_INVALIDA, CODIGO_INVALIDO, OTRO }

class ChatException(val tipo: TipoError, message: String, cause: Throwable? = null) : Exception(message, cause)

/** Webhook y token que el usuario escribe en Ajustes. */
data class WebhookConfig(val url: String, val token: String)

interface ChatRepository {
    /** Envía el mensaje y devuelve la respuesta del asistente; lanza [ChatException] si algo falla. */
    suspend fun enviar(estudianteCodigo: String, sessionId: String, mensaje: String): ChatResponse
}

/** Errores comunes a todas las acciones del webhook según el código HTTP. */
private fun validarEstado(codigoHttp: Int) {
    when {
        codigoHttp == 401 || codigoHttp == 403 ->
            throw ChatException(TipoError.TOKEN, "El token del chat es incorrecto (error $codigoHttp). Revísalo en Ajustes.")
        codigoHttp == 404 ->
            throw ChatException(TipoError.NO_ENCONTRADO, "No se encontró el webhook (404). Verifica la URL y que el workflow esté activo.")
        codigoHttp in 500..599 ->
            throw ChatException(TipoError.SERVIDOR, "El servidor de n8n tuvo un problema (error $codigoHttp). Intenta de nuevo en un momento.")
    }
}

/** Traduce código HTTP y cuerpo a una respuesta o a un error legible. Separado para poder probarlo sin red. */
fun interpretarRespuesta(codigoHttp: Int, cuerpo: String): ChatResponse {
    validarEstado(codigoHttp)
    if (codigoHttp !in 200..299) {
        throw ChatException(TipoError.OTRO, "Respuesta inesperada del servidor (código $codigoHttp).")
    }
    val respuesta = try {
        ChatJson.decodeFromString<ChatResponse>(cuerpo)
    } catch (e: Exception) {
        throw ChatException(TipoError.RESPUESTA_INVALIDA, "El servidor devolvió una respuesta que no se pudo leer.", e)
    }
    if (respuesta.respuesta.isBlank()) {
        throw ChatException(TipoError.RESPUESTA_INVALIDA, "El servidor devolvió una respuesta vacía.")
    }
    return respuesta
}

/** Igual que [interpretarRespuesta] pero para la acción "perfil"; el 400 es un código inválido. */
fun interpretarPerfil(codigoHttp: Int, cuerpo: String): PerfilEstudiante {
    validarEstado(codigoHttp)
    if (codigoHttp == 400) {
        val detalle = try {
            val obj = ChatJson.parseToJsonElement(cuerpo).jsonObject
            (obj["error"] ?: obj["respuesta"])?.jsonPrimitive?.contentOrNull
        } catch (e: Exception) {
            null
        }
        throw ChatException(TipoError.CODIGO_INVALIDO, detalle?.takeIf { it.isNotBlank() } ?: "El servidor no aceptó el código de estudiante.")
    }
    if (codigoHttp !in 200..299) {
        throw ChatException(TipoError.OTRO, "Respuesta inesperada del servidor (código $codigoHttp).")
    }
    val perfil = try {
        ChatJson.decodeFromString<PerfilResponse>(cuerpo).perfil
    } catch (e: Exception) {
        throw ChatException(TipoError.RESPUESTA_INVALIDA, "El servidor devolvió un perfil que no se pudo leer.", e)
    }
    return perfil ?: throw ChatException(TipoError.RESPUESTA_INVALIDA, "El servidor no devolvió el perfil del estudiante.")
}

/** Implementación con OkHttp. La configuración se lee en cada envío para que los cambios en Ajustes apliquen al instante. */
class WebhookChatRepository(
    private val configProvider: suspend () -> WebhookConfig,
    private val client: OkHttpClient = clienteHttp(),
) : ChatRepository, PerfilRepository, NoticiasRepository {

    override suspend fun enviar(estudianteCodigo: String, sessionId: String, mensaje: String): ChatResponse {
        val (codigo, texto) = publicar(ChatJson.encodeToString(ChatRequest(estudianteCodigo, sessionId, mensaje)))
        return interpretarRespuesta(codigo, texto)
    }

    override suspend fun perfil(estudianteCodigo: String, sessionId: String): PerfilEstudiante {
        val cuerpo = ChatJson.encodeToString(PerfilRequest("perfil", estudianteCodigo.trim().uppercase(), sessionId))
        val (codigo, texto) = publicar(cuerpo)
        return interpretarPerfil(codigo, texto)
    }

    override suspend fun noticias(estudianteCodigo: String, sessionId: String): NoticiasDelDia {
        val cuerpo = ChatJson.encodeToString(PerfilRequest("noticias", estudianteCodigo.trim().uppercase(), sessionId))
        val (codigo, texto) = publicar(cuerpo)
        return interpretarNoticias(codigo, texto)
    }

    /** POST al webhook con el token; traduce los fallos de red a [ChatException]. */
    private suspend fun publicar(json: String): Pair<Int, String> {
        val config = configProvider()
        if (config.url.isBlank()) {
            throw ChatException(TipoError.CONFIGURACION, "Falta la URL del webhook. Escríbela en Ajustes.")
        }
        val url = config.url.trim().toHttpUrlOrNull()
            ?: throw ChatException(TipoError.CONFIGURACION, "La URL del webhook no es válida. Debe empezar por https://")
        val cuerpo = json.toRequestBody("application/json; charset=utf-8".toMediaType())
        val peticion = Request.Builder()
            .url(url)
            .header("X-Chat-Token", config.token.trim())
            .post(cuerpo)
            .build()

        return try {
            ejecutar(client.newCall(peticion))
        } catch (e: UnknownHostException) {
            throw ChatException(TipoError.SIN_CONEXION, "No hay conexión con el servidor. Revisa tu internet y la URL del webhook.", e)
        } catch (e: ConnectException) {
            throw ChatException(TipoError.SIN_CONEXION, "No se pudo conectar con el servidor. Revisa tu internet y la URL del webhook.", e)
        } catch (e: SocketTimeoutException) {
            throw ChatException(TipoError.TIEMPO_AGOTADO, "El servidor tardó demasiado en responder. Intenta de nuevo.", e)
        } catch (e: IOException) {
            throw ChatException(TipoError.SIN_CONEXION, "Falló la comunicación con el servidor. Revisa tu conexión.", e)
        }
    }

    private suspend fun ejecutar(call: Call): Pair<Int, String> = suspendCancellableCoroutine { cont ->
        cont.invokeOnCancellation { call.cancel() }
        call.enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                if (cont.isActive) cont.resumeWithException(e)
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    try {
                        val texto = it.body?.string().orEmpty()
                        if (cont.isActive) cont.resume(it.code to texto)
                    } catch (e: IOException) {
                        if (cont.isActive) cont.resumeWithException(e)
                    }
                }
            }
        })
    }

    companion object {
        /** Tiempos pedidos: conexión 15 s, lectura 60 s (el LLM puede tardar). */
        fun clienteHttp(): OkHttpClient = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()
    }
}
