package co.edu.unab.cbdatos.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import co.edu.unab.cbdatos.data.Noticia
import co.edu.unab.cbdatos.data.NoticiaFormato
import co.edu.unab.cbdatos.ui.NoticiasUiState
import co.edu.unab.cbdatos.ui.theme.Cian
import co.edu.unab.cbdatos.ui.theme.DegradadoMarca
import co.edu.unab.cbdatos.ui.theme.Morado
import co.edu.unab.cbdatos.ui.theme.Naranja
import co.edu.unab.cbdatos.ui.theme.Verde

/** Color de cada categoría de noticia. */
fun colorCategoria(categoria: String): Color = when (categoria.trim().lowercase()) {
    "educación", "educacion" -> Cian
    "tecnología", "tecnologia" -> Morado
    "ingeniería de sistemas", "ingenieria de sistemas" -> Naranja
    "vida unab" -> Verde
    else -> Color(0xFF8E8A99)
}

/** Pantalla "Noticias del día": noticias del scraper con categoría, fuente y fecha; tocar una abre la fuente. */
@Composable
fun NoticiasScreen(
    estado: NoticiasUiState,
    onActualizar: () -> Unit,
    onCategoria: (String) -> Unit,
    onVolver: () -> Unit,
) {
    val uri = LocalUriHandler.current
    val datos = estado.datos
    val categorias = listOf(NoticiaFormato.TODAS) + (datos?.categorias ?: emptyList())
    val lista = NoticiaFormato.filtrar(datos?.noticias.orEmpty(), estado.categoria)

    Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        CabeceraNoticias(estado, onActualizar, onVolver)
        if (datos != null) {
            LazyRow(
                contentPadding = PaddingValues(horizontal = 14.dp, vertical = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(categorias) { c ->
                    val elegida = c == estado.categoria
                    val color = if (c == NoticiaFormato.TODAS) MaterialTheme.colorScheme.primary else colorCategoria(c)
                    Text(
                        c,
                        style = MaterialTheme.typography.labelLarge,
                        color = if (elegida) Color.White else color,
                        modifier = Modifier
                            .clip(RoundedCornerShape(50))
                            .background(if (elegida) color else color.copy(alpha = 0.12f))
                            .clickable { onCategoria(c) }
                            .padding(horizontal = 14.dp, vertical = 8.dp),
                    )
                }
            }
        }
        when {
            datos == null && estado.cargando -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
            datos == null -> ErrorNoticias(estado.error ?: "No se pudieron cargar las noticias.", onActualizar)
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(start = 14.dp, end = 14.dp, bottom = 24.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                if (estado.error != null) item { ErrorNoticias(estado.error, onActualizar) }
                if (lista.isEmpty()) {
                    item {
                        Text("No hay noticias de esta categoría por ahora.", style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(8.dp))
                    }
                }
                items(lista, key = { it.url }) { n ->
                    TarjetaNoticia(n) {
                        if (n.url.startsWith("http")) {
                            try {
                                uri.openUri(n.url)
                            } catch (_: Exception) {
                                // Sin navegador disponible: se ignora
                            }
                        }
                    }
                }
                item {
                    Text(
                        "Se recogen solas cada 6 horas de unab.edu.co, El Tiempo y Google Noticias. Toca una noticia para leerla en su fuente.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 4.dp).navigationBarsPadding(),
                    )
                }
            }
        }
    }
}

