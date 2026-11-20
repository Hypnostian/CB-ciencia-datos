package co.edu.unab.cbdatos

import co.edu.unab.cbdatos.data.ChatException
import co.edu.unab.cbdatos.data.ChatJson
import co.edu.unab.cbdatos.data.ChatRequest
import co.edu.unab.cbdatos.data.ChatResponse
import co.edu.unab.cbdatos.data.CodigoEstudiante
import co.edu.unab.cbdatos.data.Intenciones
import co.edu.unab.cbdatos.data.TipoError
import co.edu.unab.cbdatos.data.interpretarRespuesta
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class ModelosYValidacionTest {

    @Test
    fun `la peticion usa los nombres del contrato`() {
        val json = ChatJson.encodeToString(ChatRequest("U00123456", "abc-123", "Hola"))
        val obj = Json.parseToJsonElement(json).jsonObject
        assertEquals("U00123456", obj["estudiante_codigo"]!!.jsonPrimitive.content)
        assertEquals("abc-123", obj["session_id"]!!.jsonPrimitive.content)
        assertEquals("Hola", obj["mensaje"]!!.jsonPrimitive.content)
    }

    @Test
    fun `la respuesta completa se lee con fuentes`() {
        val cuerpo = """{"respuesta":"Texto","intencion":"cursos","fuentes":[{"titulo":"Plan","url":"https://unab.edu.co/plan"}],"extra":1}"""
        val r = ChatJson.decodeFromString<ChatResponse>(cuerpo)
        assertEquals("Texto", r.respuesta)
        assertEquals("cursos", r.intencion)
        assertEquals(1, r.fuentes.size)
        assertEquals("https://unab.edu.co/plan", r.fuentes[0].url)
    }

    @Test
    fun `una respuesta sin intencion ni fuentes usa valores por defecto`() {
        val r = ChatJson.decodeFromString<ChatResponse>("""{"respuesta":"Hola","intencion":null,"fuentes":null}""")
        assertEquals(Intenciones.GENERAL, r.intencion)
        assertTrue(r.fuentes.isEmpty())
    }

    @Test
    fun `json malformado produce error controlado`() {
        try {
            interpretarRespuesta(200, "<html>no es json</html>")
            fail("Debía fallar")
        } catch (e: ChatException) {
            assertEquals(TipoError.RESPUESTA_INVALIDA, e.tipo)
        }
    }

    @Test
    fun `respuesta vacia se trata como invalida`() {
        try {
            interpretarRespuesta(200, """{"respuesta":"  "}""")
            fail("Debía fallar")
        } catch (e: ChatException) {
            assertEquals(TipoError.RESPUESTA_INVALIDA, e.tipo)
        }
    }

    @Test
    fun `codigos http se traducen a errores claros`() {
        fun tipo(c: Int) = try { interpretarRespuesta(c, ""); null } catch (e: ChatException) { e.tipo }
        assertEquals(TipoError.TOKEN, tipo(401))
        assertEquals(TipoError.NO_ENCONTRADO, tipo(404))
        assertEquals(TipoError.SERVIDOR, tipo(500))
        assertEquals(TipoError.SERVIDOR, tipo(503))
        assertEquals(TipoError.OTRO, tipo(418))
    }

    @Test
    fun `codigo de estudiante valido`() {
        assertTrue(CodigoEstudiante.esValido("U00123456"))
        assertTrue(CodigoEstudiante.esValido("  u00123456 "))
    }

    @Test
    fun `codigo de estudiante invalido`() {
        listOf("", "U0012345", "U001234567", "U01123456", "00123456", "U00ABC456", "U00 23456").forEach {
            assertFalse("Debía ser inválido: '$it'", CodigoEstudiante.esValido(it))
        }
    }

    @Test
    fun `etiquetas de intencion`() {
        assertEquals("Matrícula", Intenciones.etiqueta("matricula"))
        assertEquals("Fuera de tema", Intenciones.etiqueta("fuera_de_tema"))
        assertEquals("General", Intenciones.etiqueta("algo_raro"))
    }
}
