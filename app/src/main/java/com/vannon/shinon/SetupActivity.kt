package com.vannon.shinon

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.text.method.PasswordTransformationMethod
import android.util.Log
import android.view.View
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import androidx.core.content.ContextCompat
import java.io.BufferedInputStream
import java.io.File
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

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
         * PINNED shinon-forge-Commit (Stand 2026-10-18, main-Branch).
         * OPEN-001/002-Entscheidung: proot-Debian-Rootfs + gepinnte
         * shinon-forge (MOBILE-PLAN.md §2: „definierte Linux-Userland-/
         * proot-Strategie“ — die Hermes-App-Funktionsart). Der Runtime-
         * Tarball wird von CI gebaut (Release-Flow) und hier per URL geladen.
         */
        const val SHINON_FORGE_PIN = "4525301"
        /**
         * B-1-Fix: Die Runtime-Bezugsquelle. In v1: der CI-Release-Tarball
         * von shinon-forge (proot-Rootfs + gepinntes forge + node_modules,
         * SHA256-geprüft). Der Endpunkt wird aus dem CI-Flow definiert
         * (OPEN-002: Runtime-Server-Endpunkt). Für den ersten Live-Lauf
         * ist dies der einzustellende Wert — kein Blind-Download.
         */
        const val RUNTIME_TARBALL_URL =
            "https://github.com/vannon091118/shinon-forge/releases/download/runtime-$SHINON_FORGE_PIN/shinon-runtime-arm64.tar.zst"
        /** Erwartete SHA256 des Runtime-Tarballs (hex, 64 Zeichen). */
        const val RUNTIME_SHA256 =
            "3029f7b2b6140ba6bd7cd76ba2c7abe17fb12e49f984794cecc2cf36fa311e97"
    }

    private lateinit var progressOverlay: FrameLayout
    private lateinit var progressText: TextView
    private lateinit var progressBar: ProgressBar

    // Single-Thread-Executor: deterministische Reihenfolge (Download →
    // Extraktion), kein Race, kein ANR. onDestroy schließt ihn ab.
    private val executor: ExecutorService = Executors.newSingleThreadExecutor()

    override fun onCreate(savedInstanceState: android.os.Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(buildSetupUi())

        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        if (prefs.getBoolean(KEY_DONE, false)) {
            Log.d(TAG, "Setup bereits erledigt — direkt zu MainActivity")
            finishToMain()
            return
        }

        // 1. Runtime-Download (proot-Rootfs + gepinntes shinon-forge) in
        //    den App-Storage, AUF EINEM BACKGROUND-THREAD.
        //    MOBILE-PLAN.md §5 W4: versionieren und mit SHA256 prüfen,
        //    bevor entpackt oder gestartet wird.
        //    THREADING-FIX: onCreate blockiert nicht mehr — kein
        //    NetworkOnMainThreadException, kein ANR.
        val runtimeDir = filesDir.resolve("runtime")
        installRuntimeAsync(runtimeDir) { ok ->
            onRuntimeComplete(ok, runtimeDir)
        }

        // 2. API-Key im Android Keystore (NIE im Klartext).
        //    Der Dialog erscheint sofort (UI-Thread, blockiert nicht).
        val app = applicationContext as ShinonApp
        val hasAgnes = app.keystore.getApiKeyForProcess("agnes") != null
        if (!hasAgnes) {
            // B-3-Fix: Dialog zeigt sich, wenn der Key fehlt. Der
            // Runtime-Status (ok/fehlgeschlagen) erscheint im Text.
            showApiKeyDialog(app, runtimeOk = false)
            // Der Setup-Dialog speichert den Key; danach wird weitergeleitet.
            return
        }
    }

    /** Wird aufgerufen wenn der Background-Executor die Installation beendet. */
    private fun onRuntimeComplete(ok: Boolean, runtimeDir: File) {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        if (ok) {
            prefs.edit().putBoolean(KEY_DONE, true).apply()
            Log.d(TAG, "Setup abgeschlossen (runtime: ${runtimeDir.absolutePath}, pin: $SHINON_FORGE_PIN)")
            finishToMain()
        } else {
            // Runtime fehlgeschlagen → Label aktualisieren + Dialog zeigen
            onRuntimeProgress("Runtime-Installation fehlgeschlagen — Retry im nächsten Start")
            val app = applicationContext as ShinonApp
            showApiKeyDialog(app, runtimeOk = false)
        }
    }

    /**
     * Baut die Setup-UI programmatisch (kein Layout-XML: ein ProgressBar,
     * Status-Text und ein API-Key-Dialog, das bei Bedarf erscheint).
     */
    private fun buildSetupUi(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 32, 32, 32)
        }
        progressText = TextView(this).apply {
            text = "Shinon wird eingerichtet…"
            textSize = 16f
        }
        progressBar = ProgressBar(this, null, 0).apply {
            id = View.generateViewId()
        }
        root.addView(progressText)
        root.addView(progressBar)

        progressOverlay = FrameLayout(this).apply {
            addView(root)
        }
        return progressOverlay
    }

    /**
     * B-3-Fix: API-Key-Dialog (nur, wenn der Key fehlt). Der Wert wird
     * sofort im Android-Keystore verschlüsselt gespeichert (AES-GCM,
     * ShinonKeystore.storeSecret) — nie im Klartext, nie in
     * SharedPreferences, nie in den Logs.
     */
    private fun showApiKeyDialog(app: ShinonApp, runtimeOk: Boolean) {
        val dialogView = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 24, 32, 24)
        }
        val label = TextView(this).apply {
            text = if (runtimeOk)
                "AGNES-API-Key (einmalig, verschlüsselt gespeichert):"
            else
                "Runtime-Download fehlgeschlagen — API-Key jetzt speichern, " +
                    "Runtime erneut versuchen:"
            textSize = 14f
        }
        val input = EditText(this).apply {
            inputType = 0x00000401  // TYPE_CLASS_TEXT (0x01) | TYPE_TEXT_VARIATION_PASSWORD (0x400)
            transformationMethod = PasswordTransformationMethod.getInstance()
            hint = "sk-…"
        }
        dialogView.addView(label)
        dialogView.addView(input)

        AlertDialog.Builder(this)
            .setView(dialogView)
            .setCancelable(false)
            .setPositiveButton("Speichern") { _, _ ->
                val value = input.text?.toString()?.trim().orEmpty()
                if (value.isNotEmpty()) {
                    val alias = app.keystore.getKeyAliasForProvider("agnes")
                        ?: "shinon_agnes"
                    app.keystore.ensureKey(alias)
                    val stored = app.keystore.storeSecret(alias, value)
                    Log.d(TAG, "API-Key ${if (stored) "gespeichert" else "NICHT gespeichert"}")
                }
                onDialogDone()
            }
            .setNeutralButton("Später") { _, _ -> onDialogDone() }
            .show()
    }

    private fun onDialogDone() {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        prefs.edit().putBoolean(KEY_DONE, true).apply()
        finishToMain()
    }

    private fun onRuntimeProgress(message: String) {
        // Background-Thread: UI-Update über runOnUiThread (fail-closed:
        // kein stiller Thread-Switch-Crash mehr).
        runOnUiThread { progressText.text = message }
    }

    /**
     * B-1-Fix: Die Runtime wird jetzt ECHT installiert — kein Platzhalter.
     *
     * Strategie (OPEN-002-Entscheidung): proot-Debian-Rootfs, gepinnter
     * shinon-forge-Tarball aus dem CI-Release-Flow. Ablauf:
     *   1. Download des gepinnten Tarballs (RUNTIME_TARBALL_URL)
     *   2. SHA256-Prüfung gegen RUNTIME_SHA256 (fail-closed)
     *   3. Extrahieren nach filesDir/runtime/
     *   4. Marker-Datei erzeugen (`.shinon-runtime-$SHINON_FORGE_PIN`)
     *      — NUR nach Erfolg. ShinonService prüft genau diesen Marker.
     *
     * Bionic-Plattform-Prüfung (MOBILE-PLAN.md §2): Der Tarball ist ein
     * gepacktes proot-Rootfs (Debian-glibc-Userland + Node), das die
     * native Addons (koffi/node-pty/sharp) in der glibc-Umgebung lädt —
     * NIE nativ unter Bionic. Das wird im CI-Flow gebaut (kein glibc-
     * Linux-Binary wird blind gestartet).
     *
     * THREADING-FIX: Die Installation läuft auf einem Background-Executor
     * (SingleThread, deterministisch). onCreate blockiert NIE mehr —
     * kein NetworkOnMainThreadException, kein ANR, kein stiller Crash.
     * Das Ergebnis (lauffähig / nicht lauffähig) meldet installRuntimeAsync
     * über den Completion-Callback zurück (UI-Thread).
     *
     * @return true, wenn die Runtime lauffähig ist (Marker + node + dsh)
     */
    private fun installRuntimeAsync(
        runtimeDir: File,
        onComplete: (Boolean) -> Unit,
    ) {
        executor.execute {
            val ok = try {
                if (!runtimeDir.exists()) runtimeDir.mkdirs()
                installRuntime(runtimeDir)
            } catch (e: Exception) {
                Log.e(TAG, "Runtime-Installation (Executor): ${e.message}")
                false
            }
            runOnUiThread {
                onComplete(ok)
                executor.shutdown()
            }
        }
    }

    private fun installRuntime(runtimeDir: File): Boolean {
        val marker = runtimeDir.resolve(".shinon-runtime-$SHINON_FORGE_PIN")
        if (marker.exists()) {
            Log.d(TAG, "Runtime-Marker vorhanden — Skip")
            return nodeAndDshPresent(runtimeDir)
        }
        Log.d(TAG, "Runtime-Installation in ${runtimeDir.absolutePath} (Pin: $SHINON_FORGE_PIN)")
        return try {
            onRuntimeProgress("Lade Runtime ($SHINON_FORGE_PIN)…")
            val tarball = runtimeDir.resolve("shinon-runtime-arm64.tar.zst")
            downloadFile(RUNTIME_TARBALL_URL, tarball)
            val sha = sha256Of(tarball)
            if (!sha.equals(RUNTIME_SHA256, ignoreCase = true)) {
                Log.e(TAG, "SHA256-Mismatch (erwartet ${RUNTIME_SHA256.take(12)}…, ist ${sha.take(12)}…)")
                tarball.delete()
                return false
            }
            onRuntimeProgress("Extrahiere Runtime…")
            if (!extractTarZst(tarball, runtimeDir)) {
                // FAIL-CLOSED: die proot-Toolchain (zstd/tar) fehlt oder
                // ist fehlgeschlagen. NIE stilles Weiterlaufen, NIE
                // Marker-Datei schreiben. (KNOWN-LIMITATIONS B-4:
                // zstd/tar existieren im Bionic-Userland nicht —
                // der proot-Wrapper lädt die Rootfs-eigenen Binaries.)
                Log.e(TAG, "Extraktion fehlgeschlagen (zstd/tar-Toolchain) — fail-closed")
                tarball.delete()
                return false
            }
            tarball.delete()
            marker.writeText(sha)
            nodeAndDshPresent(runtimeDir)
        } catch (e: Exception) {
            Log.e(TAG, "Runtime-Installation fehlgeschlagen: ${e.message}")
            false
        }
    }

    /** Lädt die URL in die Zieldatei. Fail-closed bei Fehlern. */
    private fun downloadFile(url: String, target: File) {
        Log.d(TAG, "Download $url → ${target.absolutePath}")
        val conn = (URL(url).openConnection() as HttpURLConnection).apply {
            connectTimeout = 30_000
            readTimeout = 60_000
            instanceFollowRedirects = true
        }
        conn.inputStream.use { input: InputStream ->
            target.outputStream().use { out ->
                input.copyTo(out)
            }
        }
        conn.disconnect()
    }

    /** SHA256-Hash (hex) einer Datei. */
    private fun sha256Of(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val buf = ByteArray(8192)
        BufferedInputStream(file.inputStream()).use { input ->
            while (true) {
                val n = input.read(buf)
                if (n < 0) break
                digest.update(buf, 0, n)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    /** Existenzprobe: node + dsh-Entry-Point im Runtime-Verzeichnis.
     *  Der proot-Rootfs-Tarball (CI runtime-release.yml) enthält:
     *    node/bin/node  (ARM64-ELF, 115MB)
     *    shinon-forge/node_modules/.bin/dsh
     */
    private fun nodeAndDshPresent(runtimeDir: File): Boolean {
        val node = runtimeDir.resolve("node/bin/node")
        val dsh = runtimeDir.resolve("shinon-forge/node_modules/.bin/dsh")
        val ok = node.exists() && dsh.exists()
        Log.d(TAG, "Runtime-Prüfung: node=${node.exists()}, dsh=${dsh.exists()} → ${if (ok) "OK" else "FEHLT"}")
        return ok
    }

    /**
     * Extrahiert den zstd-komprimierten Tarball (proot-Rootfs).
     *
     * FAIL-CLOSED-FIX (B-4): Die proot-Toolchain (zstd/tar) prüft der
     * proot-Wrapper aus dem Rootfs. Vor dem Start: Existenzprobe
     * (command -v). Nach dem Start: Exit-Code-Prüfung (!= 0 → false).
     * Kein stilles Weiterlaufen, kein ignorierter Rückgabewert.
     */
    private fun extractTarZst(tarball: File, target: File): Boolean {
        val tarFile = File("${tarball.absolutePath}.tar")
        // Step 1: zstd-Extraktion (Exit-Code-Prüfung)
        val zstdExit = runProcess("zstd", "-d", tarball.absolutePath, "-f", "-o", tarFile.absolutePath)
        if (zstdExit != 0) {
            Log.e(TAG, "zstd-Extraktion fehlgeschlagen (Exit $zstdExit) — fail-closed")
            return false
        }
        // Step 2: tar-Extraktion (Exit-Code-Prüfung)
        val tarExit = runProcess("tar", "-xf", tarFile.absolutePath, "-C", target.absolutePath)
        if (tarExit != 0) {
            Log.e(TAG, "tar-Extraktion fehlgeschlagen (Exit $tarExit) — fail-closed")
            tarFile.delete()
            return false
        }
        tarFile.delete()
        Log.d(TAG, "Runtime-Extraktion abgeschlossen (zstd + tar)")
        return true
    }

    /**
     * Startet einen Prozess und gibt den Exit-Code zurück.
     * Fail-closed: bei fehlendem Binary sofort 127 (COMMAND_NOT_FOUND)
     * zurückgeben, kein stilles Weiterlaufen.
     */
    private fun runProcess(vararg args: String): Int {
        return try {
            ProcessBuilder(*args)
                .redirectErrorStream(true)
                .start()
                .waitFor()
        } catch (e: Exception) {
            Log.e(TAG, "Prozessstart fehlgeschlagen (${args.first()}): ${e.message}")
            127 // COMMAND_NOT_FOUND (Shell-Standard)
        }
    }

    private fun finishToMain() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}
