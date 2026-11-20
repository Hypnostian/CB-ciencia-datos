package co.edu.unab.cbdatos.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import co.edu.unab.cbdatos.BuildConfig
import java.io.IOException
import java.util.UUID
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.serialization.encodeToString

/** Un session_id por estudiante: la memoria de n8n se conserva entre aperturas de la app. */
interface SessionStore {
    suspend fun sessionId(codigo: String): String
    suspend fun nuevaSesion(codigo: String): String

    /** Conversación visible guardada (JSON) del estudiante, o null si no hay. */
    suspend fun leerHistorial(codigo: String): String? = null

    /** Guarda la conversación visible; null o vacío la borra. */
    suspend fun guardarHistorial(codigo: String, json: String?) {}
}

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "ajustes")

/** Ajustes persistentes en DataStore. Los valores por defecto del webhook vienen de BuildConfig (local.properties) si existen. */
class SettingsStore(context: Context) : SessionStore, AlmacenSesion {
    private val store = context.applicationContext.dataStore

    private val datos: Flow<Preferences> = store.data.catch { e ->
        if (e is IOException) emit(emptyPreferences()) else throw e
    }

    val webhookUrl: Flow<String> = datos.map { it[KEY_URL] ?: BuildConfig.DEFAULT_WEBHOOK_URL }
    val chatToken: Flow<String> = datos.map { it[KEY_TOKEN] ?: BuildConfig.DEFAULT_CHAT_TOKEN }
    override val codigoEstudiante: Flow<String?> = datos.map { it[KEY_CODIGO] }
    override val perfil: Flow<PerfilEstudiante?> = datos.map { prefs ->
        prefs[KEY_PERFIL]?.let { runCatching { ChatJson.decodeFromString<PerfilEstudiante>(it) }.getOrNull() }
    }
    val temaOscuro: Flow<Boolean> = datos.map { it[KEY_OSCURO] ?: false }

    suspend fun config(): WebhookConfig = WebhookConfig(webhookUrl.first(), chatToken.first())

    suspend fun guardarWebhook(url: String, token: String) {
        store.edit {
            it[KEY_URL] = url.trim()
            it[KEY_TOKEN] = token.trim()
        }
    }

    override suspend fun guardarSesion(codigo: String, perfil: PerfilEstudiante) {
        store.edit {
            it[KEY_CODIGO] = codigo
            it[KEY_PERFIL] = ChatJson.encodeToString(perfil)
        }
    }

    override suspend fun guardarPerfil(perfil: PerfilEstudiante) {
        store.edit { it[KEY_PERFIL] = ChatJson.encodeToString(perfil) }
    }

    override suspend fun cerrarSesion() {
        store.edit {
            it.remove(KEY_CODIGO)
            it.remove(KEY_PERFIL)
        }
    }

    suspend fun guardarTemaOscuro(oscuro: Boolean) {
        store.edit { it[KEY_OSCURO] = oscuro }
    }

    override suspend fun sessionId(codigo: String): String {
        val key = stringPreferencesKey("session_$codigo")
        datos.first()[key]?.let { return it }
        return nuevaSesion(codigo)
    }

    override suspend fun nuevaSesion(codigo: String): String {
        val nuevo = UUID.randomUUID().toString()
        store.edit { it[stringPreferencesKey("session_$codigo")] = nuevo }
        return nuevo
    }

    override suspend fun leerHistorial(codigo: String): String? =
        datos.first()[stringPreferencesKey("historial_$codigo")]

    override suspend fun guardarHistorial(codigo: String, json: String?) {
        val key = stringPreferencesKey("historial_$codigo")
        store.edit { if (json.isNullOrEmpty() || json == "[]") it.remove(key) else it[key] = json }
    }

    private companion object {
        val KEY_URL = stringPreferencesKey("webhook_url")
        val KEY_TOKEN = stringPreferencesKey("chat_token")
        val KEY_CODIGO = stringPreferencesKey("codigo_estudiante")
        val KEY_PERFIL = stringPreferencesKey("perfil_estudiante")
        val KEY_OSCURO = booleanPreferencesKey("tema_oscuro")
    }
}
