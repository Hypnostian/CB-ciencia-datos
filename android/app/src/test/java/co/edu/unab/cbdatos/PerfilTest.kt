package co.edu.unab.cbdatos

import co.edu.unab.cbdatos.data.AlmacenSesion
import co.edu.unab.cbdatos.data.ChatException
import co.edu.unab.cbdatos.data.ChatJson
import co.edu.unab.cbdatos.data.PerfilEstudiante
import co.edu.unab.cbdatos.data.PerfilFormato
import co.edu.unab.cbdatos.data.PerfilRepository
import co.edu.unab.cbdatos.data.PerfilRequest
import co.edu.unab.cbdatos.data.PerfilResponse
import co.edu.unab.cbdatos.data.SessionStore
import co.edu.unab.cbdatos.data.TipoError
import co.edu.unab.cbdatos.data.interpretarPerfil
import co.edu.unab.cbdatos.ui.PerfilViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test

private const val PERFIL_COMPLETO = """{"perfil": {
  "codigo":"U00179643", "nombre":"Juan Sebastián Lizcano Jaimes", "nombres":"Juan Sebastián", "apellidos":"Lizcano Jaimes",
  "correo":"u00179643@demo.unab.local", "programa":"Ingeniería de Sistemas", "semestre_actual":7, "estado":"activo",
  "periodo_actual":"2026-2",
  "horario":[{"nrc":"12345","curso_codigo":"ISIS701","curso":"Arquitectura de software","creditos":3,"profesor":"Ana Pérez","horario":"Lun-Mié 07:00-09:00"}],
  "creditos_inscritos":17,
  "avance":{"creditos_aprobados":91,"creditos_totales":151,"porcentaje_avance":60.3,"cursos_aprobados":34,"cursos_plan":51},
  "competencias_digitales":{"requisito":"Competencias Digitales R2025","fecha_prueba":"2025-03-22",
    "competencias":[{"competencia":"Vida en línea","estado":"aprobada","cumplida_con":"Examen Vida en línea"},
                    {"competencia":"MS Word","estado":"no aprobada","cumplida_con":null}],
    "faltantes":["MS Word"],"total_aprobadas":1,"total_pilares":2,"cumplido":false},
  "horas_libres":{"horas_cumplidas":104,"horas_requeridas":96,"horas_faltantes":0,"completo":true},
  "nuevo":false, "campo_futuro": 1
}}"""

class PerfilJsonTest {

    @Test
    fun `perfil completo se lee con horario y avance`() {
        val p = interpretarPerfil(200, PERFIL_COMPLETO)
        assertEquals("U00179643", p.codigo)
        assertEquals("Juan Sebastián", p.nombres)
        assertEquals(7, p.semestreActual)
        assertEquals("2026-2", p.periodoActual)
        assertEquals(17, p.creditosInscritos)
        val c = p.horario.single()
        assertEquals("12345", c.nrc)
        assertEquals("ISIS701", c.cursoCodigo)
        assertEquals("Ana Pérez", c.profesor)
        assertEquals(3, c.creditos)
        assertEquals(91, p.avance!!.creditosAprobados)
        assertEquals(60.3, p.avance!!.porcentajeAvance, 0.001)
        assertFalse(p.nuevo)
    }

    @Test
    fun `perfil trae competencias digitales y horas libres`() {
        val p = interpretarPerfil(200, PERFIL_COMPLETO)
        val c = p.competenciasDigitales!!
        assertEquals(listOf("MS Word"), c.faltantes)
        assertTrue(c.competencias[0].aprobada)
        assertFalse(c.competencias[1].aprobada)
        assertEquals("Examen Vida en línea", c.competencias[0].cumplidaCon)
        val h = p.horasLibres!!
        assertTrue(h.completo)
        assertEquals(1f, PerfilFormato.fraccionHoras(h))
        assertTrue(PerfilFormato.textoHoras(h).startsWith("Requisito cumplido"))
        assertEquals("JL", PerfilFormato.iniciales(p))
        assertEquals("Llevas 8 horas adicionales.", PerfilFormato.horasAdicionales(h))
        assertEquals("Llevas 1 hora adicional.", PerfilFormato.horasAdicionales(h.copy(horasCumplidas = 97)))
        assertEquals("22 de marzo de 2025", PerfilFormato.fechaLarga(c.fechaPrueba!!))
        assertEquals("sin fecha", PerfilFormato.fechaLarga("sin fecha"))
        assertEquals("60%", PerfilFormato.porcentajeTexto(p.avance!!))
        val pendiente = h.copy(horasCumplidas = 40, horasFaltantes = 56, completo = false)
        assertEquals("Te faltan 56 horas para graduarte", PerfilFormato.textoHoras(pendiente))
    }

