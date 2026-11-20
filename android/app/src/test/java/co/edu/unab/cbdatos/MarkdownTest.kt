package co.edu.unab.cbdatos

import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import co.edu.unab.cbdatos.ui.Markdown
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class MarkdownTest {

    @Test
    fun negritaSinAsteriscos() {
        val t = Markdown.aTexto("Llevas un avance del **37.3%** en el plan.")
        assertEquals("Llevas un avance del 37.3% en el plan.", t.text)
        val estilo = t.spanStyles.single()
        assertEquals(FontWeight.Bold, estilo.item.fontWeight)
        assertEquals("37.3%", t.text.substring(estilo.start, estilo.end))
    }

    @Test
    fun listasConVineta() {
        val t = Markdown.aTexto("Cursos:\n* **Desarrollo frontend** (ISIS403) - NRC: **76710**\n- Electromagnetismo")
        assertEquals("Cursos:\n• Desarrollo frontend (ISIS403) - NRC: 76710\n• Electromagnetismo", t.text)
        assertEquals(2, t.spanStyles.count { it.item.fontWeight == FontWeight.Bold })
    }

    @Test
    fun cursivaYTextoNormal() {
        val t = Markdown.aTexto("*(Nota: fecha sin verificar)* y 3 * 4 = 12")
        assertEquals("(Nota: fecha sin verificar) y 3 * 4 = 12", t.text)
        assertTrue(t.spanStyles.any { it.item.fontStyle == FontStyle.Italic })
    }

    @Test
    fun encabezadoEnNegrita() {
        val t = Markdown.aTexto("## Semestre 1\nÁlgebra lineal")
        assertEquals("Semestre 1\nÁlgebra lineal", t.text)
        assertEquals(FontWeight.Bold, t.spanStyles.single().item.fontWeight)
    }
}
