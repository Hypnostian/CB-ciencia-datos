package co.edu.unab.cbdatos.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    urlActual: String,
    tokenActual: String,
    temaOscuro: Boolean,
    codigo: String?,
    onGuardar: (url: String, token: String) -> Unit,
    onTema: (Boolean) -> Unit,
    onCerrarSesion: () -> Unit,
    onVolver: () -> Unit,
) {
    var url by rememberSaveable(urlActual) { mutableStateOf(urlActual) }
    var token by rememberSaveable(tokenActual) { mutableStateOf(tokenActual) }
    var verToken by rememberSaveable { mutableStateOf(false) }
    var guardado by rememberSaveable { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Ajustes") },
                navigationIcon = { TextButton(onClick = onVolver) { Text("Volver") } },
            )
        },
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text("Conexión con n8n", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
            Text(
                "Pega la URL del webhook de producción y el token compartido. Se guardan solo en este dispositivo.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            OutlinedTextField(
                value = url,
                onValueChange = { url = it; guardado = false },
                label = { Text("URL del webhook") },
                placeholder = { Text("https://.../webhook/unab-chat") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = token,
                onValueChange = { token = it; guardado = false },
                label = { Text("Token del chat (X-Chat-Token)") },
                singleLine = true,
                visualTransformation = if (verToken) VisualTransformation.None else PasswordVisualTransformation(),
                trailingIcon = { TextButton(onClick = { verToken = !verToken }) { Text(if (verToken) "Ocultar" else "Ver") } },
                modifier = Modifier.fillMaxWidth(),
            )
            Button(onClick = { onGuardar(url, token); guardado = true }, modifier = Modifier.fillMaxWidth()) { Text("Guardar") }
            if (guardado) Text("Guardado.", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.bodySmall)

            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Tema oscuro (azul noche)")
                Switch(checked = temaOscuro, onCheckedChange = onTema)
            }

            if (!codigo.isNullOrEmpty()) {
                Text("Estudiante actual: $codigo", style = MaterialTheme.typography.bodyMedium)
                OutlinedButton(onClick = onCerrarSesion, modifier = Modifier.fillMaxWidth()) { Text("Cerrar sesión") }
            }
        }
    }
}
