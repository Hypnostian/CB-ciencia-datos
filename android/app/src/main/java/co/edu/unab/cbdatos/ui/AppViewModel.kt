package co.edu.unab.cbdatos.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import co.edu.unab.cbdatos.data.SettingsStore
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/** Estado de la sesión del estudiante: null mientras DataStore carga, "" si no ha ingresado. */
class AppViewModel(private val ajustes: SettingsStore) : ViewModel() {

    val codigo: StateFlow<String?> = ajustes.codigoEstudiante.map { it.orEmpty() }.stateIn(viewModelScope, SharingStarted.Eagerly, null)

    val webhookUrl: StateFlow<String> = ajustes.webhookUrl.stateIn(viewModelScope, SharingStarted.Eagerly, "")
    val chatToken: StateFlow<String> = ajustes.chatToken.stateIn(viewModelScope, SharingStarted.Eagerly, "")
    val temaOscuro: StateFlow<Boolean> = ajustes.temaOscuro.stateIn(viewModelScope, SharingStarted.Eagerly, false)

    fun guardarWebhook(url: String, token: String) {
        viewModelScope.launch { ajustes.guardarWebhook(url, token) }
    }

    fun cambiarTema(oscuro: Boolean) {
        viewModelScope.launch { ajustes.guardarTemaOscuro(oscuro) }
    }
}