    @Test
    fun `perfil minimo usa valores por defecto`() {
        val p = interpretarPerfil(200, """{"perfil":{"codigo":"U00000001","nombre":"Ana Gómez"}}""")
        assertEquals("Ana Gómez", p.nombre)
        assertNull(p.semestreActual)
        assertNull(p.avance)
        assertNull(p.competenciasDigitales)
        assertNull(p.horasLibres)
        assertTrue(p.horario.isEmpty())
        assertEquals("", p.programa)
        assertEquals("U00000001", PerfilFormato.subtitulo(p))
    }

    @Test
    fun `la peticion de perfil no lleva mensaje y usa los nombres del contrato`() {
        val obj = Json.parseToJsonElement(ChatJson.encodeToString(PerfilRequest("perfil", "U00179643", "s-1"))).jsonObject
        assertEquals("perfil", obj["accion"]!!.jsonPrimitive.content)
        assertEquals("U00179643", obj["estudiante_codigo"]!!.jsonPrimitive.content)
        assertEquals("s-1", obj["session_id"]!!.jsonPrimitive.content)
        assertFalse(obj.containsKey("mensaje"))
    }

    @Test
    fun `el perfil sobrevive a guardar y leer como JSON`() {
        val original = interpretarPerfil(200, PERFIL_COMPLETO)
        val copia = ChatJson.decodeFromString<PerfilEstudiante>(ChatJson.encodeToString(original))
        assertEquals(original, copia)
    }

    @Test
    fun `errores HTTP del perfil se traducen`() {
        fun tipo(codigo: Int, cuerpo: String): ChatException = try {
            interpretarPerfil(codigo, cuerpo); throw AssertionError("debía fallar")
        } catch (e: ChatException) {
            e
        }
        assertEquals(TipoError.TOKEN, tipo(401, """{"respuesta":"No autorizado."}""").tipo)
        assertEquals(TipoError.NO_ENCONTRADO, tipo(404, "").tipo)
        assertEquals(TipoError.SERVIDOR, tipo(503, "").tipo)
        val e400 = tipo(400, """{"error":"Código inválido"}""")
        assertEquals(TipoError.CODIGO_INVALIDO, e400.tipo)
        assertEquals("Código inválido", e400.message)
        assertEquals("No válido", tipo(400, """{"respuesta":"No válido"}""").message)
        assertEquals(TipoError.CODIGO_INVALIDO, tipo(400, "no es json").tipo)
        assertEquals(TipoError.RESPUESTA_INVALIDA, tipo(200, "no es json").tipo)
        assertEquals(TipoError.RESPUESTA_INVALIDA, tipo(200, "{}").tipo)
        assertEquals(TipoError.RESPUESTA_INVALIDA, tipo(200, """{"perfil":{"nombre":"x"}}""").tipo)
    }

    @Test
    fun `respuesta envoltorio vacia da perfil nulo`() {
        assertNull(ChatJson.decodeFromString<PerfilResponse>("{}").perfil)
    }
}

class PerfilFormatoTest {
    private val completo = interpretarPerfil(200, PERFIL_COMPLETO)

    @Test
    fun `subtitulo con programa y semestre`() {
        assertEquals("Ingeniería de Sistemas, semestre 7", PerfilFormato.subtitulo(completo))
    }

    @Test
    fun `subtitulo con solo una parte`() {
        assertEquals("semestre 3", PerfilFormato.subtitulo(PerfilEstudiante("U00000001", "Ana", semestreActual = 3)))
        assertEquals("Derecho", PerfilFormato.subtitulo(PerfilEstudiante("U00000001", "Ana", programa = "Derecho")))
    }

