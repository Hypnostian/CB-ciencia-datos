package co.edu.unab.cbdatos

import co.edu.unab.cbdatos.data.ChatException
import co.edu.unab.cbdatos.data.ChatRepository
import co.edu.unab.cbdatos.data.ChatResponse
import co.edu.unab.cbdatos.data.Fuente
import co.edu.unab.cbdatos.data.SessionStore
import co.edu.unab.cbdatos.data.TipoError
import co.edu.unab.cbdatos.ui.Autor
import co.edu.unab.cbdatos.ui.ChatViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ChatViewModelTest {

    private class RepoFalso : ChatRepository {
        val llamadas = mutableListOf<Triple<String, String, String>>()
        var fallar: ChatException? = null

        override suspend fun enviar(estudianteCodigo: String, sessionId: String, mensaje: String): ChatResponse {
            llamadas += Triple(estudianteCodigo, sessionId, mensaje)
            fallar?.let { throw it }
            return ChatResponse("Respuesta a: $mensaje", "cursos", listOf(Fuente("Plan", "https://unab.edu.co")))
        }
    }

    private class SesionesFalsas : SessionStore {
        var actual = "sesion-1"
        var contador = 1
        var historial: String? = null
        override suspend fun leerHistorial(codigo: String) = historial
        override suspend fun guardarHistorial(codigo: String, json: String?) {
            historial = json
        }
        override suspend fun sessionId(codigo: String) = actual
        override suspend fun nuevaSesion(codigo: String): String {
            contador++
            actual = "sesion-$contador"
            return actual
        }
    }

    private val despachador = StandardTestDispatcher()
    private lateinit var repo: RepoFalso
    private lateinit var sesiones: SesionesFalsas
    private lateinit var vm: ChatViewModel

    @Before
    fun preparar() {
        Dispatchers.setMain(despachador)
        repo = RepoFalso()
        sesiones = SesionesFalsas()
        vm = ChatViewModel("U00123456", repo, sesiones)
    }

    @After
    fun limpiar() {
        Dispatchers.resetMain()
    }

    @Test
    fun `camino feliz agrega mensaje del usuario y respuesta con intencion y fuentes`() = runTest(despachador) {
        vm.enviar("¿Qué cursos debo tomar?")
        assertTrue(vm.estado.value.escribiendo)
        advanceUntilIdle()

        val e = vm.estado.value
        assertFalse(e.escribiendo)
        assertNull(e.error)
        assertEquals(2, e.mensajes.size)
        assertEquals(Autor.USUARIO, e.mensajes[0].autor)
        assertEquals(Autor.ASISTENTE, e.mensajes[1].autor)
        assertEquals("cursos", e.mensajes[1].intencion)
        assertEquals(1, e.mensajes[1].fuentes.size)
        assertEquals(Triple("U00123456", "sesion-1", "¿Qué cursos debo tomar?"), repo.llamadas.single())
    }

    @Test
    fun `mensaje en blanco no se envia`() = runTest(despachador) {
        vm.enviar("   ")
        advanceUntilIdle()
        assertTrue(vm.estado.value.mensajes.isEmpty())
        assertTrue(repo.llamadas.isEmpty())
    }

    @Test
    fun `error permite reintentar sin duplicar el mensaje`() = runTest(despachador) {
        repo.fallar = ChatException(TipoError.SIN_CONEXION, "Sin conexión")
        vm.enviar("Hola")
        advanceUntilIdle()
        assertEquals("Sin conexión", vm.estado.value.error)
        assertEquals("Hola", vm.estado.value.pendiente)
        assertEquals(1, vm.estado.value.mensajes.size)

        repo.fallar = null
        vm.reintentar()
        advanceUntilIdle()
        val e = vm.estado.value
        assertNull(e.error)
        assertNull(e.pendiente)
        assertEquals(2, e.mensajes.size)
        assertEquals(2, repo.llamadas.size)
    }

    @Test
    fun `nueva conversacion limpia el chat y cambia el session_id`() = runTest(despachador) {
        vm.enviar("Hola")
        advanceUntilIdle()
        vm.nuevaConversacion()
        advanceUntilIdle()
        assertTrue(vm.estado.value.mensajes.isEmpty())
        assertNotEquals("sesion-1", sesiones.actual)

        vm.enviar("Otra")
        advanceUntilIdle()
        assertNotNull(repo.llamadas.last().second)
        assertEquals(sesiones.actual, repo.llamadas.last().second)
    }

    @Test
    fun `nueva conversacion limpia la pantalla de inmediato y un envio posterior usa la sesion nueva`() = runTest(despachador) {
        vm.enviar("Hola")
        advanceUntilIdle()
        vm.nuevaConversacion()
        // Sin avanzar el despachador: la pantalla ya esta limpia y el cambio de sesion sigue pendiente
        assertTrue(vm.estado.value.mensajes.isEmpty())
        vm.enviar("Pregunta nueva")
        advanceUntilIdle()
        assertEquals(2, vm.estado.value.mensajes.size)
        assertEquals("Pregunta nueva", vm.estado.value.mensajes[0].texto)
        assertEquals("sesion-2", repo.llamadas.last().second)
        assertEquals(2, vm.estado.value.mensajes.size)
    }

    @Test
    fun `la conversacion se guarda y se restaura al reiniciar`() = runTest(despachador) {
        vm.enviar("Hola")
        advanceUntilIdle()
        assertNotNull(sesiones.historial)

        val nuevo = ChatViewModel("U00123456", repo, sesiones)
        advanceUntilIdle()
        val m = nuevo.estado.value.mensajes
        assertEquals(2, m.size)
        assertEquals("Hola", m[0].texto)
        assertEquals("cursos", m[1].intencion)
        assertEquals(1, m[1].fuentes.size)

        nuevo.enviar("Otra")
        advanceUntilIdle()
        assertEquals(4, nuevo.estado.value.mensajes.size)
        assertEquals(4, nuevo.estado.value.mensajes.map { it.id }.toSet().size)
    }

    @Test
    fun `nueva conversacion borra el historial guardado`() = runTest(despachador) {
        vm.enviar("Hola")
        advanceUntilIdle()
        vm.nuevaConversacion()
        advanceUntilIdle()
        assertTrue(sesiones.historial == null || sesiones.historial == "[]")
        val nuevo = ChatViewModel("U00123456", repo, sesiones)
        advanceUntilIdle()
        assertTrue(nuevo.estado.value.mensajes.isEmpty())
    }

    @Test
    fun `solo se guardan los ultimos 40 mensajes`() = runTest(despachador) {
        repeat(25) {
            vm.enviar("Mensaje $it")
            advanceUntilIdle()
        }
        val nuevo = ChatViewModel("U00123456", repo, sesiones)
        advanceUntilIdle()
        assertEquals(40, nuevo.estado.value.mensajes.size)
        assertEquals("Respuesta a: Mensaje 24", nuevo.estado.value.mensajes.last().texto)
    }
}
