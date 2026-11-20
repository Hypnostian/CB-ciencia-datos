package co.edu.unab.cbdatos.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.IntrinsicSize
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ExitToApp
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import co.edu.unab.cbdatos.data.AvanceAcademico
import co.edu.unab.cbdatos.data.CompetenciasDigitales
import co.edu.unab.cbdatos.data.CursoHorario
import co.edu.unab.cbdatos.data.HorasLibres
import co.edu.unab.cbdatos.data.PerfilEstudiante
import co.edu.unab.cbdatos.data.PerfilFormato
import co.edu.unab.cbdatos.ui.theme.Cian
import co.edu.unab.cbdatos.ui.theme.DegradadoMarca
import co.edu.unab.cbdatos.ui.theme.Morado
import co.edu.unab.cbdatos.ui.theme.Naranja
import co.edu.unab.cbdatos.ui.theme.Rojo
import co.edu.unab.cbdatos.ui.theme.Verde

/** Pantalla "Mi perfil y horario": datos del estudiante, avance, requisitos de grado y cursos del periodo actual. */
@Composable
fun PerfilScreen(
    perfil: PerfilEstudiante?,
    actualizando: Boolean,
    error: String?,
    onActualizar: () -> Unit,
    onCerrarSesion: () -> Unit,
    onVolver: () -> Unit,
) {
    Column(
        Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .verticalScroll(rememberScrollState()),
    ) {
        Cabecera(perfil, actualizando, onActualizar, onVolver)
        Column(
            Modifier.padding(horizontal = 16.dp, vertical = 16.dp).navigationBarsPadding(),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            if (error != null) {
                Surface(shape = MaterialTheme.shapes.medium, color = MaterialTheme.colorScheme.errorContainer, modifier = Modifier.fillMaxWidth()) {
                    Text(error, color = MaterialTheme.colorScheme.onErrorContainer, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(14.dp))
                }
            }
            if (perfil == null) {
                Text("Aún no hay datos del perfil. Pulsa actualizar para cargarlos.", style = MaterialTheme.typography.bodyMedium)
            } else {
                perfil.avance?.let { Avance(it) }
                perfil.competenciasDigitales?.let { Competencias(it) }
                perfil.horasLibres?.let { Horas(it) }
                Horario(perfil)
                DatosPersonales(perfil)
            }
            Row(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(18.dp))
                    .background(MaterialTheme.colorScheme.secondaryContainer)
                    .padding(14.dp),
            ) {
                Icon(Icons.Filled.Info, contentDescription = null, tint = Naranja, modifier = Modifier.size(20.dp))
                Text(AVISO_SINTETICO, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSecondaryContainer,
                    modifier = Modifier.padding(start = 10.dp))
            }
            OutlinedButton(
                onClick = onCerrarSesion,
                shape = RoundedCornerShape(16.dp),
                border = BorderStroke(1.dp, Rojo.copy(alpha = 0.5f)),
                modifier = Modifier.fillMaxWidth().height(52.dp),
            ) {
                Icon(Icons.AutoMirrored.Filled.ExitToApp, contentDescription = null, tint = Rojo, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text("Cerrar sesión", color = Rojo)
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Cabecera(perfil: PerfilEstudiante?, actualizando: Boolean, onActualizar: () -> Unit, onVolver: () -> Unit) {
    Box(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(bottomStart = 32.dp, bottomEnd = 32.dp))
            .background(DegradadoMarca)
            .statusBarsPadding()
            .padding(start = 8.dp, end = 8.dp, top = 4.dp, bottom = 24.dp),
    ) {
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onVolver) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Volver", tint = Color.White) }
                Text("Mi perfil y horario", style = MaterialTheme.typography.titleMedium, color = Color.White, modifier = Modifier.weight(1f))
                if (actualizando) {
                    CircularProgressIndicator(Modifier.padding(end = 14.dp).size(22.dp), strokeWidth = 2.dp, color = Color.White)
                } else {
                    IconButton(onClick = onActualizar) { Icon(Icons.Filled.Refresh, contentDescription = "Actualizar", tint = Color.White) }
                }
            }
            if (perfil != null) {
                Row(Modifier.padding(start = 12.dp, end = 12.dp, top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                    AvatarIniciales(PerfilFormato.iniciales(perfil), 72.dp)
                    Column(Modifier.padding(start = 16.dp)) {
                        Text(perfil.nombre, style = MaterialTheme.typography.titleLarge, color = Color.White)
                        Text(perfil.programa.ifBlank { perfil.codigo }, style = MaterialTheme.typography.bodyMedium, color = Color.White.copy(alpha = 0.85f))
                        Spacer(Modifier.height(8.dp))
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            perfil.semestreActual?.let { EtiquetaClara("Semestre $it") }
                            if (perfil.periodoActual.isNotBlank()) EtiquetaClara("Periodo ${perfil.periodoActual}")
                            if (perfil.estado.isNotBlank()) EtiquetaClara(perfil.estado.replaceFirstChar { it.uppercase() })
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun EtiquetaClara(texto: String) {
    Text(
        texto,
        style = MaterialTheme.typography.labelSmall,
        color = Color.White,
        modifier = Modifier.clip(RoundedCornerShape(50)).background(Color.White.copy(alpha = 0.18f)).padding(horizontal = 10.dp, vertical = 4.dp),
    )
}

@Composable
private fun Avance(a: AvanceAcademico) {
    val porcentaje = PerfilFormato.porcentaje(a)
    TarjetaSuave {
        TituloSeccion("Avance del plan de estudios", Icons.Filled.Star, Morado)
        Row(verticalAlignment = Alignment.CenterVertically) {
            AnilloProgreso((porcentaje / 100.0).toFloat(), Morado, tamano = 104.dp, grosor = 11.dp) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(PerfilFormato.porcentajeTexto(a), style = MaterialTheme.typography.titleLarge, color = Morado)
                    Text("avance", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            Column(Modifier.padding(start = 18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Cifra("${a.creditosAprobados} / ${a.creditosTotales}", "créditos aprobados")
                if (a.cursosPlan > 0) Cifra("${a.cursosAprobados} / ${a.cursosPlan}", "cursos del plan")
            }
        }
    }
}

@Composable
private fun Cifra(valor: String, etiqueta: String) {
    Column {
        Text(valor, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Text(etiqueta, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

/** Requisito Competencias Digitales R2025, con el mismo orden de pilares del portal del estudiante. */
@Composable
private fun Competencias(c: CompetenciasDigitales) {
    TarjetaSuave {
        TituloSeccion("Competencias digitales", Icons.Filled.CheckCircle, Verde) {
            Pildora(if (c.cumplido) "Cumplido" else "${c.totalAprobadas} de ${c.totalPilares}", if (c.cumplido) Verde else Naranja, solida = c.cumplido)
        }
        Text(
            c.requisito + (c.fechaPrueba?.let { ". Prueba presentada el ${PerfilFormato.fechaLarga(it)}" } ?: ""),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        c.competencias.forEach { item ->
            val color = colorEstado(item.aprobada)
            Row(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(14.dp))
                    .background(color.copy(alpha = 0.07f))
                    .padding(horizontal = 12.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(Modifier.size(28.dp).clip(CircleShape).background(color), contentAlignment = Alignment.Center) {
                    Icon(if (item.aprobada) Icons.Filled.CheckCircle else Icons.Filled.Close, contentDescription = null,
                        tint = Color.White, modifier = Modifier.size(18.dp))
                }
                Column(Modifier.padding(start = 12.dp).weight(1f)) {
                    Text(item.competencia, style = MaterialTheme.typography.titleSmall)
                    Text(
                        if (item.aprobada) item.cumplidaCon ?: "Aprobada en la prueba" else "No aprobada: inscribe el curso de este pilar",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}

@Composable
private fun Horas(h: HorasLibres) {
    val completo = h.completo || h.horasCumplidas >= h.horasRequeridas
    val color = if (completo) Verde else Cian
    TarjetaSuave {
        TituloSeccion("Horas libres", Icons.Filled.Favorite, Rojo) {
            if (completo) Pildora("Completas", Verde, solida = true)
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            AnilloProgreso(PerfilFormato.fraccionHoras(h), color, tamano = 104.dp, grosor = 11.dp) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("${h.horasCumplidas}", style = MaterialTheme.typography.titleLarge, color = color)
                    Text("de ${h.horasRequeridas} h", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            Column(Modifier.padding(start = 18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(PerfilFormato.textoHoras(h), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                Text(
                    if (completo && h.horasCumplidas > h.horasRequeridas) PerfilFormato.horasAdicionales(h)
                    else "Se necesitan ${h.horasRequeridas} horas libres para graduarte.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                LinearProgressIndicator(
                    progress = { PerfilFormato.fraccionHoras(h) },
                    color = color,
                    trackColor = MaterialTheme.colorScheme.surfaceVariant,
                    strokeCap = StrokeCap.Round,
                    modifier = Modifier.fillMaxWidth().height(8.dp),
                )
            }
        }
    }
}

private val ColoresCurso = listOf(Morado, Naranja, Cian, Verde)

@Composable
private fun Horario(p: PerfilEstudiante) {
    TarjetaSuave {
        val total = p.creditosInscritos.takeIf { it > 0 } ?: p.horario.sumOf { it.creditos }
        TituloSeccion("Cursos del periodo actual", Icons.AutoMirrored.Filled.List, Cian) {
            if (total > 0) Pildora("$total créditos", Cian)
        }
        if (p.horario.isEmpty()) {
            Text("No tienes cursos inscritos en este periodo", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        p.horario.forEachIndexed { i, c -> CursoTarjeta(c, ColoresCurso[i % ColoresCurso.size]) }
    }
}

@Composable
private fun CursoTarjeta(c: CursoHorario, color: Color) {
    Row(
        Modifier
            .fillMaxWidth()
            .height(IntrinsicSize.Min)
            .clip(RoundedCornerShape(14.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)),
    ) {
        Box(Modifier.width(5.dp).fillMaxHeight().background(color))
        Column(Modifier.padding(12.dp).weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(c.curso.ifBlank { c.cursoCodigo }, style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
                if (c.creditos > 0) Pildora("${c.creditos} cr", color)
            }
            val ids = listOf(c.cursoCodigo, c.nrc.takeIf { it.isNotBlank() }?.let { "NRC $it" }).filterNotNull().filter { it.isNotBlank() }
            if (ids.isNotEmpty()) Text(ids.joinToString("  |  "), style = MaterialTheme.typography.labelSmall, color = color)
            if (c.horario.isNotBlank()) Detalle(Icons.Filled.DateRange, c.horario)
            if (c.profesor.isNotBlank()) Detalle(Icons.Filled.Person, c.profesor)
        }
    }
}

@Composable
private fun Detalle(icono: androidx.compose.ui.graphics.vector.ImageVector, texto: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(icono, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(15.dp))
        Text(texto, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(start = 6.dp))
    }
}

@Composable
private fun DatosPersonales(p: PerfilEstudiante) {
    TarjetaSuave {
        TituloSeccion("Datos del estudiante", Icons.Filled.Person, Naranja)
        Dato("Código", p.codigo)
        Dato("Programa", p.programa)
        Dato("Correo (demo)", p.correo)
    }
}

@Composable
private fun Dato(etiqueta: String, valor: String) {
    if (valor.isBlank()) return
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(etiqueta, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(valor, style = MaterialTheme.typography.bodyMedium, textAlign = TextAlign.End, modifier = Modifier.padding(start = 12.dp))
    }
}
