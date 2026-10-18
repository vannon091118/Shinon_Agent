package com.vannon.shinon

import android.app.Application
import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import java.security.KeyStore

/**
 * ShinonApp — Application-Klasse für die Android-Shell.
 *
 * EINE Aufgabe: den Android Keystore-Wrapper initialisieren. Secrets
 * (API-Keys, Auth-Tokens) werden im App-internen Schlüssel gespeichert,
 * NIE im Build, NIE im Repository, NIE in der URL, NIE in den Logs.
 *
 * Der Keystore schützt die API-Keys, NIE die Auth-Tokens der lokalen
 * DSH-URL (die werden pro Session generiert und nur im WebView-Cache
 * gehalten).
 */
class ShinonApp : Application() {

    lateinit var keystore: ShinonKeystore

    override fun onCreate() {
        super.onCreate()
        keystore = ShinonKeystore(this)
        keystore.initialize()
    }
}

/**
 * ShinonKeystore — Android-Keystore-Wrapper für API-Keys.
 *
 * Sicherheit:
 *   - Secret NIE im Plaintext-Dateisystem.
 *   - Keystore ist nicht exportierbar (no extraction).
 *   - Nur im Speicher als Environment an den Node-Prozess übergeben.
 *
 * MOBILE-PLAN.md §5 W4: „Auth-Secret mit Android Keystore schützen,
 * an den Prozess nur im Speicher als Environment übergeben; niemals
 * in Build-Config, Repo, URL, Logs oder ProcessBuilder-Kommandozeile."
 */
class ShinonKeystore(private val app: Application) {

    private var ks: KeyStore? = null

    fun initialize() {
        val ks = KeyStore.getInstance("AndroidKeyStore")
        ks.load(null)
        this.ks = ks
    }

    /**
     * Erzeugt einen AES-Schlüssel im Android-Keystore (kein Extraction).
     * Der API-Key selbst wird später unter diesem Schlüssel verschlüsselt
     * gespeichert — nie im Klartext.
     * @param keyAlias der Alias im Android-Keystore (z. B. "shinon_agnes")
     * @return true, wenn der Schlüssel erfolgreich erstellt oder existiert
     */
    fun ensureKey(keyAlias: String): Boolean {
        val ks = this.ks ?: return false
        if (ks.containsAlias(keyAlias)) return true
        try {
            val spec = KeyGenParameterSpec.Builder(
                keyAlias,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                // AES-GCM verschlüsselt blockweise ohne Padding. Der frühere
                // Wert PADDING_RSA_OAEP existiert in KeyProperties nicht und
                // wäre für einen AES-Schlüssel auch sachlich falsch; für
                // AES-GCM ist ENCRYPTION_PADDING_NONE korrekt.
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build()
            val keyGen = javax.crypto.KeyGenerator.getInstance("AES", "AndroidKeyStore")
            keyGen.init(spec)
            val key = keyGen.generateKey()
            ks.setKeyEntry(keyAlias, key, null, null)
            return true
        } catch (e: Exception) {
            return false
        }
    }

    /**
     * Prüft, ob der API-Key im Android-Keystore gespeichert ist.
     * (Der echte Wert wird bei Setup eingegeben und unter dem
     * Keystore-Schlüssel verschlüsselt abgelegt; hier nur die
     * Existenzprüfung für die Weiterleitung an den Node-Prozess.)
     */
    fun hasKey(keyAlias: String): Boolean {
        val ks = this.ks ?: return false
        return try {
            ks.containsAlias(keyAlias) && ks.getKey(keyAlias, null) != null
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Alias, unter dem der AGNES-API-Key verschlüsselt liegt.
     * @return der Alias-Name (z. B. "shinon_agnes") oder null
     */
    fun getKeyAliasForProvider(provider: String): String? {
        val alias = "shinon_${provider.lowercase()}"
        return if (hasKey(alias)) alias else null
    }

    // ── B-3-Fix: Secret-Speicherung (SEC-KEY-001/002) ─────────────────
    // Der API-Key-Wert wird AES-256-GCM-verschlüsselt unter dem
    // Keystore-Schlüssel abgelegt. Der Zivillast-Block (ciphertext) wird
    // in der SharedPreferences-Datei unter App-internem Storage abgelegt,
    // NIEMALS im Klartext. Die Initialisation (IV, 12 Bytes) wird dem
    // Ciphertext vorangestellt.
    //
    // Der entschlüsselte Wert erreicht den Node-Prozess ausschließlich
    // als Environment-Variable (ShinonService.startEngine, AGNES_API_KEY)
    // — nie in argv, nie in Logs, nie in die URL.
    // ────────────────────────────────────────────────────────────────

    private val PREFS = "shinon_secrets"

    /**
     * Speichert ein Secret (z. B. AGNES-API-Key) verschlüsselt im
     * App-Storage. Der Klartext-Wert wird nie auf die Festplatte.
     *
     * @param keyAlias der Android-Keystore-Alias (z. B. "shinon_agnes")
     * @param plaintext der Klartext-Wert (wird sofort vergessbar)
     * @return true, wenn gespeichert; false bei Fehlschlag
     */
    fun storeSecret(keyAlias: String, plaintext: String): Boolean {
        val ks = this.ks ?: return false
        if (!ks.containsAlias(keyAlias)) {
            if (!ensureKey(keyAlias)) return false
        }
        val key = try {
            ks.getKey(keyAlias, null) as? SecretKey ?: return false
        } catch (e: Exception) {
            return false
        }

        return try {
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.ENCRYPT_MODE, key)
            val iv = cipher.iv // 12 Bytes, GCM-Standard
            val ciphertext = cipher.doFinal(plaintext.toByteArray(Charsets.UTF_8))
            val blob = Base64.encodeToString(iv + ciphertext, Base64.DEFAULT)
            app.getSharedPreferences(PREFS, app.MODE_PRIVATE)
                .edit()
                .putString("secret_$keyAlias", blob)
                .apply()
            true
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Liest ein Secret aus dem App-Storage und entschlüsselt es.
     * @param keyAlias der Android-Keystore-Alias
     * @return der Klartext-Wert oder null (nicht gespeichert/fehler)
     */
    fun readSecret(keyAlias: String): String? {
        val ks = this.ks ?: return null
        if (!ks.containsAlias(keyAlias)) return null
        val key = try {
            ks.getKey(keyAlias, null) as? SecretKey ?: return null
        } catch (e: Exception) {
            return null
        }

        val blob = app.getSharedPreferences(PREFS, app.MODE_PRIVATE)
            .getString("secret_$keyAlias", null) ?: return null

        return try {
            val data = Base64.decode(blob, Base64.DEFAULT)
            val iv = data.copyOfRange(0, 12)
            val ciphertext = data.copyOfRange(12, data.size)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(
                Cipher.DECRYPT_MODE,
                key,
                GCMParameterSpec(128, iv)
            )
            String(cipher.doFinal(ciphertext), Charsets.UTF_8)
        } catch (e: Exception) {
            null
        }
    }

    /**
     * Liefert den API-Key-Wert für den Node-Prozess (AGNES_API_KEY).
     * Ruft storeSecret + readSecret auf; wenn noch nichts gespeichert
     * ist, liefert es null.
     *
     * @param provider der Provider (z. B. "agnes")
     * @return der Klartext-Key oder null
     */
    fun getApiKeyForProcess(provider: String): String? {
        val alias = getKeyAliasForProvider(provider) ?: return null
        return readSecret(alias)
    }
}
