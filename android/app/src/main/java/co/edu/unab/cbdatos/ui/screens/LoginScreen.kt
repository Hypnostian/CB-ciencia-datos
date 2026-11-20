package co.edu.unab.cbdatos.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.SuggestionChip
import androidx.compose.material3.SuggestionChipDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import co.edu.unab.cbdatos.ui.theme.DegradadoMarca
import co.edu.unab.cbdatos.ui.theme.Naranja

/** Aviso de datos sintéticos, visible en el ingreso y en el perfil. */
const val AVISO_SINTETICO = "Los datos de estudiantes, matrículas y notas son sintéticos y se generaron solo para este curso. " +
    "No corresponden a personas reales ni a la plataforma oficial de la universidad."

/** Códigos sintéticos de demostración (perfiles distintos: regular, rezagado, adelantado y primer semestre). */
val CodigosDemo = listOf("U00100001", "U00100002", "U00100003", "U00100004")

/** Pantalla de ingreso: pide el código de estudiante sintético. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun LoginScreen(
    ingresando: Boolean,
    error: String?,
    onIngresar: (String) -> Unit,
    onCodigoCambiado: () -> Unit,
    onAjustes: () -> Unit,
) {
    var codigo by rememberSaveable { mutableStateOf("") }

    fun enviar() {
        if (!ingresando) onIngresar(codigo.trim().uppercase())
    }

    Column(
        Modifier
            .fillMaxSize()
            .imePadding()
            .verticalScroll(rememberScrollState()),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        // Encabezado con el degradado de la marca
        Box(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(bottomStart = 40.dp, bottomEnd = 40.dp))
                .background(DegradadoMarca)
                .statusBarsPadding()
                .padding(start = 24.dp, end = 24.dp, top = 36.dp, bottom = 72.dp),
            contentAlignment = Alignment.Center,
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Box(
                    Modifier.size(116.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.16f)),
                    contentAlignment = Alignment.Center,
                ) { LogoAsistente(92.dp) }
                Spacer(Modifier.height(18.dp))
                Text("Asistente Académico UNAB", style = MaterialTheme.typography.headlineSmall, color = Color.White, textAlign = TextAlign.Center)
                Spacer(Modifier.height(6.dp))
                Text(
                    "Tu plan de estudios, competencias digitales, horas libres, calendario y noticias en un solo chat",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.White.copy(alpha = 0.85f),
                    textAlign = TextAlign.Center,
                )
                Spacer(Modifier.height(12.dp))
                Pildora("Proyecto de Ciencia de Datos", Naranja, solida = true)
            }
        }

        // Tarjeta de ingreso que se monta sobre el encabezado
        Box(Modifier.padding(horizontal = 20.dp).offset(y = (-44).dp)) {
            TarjetaSuave {
                Text("Ingresa con tu código", style = MaterialTheme.typography.titleLarge)
                Text(
                    "Usa un código sintético con el formato U00 seguido de 6 dígitos.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                OutlinedTextField(
                    value = codigo,
                    onValueChange = { codigo = it.take(9); onCodigoCambiado() },
                    label = { Text("Código de estudiante") },
                    placeholder = { Text("U00123456") },
                    leadingIcon = { Icon(Icons.Filled.Person, contentDescription = null) },
                    singleLine = true,
                    enabled = !ingresando,
                    isError = error != null,
                    supportingText = { Text(error ?: "U00 seguido de 6 dígitos") },
                    shape = RoundedCornerShape(16.dp),
                    colors = OutlinedTextFieldDefaults.colors(unfocusedBorderColor = MaterialTheme.colorScheme.outline),
                    keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Characters, imeAction = ImeAction.Done),
                    keyboardActions = KeyboardActions(onDone = { enviar() }),
                    modifier = Modifier.fillMaxWidth(),
                )
                Button(
                    onClick = { enviar() },
                    enabled = !ingresando,
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                    modifier = Modifier.fillMaxWidth().height(54.dp),
                ) {
                    if (ingresando) {
                        CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.onPrimary)
                        Spacer(Modifier.width(12.dp))
                        Text("Ingresando")
                    } else {
                        Text("Ingresar")
                        Spacer(Modifier.width(8.dp))
                        Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = null, modifier = Modifier.size(20.dp))
                    }
                }
                Text("Códigos de demostración", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    CodigosDemo.forEach { c ->
                        SuggestionChip(
                            onClick = { codigo = c; onCodigoCambiado() },
                            label = { Text(c) },
                            enabled = !ingresando,
                            shape = RoundedCornerShape(50),
                            colors = SuggestionChipDefaults.suggestionChipColors(
                                containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.55f),
                                labelColor = MaterialTheme.colorScheme.onPrimaryContainer,
                            ),
                        )
                    }
                }
            }
        }

        Column(
            Modifier.padding(horizontal = 20.dp).offset(y = (-28).dp).navigationBarsPadding(),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Row(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(18.dp))
                    .background(MaterialTheme.colorScheme.secondaryContainer)
                    .padding(14.dp),
                verticalAlignment = Alignment.Top,
            ) {
                Icon(Icons.Filled.Info, contentDescription = null, tint = Naranja, modifier = Modifier.size(20.dp))
                Text(
                    AVISO_SINTETICO,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSecondaryContainer,
                    modifier = Modifier.padding(start = 10.dp),
                )
            }
            Spacer(Modifier.height(6.dp))
            TextButton(onClick = onAjustes) {
                Icon(Icons.Filled.Settings, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(6.dp))
                Text("Ajustes del webhook")
            }
        }
    }
}