    @Test
    fun `nombre largo se acorta a nombres mas primer apellido`() {
        assertEquals("Juan Sebastián Lizcano", PerfilFormato.nombreEncabezado(completo))
    }

    @Test
    fun `nombre corto se muestra completo`() {
        assertEquals("Ana Gómez Ruiz", PerfilFormato.nombreEncabezado(PerfilEstudiante("U00000001", "Ana Gómez Ruiz")))
    }

    @Test
    fun `nombre largo sin nombres separados usa las dos primeras palabras`() {
        val p = PerfilEstudiante("U00000001", "María Fernanda Rodríguez Castellanos")
        assertEquals("María Fernanda", PerfilFormato.nombreEncabezado(p))
    }

    @Test
    fun `primer nombre y saludo`() {
        assertEquals("Juan Sebastián", PerfilFormato.primerNombre(completo))
        assertEquals("Ana", PerfilFormato.primerNombre(PerfilEstudiante("U00000001", "Ana Gómez")))
        assertEquals("¡Hola, Juan! Soy tu asistente académico", PerfilFormato.saludo("Juan"))
        assertEquals("¡Hola! Soy tu asistente académico", PerfilFormato.saludo(""))
    }

    @Test
    fun `porcentaje usa el del servidor o lo calcula`() {
        assertEquals(60.3, PerfilFormato.porcentaje(completo.avance!!), 0.001)
        val sin = completo.avance!!.copy(porcentajeAvance = 0.0, creditosAprobados = 75, creditosTotales = 150)
        assertEquals(50.0, PerfilFormato.porcentaje(sin), 0.001)
    }
}

@OptIn(ExperimentalCoroutinesApi::class)
class PerfilViewModelTest {

    private class AlmacenFalso(codigo: String? = null, perfil: PerfilEstudiante? = null) : AlmacenSesion {
        override val codigoEstudiante = MutableStateFlow(codigo)
        override val perfil = MutableStateFlow(perfil)
        override suspend fun guardarSesion(codigo: String, perfil: PerfilEstudiante) {
            codigoEstudiante.value = codigo
            this.perfil.value = perfil
        }

        override suspend fun guardarPerfil(perfil: PerfilEstudiante) {
            this.perfil.value = perfil
        }

        override suspend fun cerrarSesion() {
            codigoEstudiante.value = null
            perfil.value = null
        }
    }

    private class RepoFalso : PerfilRepository {
        val llamadas = mutableListOf<Pair<String, String>>()
        var fallar: ChatException? = null
        var nombre = "Juan Sebastián Lizcano Jaimes"
        override suspend fun perfil(estudianteCodigo: String, sessionId: String): PerfilEstudiante {
            llamadas += estudianteCodigo to sessionId
            fallar?.let { throw it }
            return PerfilEstudiante(estudianteCodigo, nombre, programa = "Ingeniería de Sistemas", semestreActual = 7)
        }
    }

    private class SesionesFalsas : SessionStore {
        override suspend fun sessionId(codigo: String) = "sesion-$codigo"
        override suspend fun nuevaSesion(codigo: String) = "nueva-$codigo"
    }

    private val despachador = StandardTestDispatcher()
    private lateinit var repo: RepoFalso

    @Before
    fun preparar() {
        Dispatchers.setMain(despachador)
        repo = RepoFalso()
    }

    @After
    fun limpiar() {
        Dispatchers.resetMain()
    }

    @Test
    fun `ingreso exitoso guarda codigo en mayusculas y perfil`() = runTest(despachador) {
        val almacen = AlmacenFalso()
        val vm = PerfilViewModel(almacen, repo, SesionesFalsas())
        advanceUntilIdle()
        vm.ingresar(" u00179643 ")
        assertTrue(vm.estado.value.ingresando)
        advanceUntilIdle()

        assertFalse(vm.estado.value.ingresando)
        assertNull(vm.estado.value.errorIngreso)
        assertEquals("U00179643", almacen.codigoEstudiante.value)
        assertEquals("Juan Sebastián Lizcano Jaimes", almacen.perfil.value!!.nombre)
        assertEquals("U00179643" to "sesion-U00179643", repo.llamadas.single())
    }

