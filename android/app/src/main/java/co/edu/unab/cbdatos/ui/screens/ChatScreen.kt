package co.edu.unab.cbdatos.ui.screens

import androidx.compose.ui.text.font.FontWeight
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.MailOutline
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarDuration
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import kotlinx.coroutines.launch
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import co.edu.unab.cbdatos.data.Fuente
import co.edu.unab.cbdatos.data.Intenciones
import co.edu.unab.cbdatos.data.PerfilEstudiante
import co.edu.unab.cbdatos.data.PerfilFormato
import co.edu.unab.cbdatos.ui.Autor
import co.edu.unab.cbdatos.ui.ChatUiState
import co.edu.unab.cbdatos.ui.Markdown
import co.edu.unab.cbdatos.ui.MensajeChat
import co.edu.unab.cbdatos.ui.theme.Cian
import co.edu.unab.cbdatos.ui.theme.DegradadoBurbuja
import co.edu.unab.cbdatos.ui.theme.DegradadoMarca
import co.edu.unab.cbdatos.ui.theme.DegradadoNaranja
import co.edu.unab.cbdatos.ui.theme.Morado
import co.edu.unab.cbdatos.ui.theme.Naranja
import co.edu.unab.cbdatos.ui.theme.Rojo
import co.edu.unab.cbdatos.ui.theme.Verde

/** Pregunta sugerida con su icono y color. */
data class Sugerencia(val texto: String, val icono: ImageVector, val color: Color)

val Sugerencias = listOf(
    Sugerencia("¿Qué cursos debo tomar?", Icons.AutoMirrored.Filled.List, Morado),
    Sugerencia("¿Cómo voy en mi plan de estudios?", Icons.Filled.Star, Naranja),
    Sugerencia("¿Qué competencias digitales me faltan?", Icons.Filled.CheckCircle, Verde),
    Sugerencia("¿Cuántas horas libres llevo?", Icons.Filled.Favorite, Rojo),
    Sugerencia("¿Cuántos semestres me faltan?", Icons.Filled.DateRange, Cian),
    Sugerencia("¿Qué es la insignia de competencias digitales?", Icons.Filled.Info, Morado),
    Sugerencia("¿Cuándo son las inscripciones?", Icons.Filled.Notifications, Naranja),
    Sugerencia("¿Qué noticias de tecnología hay hoy?", Icons.Filled.MailOutline, Cian),
)

/** Textos de las preguntas sugeridas (atajos del chat). */
val PreguntasSugeridas = Sugerencias.map { it.texto }

