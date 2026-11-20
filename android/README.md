# Asistente Académico UNAB (app Android)

App Android propia del proyecto de Ciencia de Datos (chatbot de apoyo académico con n8n). Es independiente de cualquier otra app: paquete `co.edu.unab.cbdatos`, sin Firebase y sin claves en el código.

## Qué hace
- **Diseño**: colores de la marca UNAB (morado, naranja, cian y verde), encabezados con degradado, tarjetas redondeadas, iconos de Material
  y anillos de progreso animados. Tema oscuro azul noche en Ajustes.
- **Ingreso**: código de estudiante sintético (`^U00\d{6}$`, por ejemplo `U00123456`) y botones con los cuatro códigos de demostración.
  Al ingresar se consulta el perfil al webhook (acción `perfil`); si falla, se queda en la pantalla con el motivo.
- **Perfil y horario**: el encabezado del chat muestra el nombre y "programa, semestre N"; tocarlo (o el menú > Mi perfil y horario) abre la
  pantalla con avatar, avance del plan (anillo), **competencias digitales** (los 5 pilares de la prueba con aprobado o pendiente, como en el
  portal), **horas libres** (anillo con las horas frente a las 96 requeridas), cursos con NRC, horario y profesor, y "Actualizar".
  Al abrir la app se muestra el perfil guardado y se refresca en segundo plano.
- **Chat**: inicio con saludo, tres indicadores (avance, competencias y horas libres) y tarjetas de preguntas sugeridas con icono;
  burbujas con avatar del asistente, indicador "escribiendo", insignia de color por intención, fuentes tocables (abren el navegador),
  atajos con las preguntas sugeridas, reintento ante errores y el botón del lápiz "Nueva conversación" (con confirmación si hay mensajes y aviso al terminar).
- **Noticias del día**: desde el inicio del chat o el menú. Noticias de educación, tecnología, ingeniería de sistemas y vida UNAB con
  categoría, marca HOY, hora de Colombia, resumen y fuente; filtro por categoría; tocar una abre la fuente (acción `noticias`).
- **Ajustes**: URL del webhook y token del chat (se guardan en DataStore), tema oscuro azul noche, cambio de estudiante.
- El `session_id` (UUID) se guarda por estudiante: la memoria de n8n se conserva al cerrar y abrir la app. "Nueva conversación" genera uno nuevo y borra el historial guardado.

## Contrato del webhook
```
POST {URL del webhook}
Headers: Content-Type: application/json, X-Chat-Token: {token}
Body:    {"estudiante_codigo": "U00123456", "session_id": "uuid", "mensaje": "..."}
200:     {"respuesta": "...", "intencion": "general|calendario|cursos|matricula|noticias|fuera_de_tema",
          "fuentes": [{"titulo": "...", "url": "..."}]}
```
Acción de noticias (misma URL y cabecera): `{"accion": "noticias", "estudiante_codigo": "U00123456", "session_id": "uuid"}`
devuelve `{"noticias": {"fecha_consulta", "de_hoy", "categorias", "noticias": [...]}}`.

Acción de perfil (misma URL y cabecera):
```
Body:    {"accion": "perfil", "estudiante_codigo": "U00123456", "session_id": "uuid"}
200:     {"perfil": {"codigo", "nombre", "nombres", "apellidos", "correo", "programa", "semestre_actual", "estado",
          "periodo_actual", "horario": [{"nrc", "curso_codigo", "curso", "creditos", "profesor", "horario"}],
          "creditos_inscritos", "avance": {"creditos_aprobados", "creditos_totales", "porcentaje_avance",
          "cursos_aprobados", "cursos_plan"},
          "competencias_digitales": {"requisito", "fecha_prueba", "competencias": [{"competencia", "estado", "cumplida_con"}],
          "faltantes", "total_aprobadas", "total_pilares", "cumplido"},
          "horas_libres": {"horas_cumplidas", "horas_requeridas", "horas_faltantes", "completo"}, "nuevo"}}
400:     {"error": "..."} o {"respuesta": "..."} (código inválido)
```
Solo `codigo` y `nombre` son obligatorios; el resto es opcional. El perfil se guarda en DataStore (JSON) y "Cerrar sesión" lo borra.

