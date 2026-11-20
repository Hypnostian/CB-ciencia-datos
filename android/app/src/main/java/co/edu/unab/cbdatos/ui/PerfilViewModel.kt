package co.edu.unab.cbdatos.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import co.edu.unab.cbdatos.data.AlmacenSesion
import co.edu.unab.cbdatos.data.ChatException
import co.edu.unab.cbdatos.data.CodigoEstudiante
import co.edu.unab.cbdatos.data.PerfilEstudiante
import co.edu.unab.cbdatos.data.PerfilRepository
import co.edu.unab.cbdatos.data.SessionStore
import co.edu.unab.cbdatos.data.TipoError
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class PerfilUiState(
    /** Verdadero mientras se valida el código contra el servidor al pulsar "Ingresar". */
    val ingresando: Boolean = false,
    val errorIngreso: String? = null,
    /** Verdadero mientras "Actualizar" (o el refresco al abrir la app) consulta el perfil. */
    val actualizando: Boolean = false,
    val errorActualizar: String? = null,
)

/** Ingreso con perfil, perfil en caché y su actualización. */
class PerfilViewModel(
    private val almacen: AlmacenSesion,
    private val repositorio: PerfilRepository,
    private val sesiones: SessionStore,
) : ViewModel() {

    /** Perfil guardado (caché); null si no hay sesión o es una sesión antigua sin perfil. */
    val perfil: StateFlow<PerfilEstudiante?> = almacen.perfil.stateIn(viewModelScope, SharingStarted.Eagerly, null)

    private val _estado = MutableStateFlow(PerfilUiState())
    val estado: StateFlow<PerfilUiState> = _estado.asStateFlow()

    init {
        // Con una sesión guardada se muestra el perfil en caché y se refresca en segundo plano
        viewModelScope.launch {
            val codigo = almacen.codigoEstudiante.first()
            if (!codigo.isNullOrEmpty()) refrescar(codigo, silencioso = true)
        }
    }

    /** Valida el formato, consulta el perfil y, si todo sale bien, guarda código y perfil. */
    fun ingresar(entrada: String) {
        if (_estado.value.ingresando) return
        if (!CodigoEstudiante.esValido(entrada)) {
            _estado.update { it.copy(errorIngreso = "El código debe ser U00 seguido de 6 dígitos (por ejemplo U00123456).") }
            return
        }
        val codigo = CodigoEstudiante.normalizar(entrada)
        _estado.update { it.copy(ingresando = true, errorIngreso = null) }
        viewModelScope.launch {
            try {
                val p = repositorio.perfil(codigo, sesiones.sessionId(codigo))
                almacen.guardarSesion(codigo, p)
                _estado.update { it.copy(ingresando = false) }
            } catch (e: CancellationException) {
                throw e
            } catch (e: ChatException) {
                _estado.update { it.copy(ingresando = false, errorIngreso = mensajeIngreso(e)) }
            } catch (e: Exception) {
                _estado.update { it.copy(ingresando = false, errorIngreso = "Ocurrió un error inesperado. Intenta de nuevo.") }
            }
        }
    }

    fun limpiarErrorIngreso() {
        _estado.update { it.copy(errorIngreso = null) }
    }

    /** Acción "Actualizar" de la pantalla de perfil. */
    fun actualizar() {
        viewModelScope.launch {
            val codigo = almacen.codigoEstudiante.first()
            if (!codigo.isNullOrEmpty()) refrescar(codigo, silencioso = false)
        }
    }

    fun cerrarSesion() {
        viewModelScope.launch {
            almacen.cerrarSesion()
            _estado.value = PerfilUiState()
        }
    }

    private suspend fun refrescar(codigo: String, silencioso: Boolean) {
        if (_estado.value.actualizando) return
        _estado.update { it.copy(actualizando = true, errorActualizar = null) }
        try {
            val p = repositorio.perfil(codigo, sesiones.sessionId(codigo))
            // Si mientras tanto se cerró la sesión o cambió el estudiante, no se guarda
            if (almacen.codigoEstudiante.first() == codigo) almacen.guardarPerfil(p)
            _estado.update { it.copy(actualizando = false) }
        } catch (e: CancellationException) {
            throw e
        } catch (e: ChatException) {
            // En segundo plano los fallos se ignoran y se conserva el perfil en caché
            _estado.update { it.copy(actualizando = false, errorActualizar = if (silencioso) null else e.message) }
        } catch (e: Exception) {
            _estado.update {
                it.copy(actualizando = false, errorActualizar = if (silencioso) null else "Ocurrió un error inesperado. Intenta de nuevo.")
            }
        }
    }

    companion object {
        /** Mensaje del ingreso; el error de token apunta al botón de ajustes de la pantalla. */
        fun mensajeIngreso(e: ChatException): String = when (e.tipo) {
            TipoError.TOKEN -> "El token del chat es incorrecto. Revísalo en \"Ajustes del webhook\"."
            TipoError.CONFIGURACION -> "Falta configurar el webhook. Escríbelo en \"Ajustes del webhook\"."
            else -> e.message ?: "No se pudo ingresar. Intenta de nuevo."
        }
    }
}
