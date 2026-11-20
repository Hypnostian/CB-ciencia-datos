package co.edu.unab.cbdatos.ui.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import co.edu.unab.cbdatos.ui.theme.Morado
import co.edu.unab.cbdatos.ui.theme.Naranja

/** Logo propio: globo de chat con birrete de graduación, dibujado con formas simples. */
@Composable
fun LogoAsistente(tamano: Dp = 96.dp, modifier: Modifier = Modifier) {
    Canvas(modifier.size(tamano)) {
        val w = size.width
        val h = size.height
        // Fondo circular morado
        drawCircle(Morado, radius = w / 2)
        // Globo de chat blanco
        drawRoundRect(
            Color.White,
            topLeft = Offset(w * 0.17f, h * 0.22f),
            size = Size(w * 0.66f, h * 0.46f),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(w * 0.09f),
        )
        val cola = Path().apply {
            moveTo(w * 0.33f, h * 0.66f)
            lineTo(w * 0.28f, h * 0.82f)
            lineTo(w * 0.48f, h * 0.66f)
            close()
        }
        drawPath(cola, Color.White, style = Fill)
        // Birrete naranja
        val tapa = Path().apply {
            moveTo(w * 0.50f, h * 0.30f)
            lineTo(w * 0.74f, h * 0.43f)
            lineTo(w * 0.50f, h * 0.56f)
            lineTo(w * 0.26f, h * 0.43f)
            close()
        }
        drawPath(tapa, Naranja, style = Fill)
        val base = Path().apply {
            moveTo(w * 0.36f, h * 0.50f)
            lineTo(w * 0.36f, h * 0.58f)
            quadraticTo(w * 0.50f, h * 0.67f, w * 0.64f, h * 0.58f)
            lineTo(w * 0.64f, h * 0.50f)
            lineTo(w * 0.50f, h * 0.57f)
            close()
        }
        drawPath(base, Naranja, style = Fill)
        drawRect(Morado, topLeft = Offset(w * 0.715f, h * 0.44f), size = Size(w * 0.02f, h * 0.14f))
    }
}