@Composable
fun ChatScreen(
    codigo: String,
    perfil: PerfilEstudiante?,
    estado: ChatUiState,
    onEnviar: (String) -> Unit,
    onReintentar: () -> Unit,
    onNuevaConversacion: () -> Unit,
    onAjustes: () -> Unit,
    onPerfil: () -> Unit,
    onNoticias: () -> Unit = {},
) {
    var entrada by rememberSaveable { mutableStateOf("") }
    val lista = rememberLazyListState()
    val uriHandler = LocalUriHandler.current

    // Baja al último elemento cuando llega un mensaje, aparece el indicador o un error. La clave incluye el estado
    // "escribiendo": cuando el indicador se reemplaza por la respuesta, el número de elementos no cambia.
    val elementos = estado.mensajes.size + (if (estado.escribiendo) 1 else 0) + (if (estado.error != null) 1 else 0)
    LaunchedEffect(estado.mensajes.size, estado.escribiendo, estado.error) {
        if (elementos > 0) lista.animateScrollToItem(elementos - 1)
    }

    fun enviar(texto: String) {
        if (texto.isBlank() || estado.escribiendo) return
        onEnviar(texto)
        entrada = ""
    }

    val snackbar = remember { SnackbarHostState() }
    val alcance = rememberCoroutineScope()
    var confirmarNueva by rememberSaveable { mutableStateOf(false) }

    fun reiniciar() {
        onNuevaConversacion()
        alcance.launch {
            snackbar.currentSnackbarData?.dismiss()
            snackbar.showSnackbar("Nueva conversación iniciada", duration = SnackbarDuration.Short)
        }
    }

    if (confirmarNueva) {
        AlertDialog(
            onDismissRequest = { confirmarNueva = false },
            title = { Text("Nueva conversación") },
            text = { Text("¿Empezar una conversación nueva? El asistente olvidará lo que hablaron en esta.") },
            confirmButton = { TextButton(onClick = { confirmarNueva = false; reiniciar() }) { Text("Empezar") } },
            dismissButton = { TextButton(onClick = { confirmarNueva = false }) { Text("Cancelar") } },
        )
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            Encabezado(
                codigo, perfil, onPerfil, onNoticias,
                onNuevaConversacion = { if (estado.mensajes.isEmpty()) reiniciar() else confirmarNueva = true },
                onAjustes = onAjustes,
            )
        },
        bottomBar = {
            BarraEntrada(
                texto = entrada,
                onTexto = { entrada = it },
                habilitado = !estado.escribiendo,
                onEnviar = { enviar(entrada) },
            )
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            if (estado.mensajes.isEmpty()) {
                Bienvenida(Modifier.weight(1f), perfil = perfil, onEnviar = ::enviar, onNoticias = onNoticias)
            } else {
                LazyColumn(
                    state = lista,
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    contentPadding = PaddingValues(horizontal = 14.dp, vertical = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp),
                ) {
                    items(estado.mensajes, key = { it.id }) { m ->
                        Burbuja(m, onFuente = { abrir(uriHandler, it) })
                    }
                    if (estado.escribiendo) item { IndicadorEscribiendo() }
                    if (estado.error != null) item { TarjetaError(estado.error, onReintentar) }
                }
                // Atajos también con la conversación en curso
                LazyRow(
                    contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(Sugerencias) { s -> Atajo(s, habilitado = !estado.escribiendo) { enviar(s.texto) } }
                }
            }
            // Si el chat está vacío y hay error (p. ej. falta configurar), se muestra aquí
            if (estado.mensajes.isEmpty() && estado.error != null) {
                Box(Modifier.padding(14.dp)) { TarjetaError(estado.error, onReintentar) }
            }
        }
    }
}