@Composable
private fun CabeceraNoticias(estado: NoticiasUiState, onActualizar: () -> Unit, onVolver: () -> Unit) {
    val datos = estado.datos
    Box(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(bottomStart = 32.dp, bottomEnd = 32.dp))
            .background(DegradadoMarca)
            .statusBarsPadding()
            .padding(start = 8.dp, end = 8.dp, top = 4.dp, bottom = 20.dp),
    ) {
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onVolver) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Volver", tint = Color.White) }
                Text("Noticias del día", style = MaterialTheme.typography.titleMedium, color = Color.White, modifier = Modifier.weight(1f))
                if (estado.cargando) {
                    CircularProgressIndicator(Modifier.padding(end = 14.dp).size(22.dp), strokeWidth = 2.dp, color = Color.White)
                } else {
                    IconButton(onClick = onActualizar) { Icon(Icons.Filled.Refresh, contentDescription = "Actualizar", tint = Color.White) }
                }
            }
            Row(Modifier.padding(start = 16.dp, end = 16.dp, top = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(
                    Modifier.size(54.dp).clip(RoundedCornerShape(18.dp)).background(Color.White.copy(alpha = 0.18f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(Icons.Filled.Notifications, contentDescription = null, tint = Color.White, modifier = Modifier.size(30.dp))
                }
                Column(Modifier.padding(start = 14.dp)) {
                    Text(
                        datos?.let { NoticiaFormato.encabezado(it.fechaConsulta) } ?: "Cargando…",
                        style = MaterialTheme.typography.titleLarge,
                        color = Color.White,
                    )
                    Text(
                        datos?.let { "${it.deHoy} de hoy en educación, tecnología e ingeniería de sistemas" }
                            ?: "Educación, tecnología e ingeniería de sistemas",
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color.White.copy(alpha = 0.85f),
                    )
                }
            }
        }
    }
}

@Composable
private fun TarjetaNoticia(n: Noticia, onAbrir: () -> Unit) {
    val color = colorCategoria(n.categoria)
    Surface(
        modifier = Modifier.fillMaxWidth().clip(MaterialTheme.shapes.large).clickable(onClick = onAbrir),
        shape = MaterialTheme.shapes.large,
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 2.dp,
        border = BorderStroke(1.dp, if (n.esHoy) color.copy(alpha = 0.45f) else MaterialTheme.colorScheme.outlineVariant),
    ) {
        Row(Modifier.height(IntrinsicSize.Min)) {
            Box(Modifier.width(5.dp).fillMaxHeight().background(color))
            Column(Modifier.padding(start = 14.dp, end = 14.dp, top = 14.dp, bottom = 12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Pildora(n.categoria, color)
                    if (n.esHoy) Pildora("HOY", Naranja, solida = true)
                    Spacer(Modifier.weight(1f))
                    Icon(Icons.Filled.DateRange, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(14.dp))
                    Text(NoticiaFormato.fecha(n.fecha), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Text(n.titulo, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold, maxLines = 3, overflow = TextOverflow.Ellipsis)
                if (n.resumen.isNotBlank()) {
                    Text(n.resumen, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 3, overflow = TextOverflow.Ellipsis)
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Filled.Info, contentDescription = null, tint = color, modifier = Modifier.size(15.dp))
                    Text(
                        "Fuente: " + NoticiaFormato.medio(n.fuente) + (NoticiaFormato.via(n.fuente)?.let { ", vía $it" } ?: ""),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.padding(start = 6.dp).weight(1f),
                    )
                    Text("Leer", style = MaterialTheme.typography.labelMedium, color = color)
                    Icon(Icons.Filled.KeyboardArrowRight, contentDescription = null, tint = color, modifier = Modifier.size(18.dp))
                }
            }
        }
    }
}

@Composable
private fun ErrorNoticias(mensaje: String, onReintentar: () -> Unit) {
    Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Surface(shape = MaterialTheme.shapes.medium, color = MaterialTheme.colorScheme.errorContainer, modifier = Modifier.fillMaxWidth()) {
            Text(mensaje, color = MaterialTheme.colorScheme.onErrorContainer, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(14.dp))
        }
        OutlinedButton(onClick = onReintentar, shape = RoundedCornerShape(16.dp)) {
            Icon(Icons.Filled.Refresh, contentDescription = null, tint = Morado, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text("Reintentar")
        }
    }
}
