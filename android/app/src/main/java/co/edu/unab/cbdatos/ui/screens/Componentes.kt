package co.edu.unab.cbdatos.ui.screens

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import co.edu.unab.cbdatos.data.Intenciones
import co.edu.unab.cbdatos.ui.theme.Cian
import co.edu.unab.cbdatos.ui.theme.DegradadoNaranja
import co.edu.unab.cbdatos.ui.theme.Morado
import co.edu.unab.cbdatos.ui.theme.Naranja
import co.edu.unab.cbdatos.ui.theme.Rojo
import co.edu.unab.cbdatos.ui.theme.Verde

/** Color de la insignia de cada intención (cursos morado, calendario cian, noticias verde, general naranja). */
fun colorIntencion(intencion: String?): Color = when (intencion?.trim()?.lowercase()) {
    Intenciones.CURSOS -> Morado
    Intenciones.MATRICULA -> Color(0xFFB04FF0)
    Intenciones.CALENDARIO -> Cian
    Intenciones.NOTICIAS -> Verde
    Intenciones.FUERA_DE_TEMA -> Color(0xFF8E8A99)
    else -> Naranja
}

/** Tarjeta blanca con borde suave, la base visual de las secciones. */
@Composable
fun TarjetaSuave(modifier: Modifier = Modifier, contenido: @Composable ColumnScope.() -> Unit) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 2.dp,
        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp), content = contenido)
    }
}

/** Icono dentro de un círculo con el color de fondo atenuado. */
@Composable
fun IconoEnCirculo(icono: ImageVector, color: Color, tamano: Dp = 40.dp) {
    Box(
        Modifier.size(tamano).clip(CircleShape).background(color.copy(alpha = 0.14f)),
        contentAlignment = Alignment.Center,
    ) {
        Icon(icono, contentDescription = null, tint = color, modifier = Modifier.size(tamano * 0.55f))
    }
}

/** Título de sección con icono. */
@Composable
fun TituloSeccion(texto: String, icono: ImageVector, color: Color, extra: @Composable () -> Unit = {}) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        IconoEnCirculo(icono, color, 36.dp)
        Text(texto, style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(start = 12.dp).weight(1f))
        extra()
    }
}

/** Píldora de texto (insignias de estado). */
@Composable
fun Pildora(texto: String, color: Color, modifier: Modifier = Modifier, solida: Boolean = false) {
    Text(
        texto,
        style = MaterialTheme.typography.labelSmall,
        color = if (solida) Color.White else color,
        modifier = modifier
            .clip(RoundedCornerShape(50))
            .background(if (solida) color else color.copy(alpha = 0.13f))
            .padding(horizontal = 10.dp, vertical = 4.dp),
    )
}

/** Anillo de progreso animado con contenido en el centro. */
@Composable
fun AnilloProgreso(
    fraccion: Float,
    color: Color,
    tamano: Dp = 96.dp,
    grosor: Dp = 10.dp,
    fondo: Color = MaterialTheme.colorScheme.surfaceVariant,
    centro: @Composable () -> Unit = {},
) {
    val animada by animateFloatAsState(fraccion.coerceIn(0f, 1f), tween(900), label = "anillo")
    Box(Modifier.size(tamano), contentAlignment = Alignment.Center) {
        Canvas(Modifier.size(tamano)) {
            val g = grosor.toPx()
            val lado = size.minDimension - g
            val esquina = Offset(g / 2, g / 2)
            drawArc(fondo, -90f, 360f, false, esquina, Size(lado, lado), style = Stroke(g, cap = StrokeCap.Round))
            if (animada > 0f) {
                drawArc(color, -90f, 360f * animada, false, esquina, Size(lado, lado), style = Stroke(g, cap = StrokeCap.Round))
            }
        }
        centro()
    }
}

/** Avatar con iniciales sobre un degradado naranja y borde blanco. */
@Composable
fun AvatarIniciales(iniciales: String, tamano: Dp = 64.dp) {
    Box(
        Modifier
            .size(tamano)
            .clip(CircleShape)
            .background(DegradadoNaranja)
            .border(3.dp, Color.White.copy(alpha = 0.85f), CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            iniciales,
            color = Color.White,
            fontWeight = FontWeight.Bold,
            style = if (tamano >= 60.dp) MaterialTheme.typography.headlineSmall else MaterialTheme.typography.titleMedium,
        )
    }
}

/** Color de estado aprobado / pendiente. */
fun colorEstado(aprobado: Boolean): Color = if (aprobado) Verde else Rojo
