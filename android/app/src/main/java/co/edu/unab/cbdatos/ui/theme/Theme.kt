package co.edu.unab.cbdatos.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

// Colores de la marca UNAB (manual de identidad): morado, naranja, cian y verde.
val Morado = Color(0xFF8600DD)
val MoradoOscuro = Color(0xFF4A0080)
val MoradoProfundo = Color(0xFF26004D)
val Naranja = Color(0xFFF79800)
val NaranjaClaro = Color(0xFFFFB84D)
val Cian = Color(0xFF00B5E2)
val Verde = Color(0xFF6CC24A)
val Rojo = Color(0xFFE5484D)
val AzulNoche = Color(0xFF0E1330)
val AzulNocheSuperficie = Color(0xFF1A2147)

/** Degradado del encabezado (morado UNAB hacia morado profundo). */
val DegradadoMarca = Brush.linearGradient(listOf(Morado, MoradoOscuro, MoradoProfundo))

/** Degradado de las burbujas del usuario. */
val DegradadoBurbuja = Brush.linearGradient(listOf(Morado, MoradoOscuro))

/** Degradado de acento (naranja) para insignias y botones destacados. */
val DegradadoNaranja = Brush.linearGradient(listOf(NaranjaClaro, Naranja))

private val Claro = lightColorScheme(
    primary = Morado,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFF0DBFF),
    onPrimaryContainer = Color(0xFF2C0050),
    secondary = Naranja,
    onSecondary = Color(0xFF1B1000),
    secondaryContainer = Color(0xFFFFE9C7),
    onSecondaryContainer = Color(0xFF3A2200),
    tertiary = Cian,
    onTertiary = Color.White,
    tertiaryContainer = Color(0xFFD5F4FC),
    onTertiaryContainer = Color(0xFF00384A),
    background = Color(0xFFF7F4FC),
    onBackground = Color(0xFF1C1626),
    surface = Color.White,
    onSurface = Color(0xFF1C1626),
    surfaceVariant = Color(0xFFF1EAF8),
    onSurfaceVariant = Color(0xFF5D5470),
    outline = Color(0xFFD9CFE6),
    outlineVariant = Color(0xFFEAE3F2),
    error = Rojo,
)

private val Oscuro = darkColorScheme(
    primary = Color(0xFFD7A8FF),
    onPrimary = Color(0xFF3F0073),
    primaryContainer = Morado,
    onPrimaryContainer = Color.White,
    secondary = Naranja,
    onSecondary = Color(0xFF1B1000),
    secondaryContainer = Color(0xFF5A3600),
    onSecondaryContainer = Color(0xFFFFE2B8),
    tertiary = Color(0xFF7FDBF5),
    onTertiary = Color(0xFF00384A),
    tertiaryContainer = Color(0xFF004E66),
    onTertiaryContainer = Color(0xFFD5F4FC),
    background = AzulNoche,
    onBackground = Color(0xFFE8E6F5),
    surface = AzulNocheSuperficie,
    onSurface = Color(0xFFE8E6F5),
    surfaceVariant = Color(0xFF262E5C),
    onSurfaceVariant = Color(0xFFC9C6DE),
    outline = Color(0xFF3A4378),
    outlineVariant = Color(0xFF2C3466),
    error = Color(0xFFFF8A8E),
)

private val Base = Typography()
private val Tipografia = Typography(
    headlineMedium = Base.headlineMedium.copy(fontWeight = FontWeight.Bold, letterSpacing = (-0.5).sp),
    headlineSmall = Base.headlineSmall.copy(fontWeight = FontWeight.Bold),
    titleLarge = Base.titleLarge.copy(fontWeight = FontWeight.Bold),
    titleMedium = Base.titleMedium.copy(fontWeight = FontWeight.SemiBold),
    titleSmall = Base.titleSmall.copy(fontWeight = FontWeight.SemiBold),
    bodyLarge = Base.bodyLarge.copy(lineHeight = 24.sp),
    bodyMedium = Base.bodyMedium.copy(lineHeight = 21.sp),
    labelLarge = Base.labelLarge.copy(fontWeight = FontWeight.SemiBold),
    labelSmall = TextStyle(fontSize = 11.sp, fontWeight = FontWeight.SemiBold, letterSpacing = 0.3.sp),
)

private val Formas = Shapes(
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(18.dp),
    large = RoundedCornerShape(24.dp),
)

@Composable
fun AsistenteTheme(oscuro: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (oscuro) Oscuro else Claro, typography = Tipografia, shapes = Formas, content = content)
}
