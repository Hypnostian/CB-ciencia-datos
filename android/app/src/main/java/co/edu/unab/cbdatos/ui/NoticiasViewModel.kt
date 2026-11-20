package co.edu.unab.cbdatos.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import co.edu.unab.cbdatos.data.ChatException
import co.edu.unab.cbdatos.data.NoticiaFormato
import co.edu.unab.cbdatos.data.NoticiasDelDia
import co.edu.unab.cbdatos.data.NoticiasRepository
import co.edu.unab.cbdatos.data.SessionStore
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class NoticiasUiState(
    val cargando: Boolean = false,
    val datos: NoticiasDelDia? = null,
    val error: String? = null,
    val categoria: String = NoticiaFormato.TODAS,
)

/** Pantalla "Noticias del día": carga las noticias del scraper por el webhook y filtra por categoría. */
class NoticiasViewModel(
    private val codigo: String,
    private val repositorio: NoticiasRepository,
    private val sesiones: SessionStore,
) : ViewModel() {
    private val _estado = MutableStateFlow(NoticiasUiState())
    val estado: StateFlow<NoticiasUiState> = _estado.asStateFlow()

    init {
        cargar()
    }

    fun cargar() {
        if (_estado.value.cargando) return
        _estado.update { it.copy(cargando = true, error = null) }
        viewModelScope.launch {
            try {
                val datos = repositorio.noticias(codigo, sesiones.sessionId(codigo))
                _estado.update { it.copy(cargando = false, datos = datos) }
            } catch (e: CancellationException) {
                throw e
            } catch (e: ChatException) {
                _estado.update { it.copy(cargando = false, error = e.message) }
            } catch (e: Exception) {
                _estado.update { it.copy(cargando = false, error = "Ocurrió un error inesperado. Intenta de nuevo.") }
            }
        }
    }

    fun elegirCategoria(categoria: String) {
        _estado.update { it.copy(categoria = categoria) }
    }
}