    @Test
    fun `codigo con formato invalido no llama al servidor`() = runTest(despachador) {
        val almacen = AlmacenFalso()
        val vm = PerfilViewModel(almacen, repo, SesionesFalsas())
        advanceUntilIdle()
        vm.ingresar("12345")
        advanceUntilIdle()
        assertNotNull(vm.estado.value.errorIngreso)
        assertTrue(repo.llamadas.isEmpty())
        assertNull(almacen.codigoEstudiante.value)
    }

    @Test
    fun `fallo de red deja el ingreso sin guardar y con mensaje`() = runTest(despachador) {
        val almacen = AlmacenFalso()
        repo.fallar = ChatException(TipoError.SIN_CONEXION, "Sin conexión")
        val vm = PerfilViewModel(almacen, repo, SesionesFalsas())
        advanceUntilIdle()
        vm.ingresar("U00179643")
        advanceUntilIdle()

        assertFalse(vm.estado.value.ingresando)
        assertEquals("Sin conexión", vm.estado.value.errorIngreso)
        assertNull(almacen.codigoEstudiante.value)
        assertNull(almacen.perfil.value)
    }

    @Test
    fun `error de token apunta a Ajustes del webhook`() = runTest(despachador) {
        repo.fallar = ChatException(TipoError.TOKEN, "token")
        val vm = PerfilViewModel(AlmacenFalso(), repo, SesionesFalsas())
        advanceUntilIdle()
        vm.ingresar("U00179643")
        advanceUntilIdle()
        assertTrue(vm.estado.value.errorIngreso!!.contains("Ajustes del webhook"))
    }

    @Test
    fun `con sesion guardada refresca en segundo plano`() = runTest(despachador) {
        val cache = PerfilEstudiante("U00179643", "Nombre viejo")
        val almacen = AlmacenFalso("U00179643", cache)
        val vm = PerfilViewModel(almacen, repo, SesionesFalsas())
        advanceUntilIdle()
        assertEquals(1, repo.llamadas.size)
        assertEquals("Juan Sebastián Lizcano Jaimes", vm.perfil.value!!.nombre)
        assertNull(vm.estado.value.errorActualizar)
    }

    @Test
    fun `si el refresco falla se conserva el perfil en cache`() = runTest(despachador) {
        val cache = PerfilEstudiante("U00179643", "Nombre en cache")
        val almacen = AlmacenFalso("U00179643", cache)
        repo.fallar = ChatException(TipoError.SERVIDOR, "Servidor caido")
        val vm = PerfilViewModel(almacen, repo, SesionesFalsas())
        advanceUntilIdle()
        assertEquals("Nombre en cache", vm.perfil.value!!.nombre)
        assertNull(vm.estado.value.errorActualizar)
        assertFalse(vm.estado.value.actualizando)
    }

    @Test
    fun `actualizar manual muestra el error pero conserva el perfil`() = runTest(despachador) {
        val almacen = AlmacenFalso("U00179643", PerfilEstudiante("U00179643", "Nombre en cache"))
        val vm = PerfilViewModel(almacen, repo, SesionesFalsas())
        advanceUntilIdle()
        repo.fallar = ChatException(TipoError.TIEMPO_AGOTADO, "Tardó demasiado")
        vm.actualizar()
        advanceUntilIdle()
        assertEquals("Tardó demasiado", vm.estado.value.errorActualizar)
        assertNotNull(vm.perfil.value)

        repo.fallar = null
        repo.nombre = "Nombre nuevo"
        vm.actualizar()
        advanceUntilIdle()
        assertNull(vm.estado.value.errorActualizar)
        assertEquals("Nombre nuevo", vm.perfil.value!!.nombre)
    }

    @Test
    fun `cerrar sesion borra codigo y perfil`() = runTest(despachador) {
        val almacen = AlmacenFalso("U00179643", PerfilEstudiante("U00179643", "Ana"))
        val vm = PerfilViewModel(almacen, repo, SesionesFalsas())
        advanceUntilIdle()
        vm.cerrarSesion()
        advanceUntilIdle()
        assertNull(almacen.codigoEstudiante.value)
        assertNull(vm.perfil.value)
    }
}