@Composable
private fun Encabezado(
    codigo: String,
    perfil: PerfilEstudiante?,
    onPerfil: () -> Unit,
    onNoticias: () -> Unit,
    onNuevaConversacion: () -> Unit,
    onAjustes: () -> Unit,
) {
    var menu by remember { mutableStateOf(false) }
    Box(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(bottomStart = 26.dp, bottomEnd = 26.dp))
            .background(DegradadoMarca)
            .statusBarsPadding()
            .padding(start = 16.dp, end = 4.dp, top = 10.dp, bottom = 14.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Row(
                Modifier.weight(1f).clip(RoundedCornerShape(16.dp)).clickable(onClick = onPerfil).padding(4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(contentAlignment = Alignment.BottomEnd) {
                    Box(Modifier.size(46.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.18f)), contentAlignment = Alignment.Center) {
                        LogoAsistente(40.dp)
                    }
                    Box(Modifier.size(12.dp).clip(CircleShape).background(Color.White).padding(2.dp).clip(CircleShape).background(Verde))
                }
                Column(Modifier.padding(start = 12.dp)) {
                    Text(
                        perfil?.let { PerfilFormato.nombreEncabezado(it) } ?: "Asistente UNAB",
                        style = MaterialTheme.typography.titleMedium,
                        color = Color.White,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        perfil?.let { PerfilFormato.subtitulo(it) } ?: codigo,
                        style = MaterialTheme.typography.bodySmall,
                        color = Color.White.copy(alpha = 0.8f),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            IconButton(onClick = onNuevaConversacion) {
                Icon(Icons.Filled.Edit, contentDescription = "Nueva conversación", tint = Color.White)
            }
            Box {
                IconButton(onClick = { menu = true }) {
                    Icon(Icons.Filled.MoreVert, contentDescription = "Más opciones", tint = Color.White)
                }
                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                    DropdownMenuItem(
                        text = { Text("Mi perfil y horario") },
                        leadingIcon = { Icon(Icons.Filled.Person, contentDescription = null) },
                        onClick = { menu = false; onPerfil() },
                    )
                    DropdownMenuItem(
                        text = { Text("Noticias del día") },
                        leadingIcon = { Icon(Icons.Filled.Notifications, contentDescription = null) },
                        onClick = { menu = false; onNoticias() },
                    )
                    DropdownMenuItem(
                        text = { Text("Ajustes") },
                        leadingIcon = { Icon(Icons.Filled.Settings, contentDescription = null) },
                        onClick = { menu = false; onAjustes() },
                    )
                }
            }
        }
    }
}

@Composable
private fun BarraEntrada(texto: String, onTexto: (String) -> Unit, habilitado: Boolean, onEnviar: () -> Unit) {
    Surface(color = MaterialTheme.colorScheme.background, modifier = Modifier.imePadding()) {
        Row(
            Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            TextField(
                value = texto,
                onValueChange = onTexto,
                placeholder = { Text("Escribe tu pregunta…") },
                maxLines = 4,
                shape = RoundedCornerShape(26.dp),
                colors = TextFieldDefaults.colors(
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent,
                    disabledIndicatorColor = Color.Transparent,
                    focusedContainerColor = MaterialTheme.colorScheme.surface,
                    unfocusedContainerColor = MaterialTheme.colorScheme.surface,
                ),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { onEnviar() }),
                modifier = Modifier
                    .weight(1f)
                    .heightIn(min = 52.dp)
                    .clip(RoundedCornerShape(26.dp))
                    .background(MaterialTheme.colorScheme.outlineVariant)
                    .padding(1.dp),
            )
            val activo = texto.isNotBlank() && habilitado
            Box(
                Modifier
                    .padding(start = 10.dp)
                    .size(52.dp)
                    .clip(CircleShape)
                    .background(if (activo) DegradadoNaranja else DegradadoBurbuja, alpha = if (activo) 1f else 0.35f)
                    .clickable(enabled = activo, onClick = onEnviar),
                contentAlignment = Alignment.Center,
            ) {
                Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Enviar", tint = Color.White)
            }
        }
    }
}

private fun abrir(handler: androidx.compose.ui.platform.UriHandler, f: Fuente) {
    val url = f.url.trim()
    if (!url.startsWith("http://") && !url.startsWith("https://")) return
    try {
        handler.openUri(url)
    } catch (_: Exception) {
        // Sin navegador disponible o enlace inválido: se ignora
    }
}

@Composable
private fun Bienvenida(modifier: Modifier, perfil: PerfilEstudiante?, onEnviar: (String) -> Unit, onNoticias: () -> Unit) {
    val nombre = perfil?.let { PerfilFormato.primerNombre(it) }.orEmpty()
    LazyColumn(
        modifier.fillMaxWidth(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Surface(shape = MaterialTheme.shapes.large, color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.6f), modifier = Modifier.fillMaxWidth()) {
                Row(Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text(PerfilFormato.saludo(nombre), style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.onPrimaryContainer)
                        Spacer(Modifier.height(6.dp))
                        Text(
                            "Pregúntame por tu plan de estudios, matrícula, competencias digitales, horas libres, calendario o noticias.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f),
                        )
                    }
                    Spacer(Modifier.width(12.dp))
                    LogoAsistente(64.dp)
                }
            }
        }
        perfil?.let { p -> item { ResumenRapido(p) } }
        item { AccesoNoticias(onNoticias) }
        item {
            Text("Prueba preguntando", style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 4.dp, start = 2.dp))
        }
        items(Sugerencias.chunked(2)) { fila ->
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                fila.forEach { s -> TarjetaSugerencia(s, Modifier.weight(1f)) { onEnviar(s.texto) } }
                if (fila.size == 1) Spacer(Modifier.weight(1f))
            }
        }
    }
}