Tiempos: conexión 15 s, lectura 60 s. Errores controlados: sin conexión, tiempo agotado, 401/403 (token), 404, 5xx y JSON inválido.

## Requisitos
- **JDK para Gradle: de 17 a 23.** El plugin de Android (AGP 8.12.3) exige como mínimo JDK 17 y Gradle 8.13 admite hasta JDK 23. El código
  se compila para Java 11 (`compileOptions` y `jvmTarget` en `app/build.gradle.kts`), así que el JDK solo afecta a Gradle. El repositorio fija el
  JDK 23 en `gradle/gradle-daemon-jvm.properties` (`toolchainVersion=23`); si tienes el 17 o el 21, cambia ese número por el tuyo. No uses
  el JDK 25 que trae Android Studio: Gradle 8.13 todavía no lo admite y la sincronización falla.
  En Android Studio: *Settings > Build, Execution, Deployment > Build Tools > Gradle > Gradle JDK* = el JDK elegido (`<RUTA_DEL_JDK>`).
- Android SDK con la plataforma 36.
- `local.properties` con la ruta del SDK (está fuera de git; Android Studio lo crea solo): `sdk.dir=<RUTA_DEL_SDK_DE_ANDROID>`. Ajústala en cada máquina.

## Compilar y probar
```
./gradlew assembleDebug testDebugUnitTest --no-daemon -Pkotlin.compiler.execution.strategy=in-process
```
El APK queda en `app/build/outputs/apk/debug/app-debug.apk`. Instálalo con `adb install -r app/build/outputs/apk/debug/app-debug.apk` o ejecuta la app desde Android Studio.

## Configurar el webhook
Opción A, en la app: **Ajustes** (en la pantalla de ingreso o en el menú "Más" del chat), pega la URL de producción del workflow (`.../webhook/unab-chat`) y el token (`CHAT_TOKEN`), y pulsa Guardar.

Opción B, valores por defecto al compilar (opcional): agrega a `local.properties`
```
N8N_WEBHOOK_URL=https://tu-instancia.app.n8n.cloud/webhook/unab-chat
CHAT_TOKEN=tu-token
```
Lo guardado en Ajustes tiene prioridad. `local.properties` no se versiona. **Ojo:** lo que se compila por esta vía queda dentro del APK (`BuildConfig`). Compila el APK tú mismo con tu `local.properties`, nunca publiques ni compartas un APK hecho con valores reales y, para repartir uno, compílalo sin esas dos claves.

Notas:
- El build de release solo acepta `https`. El build debug admite `http` para un n8n local (en el emulador, `http://10.0.2.2:5678/webhook/unab-chat`).
- Los últimos 40 mensajes de la conversación se guardan por estudiante en DataStore y se restauran al abrir la app, de modo que la pantalla coincida con la memoria del asistente; la memoria de la conversación vive en n8n (por `session_id`).

## Pruebas unitarias
- Serialización JSON de la petición y la respuesta, y manejo de JSON malformado o vacío.
- Validación del código de estudiante.
- Traducción de códigos HTTP a errores.
- ViewModel con repositorio falso: camino feliz, reintento, mensaje en blanco y nueva conversación.
- Perfil: lectura del JSON (completo y mínimo), errores HTTP, formato de encabezado y saludo, ingreso exitoso y fallido, refresco en segundo plano y cierre de sesión.
- Noticias: lectura de la respuesta, errores, fecha en hora de Colombia ("Hoy, 07:58"), medio y agregador, filtro por categoría.
- En total 48 pruebas (`./gradlew testDebugUnitTest`).

## Estructura
```
app/src/main/java/co/edu/unab/cbdatos/
  MainActivity.kt          navegación simple entre ingreso, chat, perfil, noticias y ajustes
  data/                    modelos JSON, repositorio OkHttp, DataStore, validación del código
  ui/                      ChatViewModel, PerfilViewModel, NoticiasViewModel, AppViewModel, tema (morado #8600DD, naranja #F79800)
  ui/screens/              LoginScreen, ChatScreen, PerfilScreen, NoticiasScreen, SettingsScreen, Componentes, Logo
app/src/test/              pruebas unitarias
```
