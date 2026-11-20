package co.edu.unab.cbdatos.ui

import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle

/**
 * Convierte el Markdown sencillo que devuelve el asistente en texto con estilo para la burbuja del chat:
 * **negrita**, *cursiva*, listas con "* " o "- " (se muestran con viñeta) y encabezados "# " (en negrita).
 * Lo demás se muestra tal cual.
 */
object Markdown {

    private val ENFASIS = Regex("""\*\*(.+?)\*\*|(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])""")

    fun aTexto(markdown: String): AnnotatedString = buildAnnotatedString {
        val lineas = markdown.replace("\r\n", "\n").split('\n')
        lineas.forEachIndexed { i, original ->
            var linea = original
            val vineta = Regex("""^(\s*)[*-]\s+""").find(linea)
            val encabezado = Regex("""^\s*#{1,6}\s+""").find(linea)
            when {
                vineta != null -> {
                    append(vineta.groupValues[1])
                    append("• ")
                    linea = linea.substring(vineta.range.last + 1)
                }
                encabezado != null -> linea = linea.substring(encabezado.range.last + 1)
            }
            if (encabezado != null) {
                withStyle(SpanStyle(fontWeight = FontWeight.Bold)) { agregarEnfasis(linea) }
            } else {
                agregarEnfasis(linea)
            }
            if (i < lineas.lastIndex) append('\n')
        }
    }

    private fun AnnotatedString.Builder.agregarEnfasis(texto: String) {
        var desde = 0
        for (m in ENFASIS.findAll(texto)) {
            append(texto.substring(desde, m.range.first))
            val negrita = m.groups[1]?.value
            if (negrita != null) {
                withStyle(SpanStyle(fontWeight = FontWeight.Bold)) { append(negrita) }
            } else {
                withStyle(SpanStyle(fontStyle = FontStyle.Italic)) { append(m.groups[2]!!.value) }
            }
            desde = m.range.last + 1
        }
        append(texto.substring(desde))
    }
}