/** Fila con los tres indicadores del estudiante: avance, competencias digitales y horas libres. */
@Composable
private fun ResumenRapido(p: PerfilEstudiante) {
    val avance = p.avance?.let { PerfilFormato.porcentaje(it) }
    val avanceTexto = p.avance?.let { PerfilFormato.porcentajeTexto(it) }.orEmpty()
    val comp = p.competenciasDigitales
    val horas = p.horasLibres
    if (avance == null && comp == null && horas == null) return
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        if (avance != null) Indicador("Avance", avanceTexto, (avance / 100).toFloat(), Morado, Modifier.weight(1f))
        if (comp != null && comp.totalPilares > 0) {
            Indicador("Competencias", "${comp.totalAprobadas}/${comp.totalPilares}", comp.totalAprobadas.toFloat() / comp.totalPilares,
                if (comp.cumplido) Verde else Naranja, Modifier.weight(1f))
        }
        if (horas != null) {
            Indicador("Horas libres", "${horas.horasCumplidas}", PerfilFormato.fraccionHoras(horas),
                if (horas.completo) Verde else Cian, Modifier.weight(1f))
        }
    }
}

@Composable
private fun Indicador(titulo: String, valor: String, fraccion: Float, color: Color, modifier: Modifier) {
    Surface(
        modifier = modifier,
        shape = MaterialTheme.shapes.medium,
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(Modifier.padding(vertical = 12.dp, horizontal = 8.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            AnilloProgreso(fraccion, color, tamano = 58.dp, grosor = 6.dp) {
                Text(valor, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurface)
            }
            Spacer(Modifier.height(6.dp))
            Text(titulo, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
        }
    }
}

@Composable
private fun TarjetaSugerencia(s: Sugerencia, modifier: Modifier, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        modifier = modifier.heightIn(min = 112.dp),
        shape = MaterialTheme.shapes.medium,
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        shadowElevation = 1.dp,
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            IconoEnCirculo(s.icono, s.color, 38.dp)
            Text(s.texto, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface)
        }
    }
}

@Composable
private fun Atajo(s: Sugerencia, habilitado: Boolean, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        enabled = habilitado,
        shape = RoundedCornerShape(50),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, s.color.copy(alpha = 0.35f)),
    ) {
        Row(Modifier.padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(s.icono, contentDescription = null, tint = s.color, modifier = Modifier.size(16.dp))
            Text(s.texto, style = MaterialTheme.typography.labelLarge, modifier = Modifier.padding(start = 6.dp), maxLines = 1)
        }
    }
}

@Composable
private fun AvatarBot() {
    Box(Modifier.size(32.dp).clip(CircleShape).background(MaterialTheme.colorScheme.primaryContainer), contentAlignment = Alignment.Center) {
        LogoAsistente(28.dp)
    }
}

