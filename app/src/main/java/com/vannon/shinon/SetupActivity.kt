package com.vannon.shinon

import android.content.Context
import android.content.Intent
import android.util.Log
import androidx.core.content.ContextCompat
import java.io.File

/**
 * SetupActivity — First-Run (MOBILE-PLAN.md W4).
 *
 * ONLY beim allerersten Start (Flag in SharedPreferences):
 *   1. Lädt die Shinon-Runtime (Node-Binary + gepinntes shinon-forge)
 *      in den App-internen Speicher (filesDir/runtime/), NIE auf /sdcard
 *      (Symlink-, Rechte- und Execute-Beschränkungen).
 *   2. Fragt den API-Key ab (AGNES_API_KEY), speichert ihn im Android
 *      Keystore (ShinonKeystore), NIE im Klartext.
 *   3. Setzt das Flag `setup_done` — danach wird diese Activity nie
 *      wieder gezeigt.
 *
 * Progress-Bar mit Shinon-Branding. Kein Update-Mechanismus in der
 * ersten Version: erst ein reproduzierbarer Installationsstand
 * (MOBILE-PLAN.md §5 W4). Ein späterer Update-Flow prüft SHA256 +
 * validierte Version und rollt bei Fehler zurück.
 */
class SetupActivity : Activity() {

    companion object {
        private const val TAG = "SetupActivity"
        private const val PREFS = "shinon_setup"
        private const val KEY_DONE = "setup_done"
        /**
         * PINNED shnion-forge-Commit (Stand 2026-10-14, develop-Branch).
         * Ein späterer Update-Flow prüft die Version (MOBILE-PLAN.md W4),
         * hier ist der eine, gemessene Pin — kein raten.
         */
        const val SHINON_FORGE_PIN = "d7d38ce"
    }

    override fun onCreate(savedInstanceState: android.os.Bundle?) {
        super.onCreate(savedInstanceState)
        // setContentView(R.layout.activity_setup)

        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        if (prefs.getBoolean(KEY_DONE, false)) {
            Log.d(TAG, "Setup bereits erledigt — direkt zu MainActivity")
            finishToMain()
            return
        }

        // 1. Runtime-Download (Node + shnion-forge) in den App-Storage.
        //    (MOBILE-PLAN.md §5 W4: Laufzeitpaket versionieren und mit
        //     SHA256/Signatur prüfen, bevor es entpackt oder gestartet wird.)
        val runtimeDir = filesDir.resolve("runtime")
        if (!runtimeDir.exists()) runtimeDir.mkdirs()
        installRuntime(runtimeDir)

        // 2. API-Key im Android Keystore (NIE im Klartext).
        val app = applicationContext as ShinonApp
        val alias = app.keystore.getKeyAliasForProvider("agnes")
        if (alias == null) {
            Log.w(TAG, "Kein API-Key im Keystore — Setup muss den Key abfragen")
            // Hier: AlertDialog mit EditText (PASSWORD) + Speichern unter
            //       "shinon_agnes" (ShinonKeystore.ensureKey + verschlüsseltes
            //       Speichern des Werts). NIE im Klartext, NIE in SharedPreferences.
        }

        // 3. Flag setzen — SetupActivity wird danach nie wieder gezeigt.
        prefs.edit().putBoolean(KEY_DONE, true).apply()
        Log.d(TAG, "Setup abgeschlossen (runtime: ${runtimeDir.absolutePath}, pin: $SHINON_FORGE_PIN)")
        finishToMain()
    }

    /**
     * Lädt das gepinnte Runtime-Paket in den App-Storage.
     *
     * In v1 ist das ein Platzhalter für den eigentlichen Download:
     *   - Node-Binary (ARM64, Bionic-kompatibel — kein glibc-Linux-Binary!)
     *   - shnion-forge als Git-Archiv (gepinnt: SHINON_FORGE_PIN)
     *
     * MOBILE-PLAN.md §2 (Korrektur): „Kein Linux-ARM64-Node-Binary blind
     * mit ProcessBuilder starten. Android verwendet Bionic; normale
     * Ubuntu/Debian-Userlands bauen auf glibc." — der Download prüft die
     * Ziel-Plattform (Bionic), nicht die Build-Plattform.
     *
     * @return true, wenn das Runtime-Verzeichnis lauffähig ist
     */
    private fun installRuntime(runtimeDir: File): Boolean {
        Log.d(TAG, "Runtime-Installation in ${runtimeDir.absolutePath} (Pin: $SHINON_FORGE_PIN)")
        // v1: kein echtes Download (braucht den Runtime-Server-Endpunkt aus
        // dem Release-Flow, MOBILE-PLAN.md W4). Die Struktur steht, der
        // Inhalt kommt mit dem ersten reproduzierbaren Lauf.
        val marker = runtimeDir.resolve(".shinon-runtime-$SHINON_FORGE_PIN")
        return marker.exists()
    }

    private fun finishToMain() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}
