package co.edu.unab.cbdatos

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import co.edu.unab.cbdatos.data.SettingsStore
import co.edu.unab.cbdatos.data.WebhookChatRepository
import co.edu.unab.cbdatos.ui.AppViewModel
import co.edu.unab.cbdatos.ui.ChatViewModel
import co.edu.unab.cbdatos.ui.NoticiasViewModel
import co.edu.unab.cbdatos.ui.PerfilViewModel
import co.edu.unab.cbdatos.ui.screens.PerfilScreen
import co.edu.unab.cbdatos.ui.screens.ChatScreen
import co.edu.unab.cbdatos.ui.screens.LoginScreen
import co.edu.unab.cbdatos.ui.screens.NoticiasScreen
import co.edu.unab.cbdatos.ui.screens.SettingsScreen
import co.edu.unab.cbdatos.ui.theme.AsistenteTheme

class MainActivity : ComponentActivity() {
    private val ajustes by lazy { SettingsStore(applicationContext) }
    private val repositorio by lazy { WebhookChatRepository(configProvider = { ajustes.config() }) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent { Raiz() }
    }

    @Composable
    private fun Raiz() {
        val app: AppViewModel = viewModel(factory = viewModelFactory { initializer { AppViewModel(ajustes) } })
        val perfilVm: PerfilViewModel = viewModel(factory = viewModelFactory { initializer { PerfilViewModel(ajustes, repositorio, ajustes) } })
        val perfil by perfilVm.perfil.collectAsStateWithLifecycle()
        val estadoPerfil by perfilVm.estado.collectAsStateWithLifecycle()
        val codigo by app.codigo.collectAsStateWithLifecycle()
        val url by app.webhookUrl.collectAsStateWithLifecycle()
        val token by app.chatToken.collectAsStateWithLifecycle()
        val oscuro by app.temaOscuro.collectAsStateWithLifecycle()
        var enAjustes by rememberSaveable { mutableStateOf(false) }
        var enPerfil by rememberSaveable { mutableStateOf(false) }
        var enNoticias by rememberSaveable { mutableStateOf(false) }

        AsistenteTheme(oscuro = oscuro) {
            Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                val c = codigo
                when {
                    enAjustes -> {
                        BackHandler { enAjustes = false }
                        SettingsScreen(
                            urlActual = url,
                            tokenActual = token,
                            temaOscuro = oscuro,
                            codigo = c,
                            onGuardar = app::guardarWebhook,
                            onTema = app::cambiarTema,
                            onCerrarSesion = { perfilVm.cerrarSesion(); enAjustes = false; enPerfil = false; enNoticias = false },
                            onVolver = { enAjustes = false },
                        )
                    }
                    enPerfil && !c.isNullOrEmpty() -> {
                        BackHandler { enPerfil = false }
                        PerfilScreen(
                            perfil = perfil,
                            actualizando = estadoPerfil.actualizando,
                            error = estadoPerfil.errorActualizar,
                            onActualizar = perfilVm::actualizar,
                            onCerrarSesion = { perfilVm.cerrarSesion(); enPerfil = false },
                            onVolver = { enPerfil = false },
                        )
                    }
                    enNoticias && !c.isNullOrEmpty() -> {
                        BackHandler { enNoticias = false }
                        val noticiasVm: NoticiasViewModel = viewModel(
                            key = "noticias_$c",
                            factory = viewModelFactory { initializer { NoticiasViewModel(c, repositorio, ajustes) } },
                        )
                        val estadoNoticias by noticiasVm.estado.collectAsStateWithLifecycle()
                        NoticiasScreen(
                            estado = estadoNoticias,
                            onActualizar = noticiasVm::cargar,
                            onCategoria = noticiasVm::elegirCategoria,
                            onVolver = { enNoticias = false },
                        )
                    }
                    c == null -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
                    c.isEmpty() -> LoginScreen(
                        ingresando = estadoPerfil.ingresando,
                        error = estadoPerfil.errorIngreso,
                        onIngresar = perfilVm::ingresar,
                        onCodigoCambiado = perfilVm::limpiarErrorIngreso,
                        onAjustes = { enAjustes = true },
                    )
                    else -> {
                        val chat: ChatViewModel = viewModel(
                            key = "chat_$c",
                            factory = viewModelFactory { initializer { ChatViewModel(c, repositorio, ajustes) } },
                        )
                        val estado by chat.estado.collectAsStateWithLifecycle()
                        ChatScreen(
                            codigo = c,
                            perfil = perfil,
                            estado = estado,
                            onEnviar = chat::enviar,
                            onReintentar = chat::reintentar,
                            onNuevaConversacion = chat::nuevaConversacion,
                            onAjustes = { enAjustes = true },
                            onPerfil = { enPerfil = true },
                            onNoticias = { enNoticias = true },
                        )
                    }
                }
            }
        }
    }
}