@Composable
private fun Burbuja(m: MensajeChat, onFuente: (Fuente) -> Unit) {
    val usuario = m.autor == Autor.USUARIO
    val colores = MaterialTheme.colorScheme
    if (usuario) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
            Text(
                m.texto,
                color = Color.White,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier
                    .widthIn(max = 300.dp)
                    .clip(RoundedCornerShape(20.dp, 20.dp, 6.dp, 20.dp))
                    .background(DegradadoBurbuja)
                    .padding(horizontal = 16.dp, vertical = 12.dp),
            )
        }
        return
    }
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
        AvatarBot()
        Surface(
            modifier = Modifier.padding(start = 8.dp).widthIn(max = 310.dp),
            shape = RoundedCornerShape(6.dp, 20.dp, 20.dp, 20.dp),
            color = colores.surface,
            border = BorderStroke(1.dp, colores.outlineVariant),
            shadowElevation = 1.dp,
        ) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (m.intencion != null) {
                    val color = colorIntencion(m.intencion)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.size(8.dp).clip(CircleShape).background(color))
                        Text(
                            Intenciones.etiqueta(m.intencion),
                            style = MaterialTheme.typography.labelSmall,
                            color = color,
                            modifier = Modifier.padding(start = 6.dp),
                        )
                    }
                }
                Text(Markdown.aTexto(m.texto), color = colores.onSurface, style = MaterialTheme.typography.bodyMedium)
                if (m.fuentes.isNotEmpty()) {
                    Box(Modifier.fillMaxWidth().height(1.dp).background(colores.outlineVariant))
                    Text("Fuentes", style = MaterialTheme.typography.labelSmall, color = colores.onSurfaceVariant)
                    m.fuentes.forEach { f ->
                        Row(
                            Modifier
                                .clip(RoundedCornerShape(12.dp))
                                .background(colores.primaryContainer.copy(alpha = 0.45f))
                                .clickable { onFuente(f) }
                                .padding(horizontal = 10.dp, vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Icon(Icons.Filled.Info, contentDescription = null, tint = colores.primary, modifier = Modifier.size(14.dp))
                            Text(
                                f.titulo.ifBlank { f.url },
                                style = MaterialTheme.typography.bodySmall,
                                color = colores.primary,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                                modifier = Modifier.padding(start = 6.dp),
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun IndicadorEscribiendo() {
    val t = rememberInfiniteTransition(label = "escribiendo")
    Row(verticalAlignment = Alignment.CenterVertically) {
        AvatarBot()
        Row(
            Modifier
                .padding(start = 8.dp)
                .clip(RoundedCornerShape(6.dp, 20.dp, 20.dp, 20.dp))
                .background(MaterialTheme.colorScheme.surface)
                .padding(horizontal = 16.dp, vertical = 14.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            listOf(Morado, Naranja, Cian).forEachIndexed { i, color ->
                val alfa by t.animateFloat(
                    initialValue = 0.25f,
                    targetValue = 1f,
                    animationSpec = infiniteRepeatable(tween(600, delayMillis = i * 180), RepeatMode.Reverse),
                    label = "punto$i",
                )
                Box(Modifier.size(9.dp).alpha(alfa).clip(CircleShape).background(color))
            }
        }
    }
}

@Composable
private fun TarjetaError(mensaje: String, onReintentar: () -> Unit) {
    Surface(shape = MaterialTheme.shapes.medium, color = MaterialTheme.colorScheme.errorContainer, modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(mensaje, color = MaterialTheme.colorScheme.onErrorContainer, style = MaterialTheme.typography.bodyMedium)
            TextButton(onClick = onReintentar) {
                Icon(Icons.Filled.Refresh, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(6.dp))
                Text("Reintentar")
            }
        }
    }
}

/** Acceso a la pantalla de noticias del día desde el inicio del chat. */
@Composable
private fun AccesoNoticias(onNoticias: () -> Unit) {
    Surface(
        shape = MaterialTheme.shapes.large,
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 2.dp,
        border = BorderStroke(1.dp, Cian.copy(alpha = 0.4f)),
        modifier = Modifier.fillMaxWidth().clip(MaterialTheme.shapes.large).clickable(onClick = onNoticias),
    ) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            IconoEnCirculo(Icons.Filled.Notifications, Cian, 44.dp)
            Column(Modifier.padding(start = 14.dp).weight(1f)) {
                Text("Noticias del día", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                Text("Educación, tecnología e ingeniería de sistemas, con fuente y fecha",
                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Icon(Icons.Filled.KeyboardArrowRight, contentDescription = null, tint = Cian)
        }
    }
}
