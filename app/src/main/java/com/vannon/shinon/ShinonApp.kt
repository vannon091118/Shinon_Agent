package com.vannon.shinon

import android.app.Activity
import android.app.Application
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
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
        NativeLib.initNative(filesDir.absolutePath)
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
}
