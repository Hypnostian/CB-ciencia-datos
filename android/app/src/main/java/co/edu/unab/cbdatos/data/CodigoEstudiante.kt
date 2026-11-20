package co.edu.unab.cbdatos.data

/** Validación del código de estudiante sintético: U00 + 6 dígitos (ej. U00123456). */
object CodigoEstudiante {
    private val patron = Regex("^U00\\d{6}$")

    /** Quita espacios y pasa a mayúsculas. */
    fun normalizar(entrada: String): String = entrada.trim().uppercase()

    fun esValido(entrada: String): Boolean = patron.matches(normalizar(entrada))
}
