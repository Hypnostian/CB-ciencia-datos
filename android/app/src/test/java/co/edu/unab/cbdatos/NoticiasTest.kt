package co.edu.unab.cbdatos

import co.edu.unab.cbdatos.data.ChatException
import co.edu.unab.cbdatos.data.NoticiaFormato
import co.edu.unab.cbdatos.data.TipoError
import co.edu.unab.cbdatos.data.interpretarNoticias
import java.time.LocalDate
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

private const val RESPUESTA = """{"noticias": {
  "fecha_consulta": "2026-11-18", "total": 3, "de_hoy": 2,
  "categorias": ["Educación", "Ingeniería de Sistemas", "Tecnología"],
  "noticias": [
    {"titulo": "Google lanza alerta por ciberataques con IA", "url": "https://www.eltiempo.com/a", "fecha": "2026-11-18T12:58:00+00:00",
     "categoria": "Tecnología", "resumen": "Nuevas amenazas.", "fuente": "El Tiempo", "es_hoy": true},
    {"titulo": "Programa de Ingeniería de Sistemas logra acreditación", "url": "https://news.google.com/b",
     "fecha": "2026-11-18T18:33:00+00:00", "categoria": "Ingeniería de Sistemas", "resumen": "",
     "fuente": "Emisora Ondas de Ibagué (vía Google Noticias)", "es_hoy": true},
    {"titulo": "Ranking de universidades", "url": "https://www.eltiempo.com/c", "fecha": "2026-11-10T14:03:58+00:00",
     "categoria": "Educación", "fuente": "UNAB", "campo_nuevo": 1}
  ]}}"""

class NoticiasTest {
    @Test
    fun interpreta_la_respuesta_de_la_accion_noticias() {
        val d = interpretarNoticias(200, RESPUESTA)
        assertEquals("2026-11-18", d.fechaConsulta)
        assertEquals(2, d.deHoy)
        assertEquals(3, d.noticias.size)
        assertTrue(d.noticias[0].esHoy)
        assertFalse(d.noticias[2].esHoy)
        assertEquals("", d.noticias[2].resumen)
    }

    @Test
    fun errores_del_webhook_se_traducen() {
        try {
            interpretarNoticias(401, "{}")
            fail("debía fallar")
        } catch (e: ChatException) {
            assertEquals(TipoError.TOKEN, e.tipo)
        }
        try {
            interpretarNoticias(200, """{"respuesta": "sin noticias"}""")
            fail("debía fallar")
        } catch (e: ChatException) {
            assertEquals(TipoError.RESPUESTA_INVALIDA, e.tipo)
        }
        try {
            interpretarNoticias(502, """{"error": "x"}""")
            fail("debía fallar")
        } catch (e: ChatException) {
            assertEquals(TipoError.SERVIDOR, e.tipo)
        }
    }

    @Test
    fun la_fecha_se_muestra_en_hora_de_colombia() {
        val hoy = LocalDate.of(2026, 11, 18)
        assertEquals("Hoy, 07:58", NoticiaFormato.fecha("2026-11-18T12:58:00+00:00", hoy))
        // 03:00 UTC del 19 son las 22:00 del 18 en Colombia
        assertEquals("Hoy, 22:00", NoticiaFormato.fecha("2026-11-19T03:00:00Z", hoy))
        assertEquals("Ayer, 22:26", NoticiaFormato.fecha("2026-11-17T22:26:24-05:00", hoy))
        assertEquals("10 nov 2026", NoticiaFormato.fecha("2026-11-10T14:03:58+00:00", hoy))
        assertEquals("", NoticiaFormato.fecha(null, hoy))
    }

    @Test
    fun separa_el_medio_del_agregador() {
        assertEquals("Emisora Ondas de Ibagué", NoticiaFormato.medio("Emisora Ondas de Ibagué (vía Google Noticias)"))
        assertEquals("Google Noticias", NoticiaFormato.via("Emisora Ondas de Ibagué (vía Google Noticias)"))
        assertEquals("El Tiempo", NoticiaFormato.medio("El Tiempo"))
        assertNull(NoticiaFormato.via("UNAB"))
    }

    @Test
    fun filtra_por_categoria() {
        val lista = interpretarNoticias(200, RESPUESTA).noticias
        assertEquals(3, NoticiaFormato.filtrar(lista, NoticiaFormato.TODAS).size)
        assertEquals(1, NoticiaFormato.filtrar(lista, "Tecnología").size)
        assertEquals(0, NoticiaFormato.filtrar(lista, "Vida UNAB").size)
        assertEquals("18 de noviembre de 2026", NoticiaFormato.encabezado("2026-11-18"))
    }
}
