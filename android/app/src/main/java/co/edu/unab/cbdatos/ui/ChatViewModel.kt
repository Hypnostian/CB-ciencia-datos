package co.edu.unab.cbdatos.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import co.edu.unab.cbdatos.data.ChatException
import co.edu.unab.cbdatos.data.ChatJson
import co.edu.unab.cbdatos.data.ChatRepository
import co.edu.unab.cbdatos.data.Fuente
import co.edu.unab.cbdatos.data.SessionStore
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString

@Serializable
enum class Autor { USUARIO, ASISTENTE }

@Serializable
data class MensajeChat(
    val id: Long,
    val autor: Autor,
    val texto: String,
    val intencion: String? = null,
    val fuentes: List<Fuente> = emptyList(),
)

data class ChatUiState(
    val mensajes: List<MensajeChat> = emptyList(),
    val escribiendo: Boolean = false,
    /** Mensaje de error visible; si hay uno, se ofrece reintentar. */
    val error: String? = null,
    /** Texto del último mensaje que falló, para reintentarlo sin duplicarlo. */
    val pendiente: String? = null,
)

class ChatViewModel(
    private val codigo: String,
    private val repositorio: ChatRepository,
    private val sesiones: SessionStore,
) : ViewModel() {

    private val _estado = MutableStateFlow(ChatUiState())
    val estado: StateFlow<ChatUiState> = _estado.asStateFlow()

    private var siguienteId = 0L
    private var trabajo: Job? = null

    /** Restauración del historial o cambio de sesión en curso; todo envío espera a que termine. */
    private var trabajoSesion: Job? = null
    private val candadoGuardado = Mutex()

    init {
        trabajoSesion = viewModelScope.launch { restaurar() }
    }

    /** Recupera la conversación visible guardada, para que la pantalla coincida con la memoria del asistente. */
    private suspend fun restaurar() {
        val guardados = try {
            sesiones.leerHistorial(codigo)?.let { ChatJson.decodeFromString<List<MensajeChat>>(it) }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            null
        } ?: return
        if (guardados.isEmpty()) return
        val recientes = guardados.takeLast(MAX_MENSAJES_GUARDADOS)
        // Ids negativos: no chocan con los mensajes nuevos si el usuario escribió antes de terminar de restaurar
        val restaurados = recientes.mapIndexed { i, m -> m.copy(id = (i - recientes.size).toLong()) }
        _estado.update { it.copy(mensajes = restaurados + it.mensajes) }
    }

    private suspend fun guardarHistorial() {
        candadoGuardado.withLock {
            val json = try {
                ChatJson.encodeToString(_estado.value.mensajes.takeLast(MAX_MENSAJES_GUARDADOS))
            } catch (e: Exception) {
                return
            }
            try {
                sesiones.guardarHistorial(codigo, json)
            } catch (e: CancellationException) {
                throw e
            } catch (_: Exception) {
                // El historial es una comodidad: si no se puede guardar, el chat sigue funcionando
            }
        }
    }

    fun enviar(texto: String) {
        val limpio = texto.trim()
        if (limpio.isEmpty() || _estado.value.escribiendo) return
        _estado.update {
            it.copy(mensajes = it.mensajes + MensajeChat(siguienteId++, Autor.USUARIO, limpio), error = null, pendiente = null)
        }
        viewModelScope.launch {
            trabajoSesion?.join()
            guardarHistorial()
        }
        pedirRespuesta(limpio)
    }

    /** Reenvía el último mensaje que falló. */
    fun reintentar() {
        val pendiente = _estado.value.pendiente ?: return
        if (_estado.value.escribiendo) return
        _estado.update { it.copy(error = null, pendiente = null) }
        pedirRespuesta(pendiente)
    }

    /** Descarta el historial en pantalla y estrena un session_id nuevo (el asistente olvida lo anterior). */
    fun nuevaConversacion() {
        trabajo?.cancel()
        trabajoSesion?.cancel()
        // La pantalla se limpia al instante; el cambio de sesión se espera antes de cualquier envío.
        _estado.value = ChatUiState()
        trabajoSesion = viewModelScope.launch {
            sesiones.nuevaSesion(codigo)
            guardarHistorial()
        }
    }

    private fun pedirRespuesta(texto: String) {
        _estado.update { it.copy(escribiendo = true) }
        trabajo = viewModelScope.launch {
            try {
                trabajoSesion?.join()
                val sessionId = sesiones.sessionId(codigo)
                val r = repositorio.enviar(codigo, sessionId, texto)
                _estado.update {
                    it.copy(
                        mensajes = it.mensajes + MensajeChat(siguienteId++, Autor.ASISTENTE, r.respuesta.trim(), r.intencion, r.fuentes),
                        escribiendo = false,
                    )
                }
                guardarHistorial()
            } catch (e: CancellationException) {
                throw e
            } catch (e: ChatException) {
                _estado.update { it.copy(escribiendo = false, error = e.message, pendiente = texto) }
            } catch (e: Exception) {
                _estado.update { it.copy(escribiendo = false, error = "Ocurrió un error inesperado. Intenta de nuevo.", pendiente = texto) }
            }
        }
    }

    private companion object {
        const val MAX_MENSAJES_GUARDADOS = 40
    }
}
