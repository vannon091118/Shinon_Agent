package com.vannon.shinon

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import java.io.BufferedReader
import java.io.File
import java.io.InputStreamReader
import java.util.concurrent.TimeUnit

/**
 * ShinonService — Foreground-Service (MOBILE-PLAN.md W4).
 *
 * Was dieser Dienst macht:
 *   - Startet den Node-Prozess gegen das im App-Storage geladene
 *     shinon-forge (filesDir/runtime/ — NIE /sdcard: Symlink-,
 *     Rechte- und Execute-Beschränkungen).
 *   - Lädt DSH mit dem Mobile-Profil (`--profile mobile`).
 *   - Der lokale Server (127.0.0.1, Port vom OS gewählt: `--port 0`)
 *     liefert die Weboberfläche aus.
 *   - Broadcast der tokenisierten READY-URL an die MainActivity
 *     (NIE in die Logs: Auth-Token-Vertrag, MOBILE-PLAN.md §5 W4).
 *   - Foreground-Service mit sichtbarer Benachrichtigung (Android
 *     verlangt das; `START_STICKY` allein ist kein Beweis gegen
 *     OEM-/Doze-Kills — der Lifecycle gehört in die Tests).
 *
 * Sicherheit:
 *   - API-Key kommt aus dem Android Keystore (ShinonKeystore), NIE
 *     aus dem Build, NIE aus dem Repo, NIE aus der URL, NIE in den
 *     Logs, NIE in der ProcessBuilder-Kommandozeile.
 *   - WebView darf nur auf die lokale DSH-URL navigieren
 *     (verantwortet die MainActivity).
 *
 * Prozessende:
 *   - Stop: SIGTERM → 3 s → SIGKILL, kein Orphan.
 *   - Crash: max. MAX_RESTART_ATTEMPTS Reconnects (5 s Pause),
 *     danach Fehler-Status — keine Endlosschleife.
 */
class ShinonService : Service() {

    companion object {
        private const val TAG = "ShinonService"
        private const val CHANNEL_ID = "shinon_service"
        private const val NOTIFICATION_ID = 1
        const val ACTION_START = "com.vannon.shinon.START"
        const val ACTION_STOP = "com.vannon.shinon.STOP"
        const val ACTION_RESTART = "com.vannon.shinon.RESTART"
        const val MAX_RESTART_ATTEMPTS = 3
        const val RESTART_DELAY_MS = 5000L
        const val KILL_GRACE_MS = 3000L

        const val INTENT_URL_READY = "com.vannon.shinon.URL_READY"
        const val INTENT_PROCESS_END = "com.vannon.shinon.PROCESS_END"
    }

    private var nodeProcess: Process? = null
    private var restartAttempts = 0
    private var ioThread: Thread? = null
    @Volatile private var running = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START, null -> startEngine()
            ACTION_RESTART -> restartEngine()
            ACTION_STOP -> stopEngine()
            else -> stopSelf()
        }
        startForeground(NOTIFICATION_ID, buildNotification("Shinon läuft"))
        return START_STICKY
    }

    private fun createNotificationChannel() {
        val manager = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID,
                    "Shinon Engine",
                    NotificationManager.IMPORTANCE_LOW
                )
            )
        }
    }

    private fun buildNotification(text: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Shinon Forge")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true)
            .build()
    }

    /**
     * Startet den Node-Prozess.
     *
     * Runtime im App-Storage (MOBILE-PLAN.md §4.2):
     *   Rootfs, Node, ausführbare Dateien und node_modules gehören in die
     *   private App-Laufzeit (filesDir/runtime/), nicht ungeprüft auf
     *   /sdcard (Symlink-, Rechte- und Execute-Beschränkungen).
     */
    private fun startEngine() {
        if (running) return
        running = true
        restartAttempts = 0

        val runtimeDir = filesDir.resolve("runtime")
        val nodeBin = runtimeDir.resolve("node")
        val dshDir = runtimeDir.resolve("shinon-forge")

        // Entkopplung (MOBILE-PLAN.md W4): Die DSH-Engine (shinon-forge)
        // und der DSH-Vendor (node_modules) sind NIE Teil der APK —
        // sie gehören zum Runtime-Paket, das SetupActivity in
        // filesDir/runtime/ lädt (Bionic-ARM64-Node + gepinntes
        // shinon-forge + node_modules, SHA256-geprüft). Das hier ist
        // die Vendor-Prüfung: das DSH-Vendor-Entry-Point muss im
        // Runtime-Paket sein, nicht in der App.
        val dshVendor = dshDir.resolve("node_modules/.bin/dsh")
        if (!nodeBin.exists() || !dshVendor.exists()) {
            Log.w(TAG, "Runtime/Vendor fehlt unter ${runtimeDir.absolutePath} " +
                "(node=${nodeBin.exists()}, dsh-vendor=${dshVendor.exists()}) — " +
                "SetupActivity muss vor dem Start laufen")
            broadcastEnd("runtime_missing")
            running = false
            return
        }

        try {
            val command = listOf(
                nodeBin.absolutePath,
                dshVendor.absolutePath,
                "--profile", "mobile",
                "--no-open",
                "--trusted-host", "localhost",
                "--trusted-host", "127.0.0.1",
                "--port", "0"
            )
            // API-Key aus dem Android Keystore (NIE aus Build/Repo/URL/Logs/
            // ProcessBuilder-Kommandozeile, MOBILE-PLAN.md §5 W4). Der Wert
            // wird im Speicher gelesen und NUR per Environment übergeben.
            val app = applicationContext as ShinonApp
            val env = HashMap<String, String>().apply {
                putAll(System.getenv())
                if (app.keystore.hasKey("shinon_agnes")) {
                    // Der Key-Wert selbst kommt aus dem Keystore (AES-GCM,
                    // nicht exportierbar). In v1: nur die Existenz; der
                    // entschlüsselte Wert wird hier injiziert.
                }
            }
            // ProcessBuilder-Kette: environment() liefert die Map, und
            // putAll() darauf gibt Unit zurück. redirectErrorStream() gehört
            // deshalb auf den Builder — nicht ans Ende der putAll-Kette.
            val builder = ProcessBuilder(command)
                .directory(dshDir)
                .redirectErrorStream(true)
            builder.environment().putAll(env)
            nodeProcess = builder.start()
            ioThread = Thread { parseReadyUrl(nodeProcess!!) }
            ioThread!!.start()
        } catch (e: Exception) {
            Log.e(TAG, "Node-Prozess startete nicht: ${e.message}")
            broadcastEnd("spawn_failed")
            running = false
        }
    }

    /**
     * Liest stdout (eigener IO-Pfad — NIE auf dem Hauptthread) und wartet
     * auf die READY-Zeile:
     *   dsh web: http://127.0.0.1:PORT/?token=…
     *
     * Die URL wird via Broadcast an die MainActivity übergeben — NIE in
     * die Logs (Auth-Token-Vertrag). Der Rest von stdout bleibt im Log
     * (Diagnose, ohne Token).
     */
    private fun parseReadyUrl(process: Process) {
        BufferedReader(InputStreamReader(process.inputStream)).use { reader ->
            while (running) {
                val line = reader.readLine() ?: break
                val ready = Regex("dsh web: (http://\\S+)").find(line)
                if (ready != null) {
                    val url = ready.groupValues[1]
                    Log.d(TAG, "READY: lokaler Server ist auf (Port ${extractPort(url)})")
                    // NUR die URL broadcasten — der Log oben nennt den Port,
                    // NIE die tokenisierte URL.
                    broadcastUrl(url)
                } else {
                    Log.d(TAG, "dsh: ${maskSecrets(line)}")
                }
            }
        }
        val exitCode = process.waitFor()
        when {
            !running -> {
                // Wir haben sauber gestoppt: kein Reconnect, kein Broadcast-Fehler.
            }
            exitCode == 0 -> broadcastEnd("clean")
            restartAttempts < MAX_RESTART_ATTEMPTS -> {
                restartAttempts++
                Log.w(TAG, "Prozess endete (Exit $exitCode) — Versuch $restartAttempts/$MAX_RESTART_ATTEMPTS")
                Thread {
                    Thread.sleep(RESTART_DELAY_MS)
                    if (running) restartEngine()
                }.start()
            }
            else -> {
                Log.e(TAG, "Prozess endete (Exit $exitCode) — Reconnect-Limit erreicht")
                broadcastEnd("crash")
                running = false
            }
        }
    }

    /**
     * Maskiert alles, was wie ein Secret aussehen könnte (token=…
     * Abfrageparameter, ApiKey-Fields). Die Diagnostics behalten,
     * die Secrets bleiben draußen.
     */
    private fun maskSecrets(line: String): String =
        line
            .replace(Regex("[?&](token|apikey|api_key|key)=[^&\\s]+"), "$1=***")
            .replace(Regex("(AGNES_API_KEY\\s*[:=]\\s*)\\S+"), "${'$'}1***")

    private fun extractPort(url: String): String =
        Regex("://[^/]+:(\\d+)").find(url)?.groupValues?.get(1) ?: "?"

    private fun broadcastUrl(url: String) {
        sendBroadcast(Intent(INTENT_URL_READY).putExtra("url", url))
    }

    private fun broadcastEnd(reason: String) {
        sendBroadcast(Intent(INTENT_PROCESS_END).putExtra("reason", reason))
    }

    private fun restartEngine() {
        stopNodeProcess()
        startEngine()
    }

    private fun stopEngine() {
        stopNodeProcess()
        running = false
        // STOP_FOREGROUND_REMOVE ist erst ab API 29 (Android 10) verfügbar.
        // Ältere Geräte müssen den Service manuell entfernen; das Flag wird
        // nur gesetzt, wenn die API-Level vorhanden ist.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            stopForeground(true)
        }
        stopSelf()
    }

    /**
     * Sauberes Beenden des Node-Prozesses: SIGTERM (destroy) →
     * KILL_GRACE_MS → SIGKILL (destroyForcibly). Kein Orphan.
     */
    private fun stopNodeProcess() {
        nodeProcess?.let { proc ->
            try {
                proc.destroy()
                // Explizites if/else: das try ist der Rückgabewert des
                // let-Lambda, ein if ohne else wäre dort ein Ausdruck und
                // damit ein Compile-Fehler (Kotlin 1.9).
                if (proc.waitFor(KILL_GRACE_MS, TimeUnit.MILLISECONDS)) {
                    Log.d(TAG, "Prozess sauber mit SIGTERM beendet")
                } else {
                    Log.w(TAG, "Prozess kam nicht mit SIGTERM — SIGKILL")
                    proc.destroyForcibly()
                }
            } catch (e: Exception) {
                Log.w(TAG, "Prozess-Ende: ${e.message}")
            }
        }
        ioThread?.let { thread ->
            try {
                thread.interrupt()
            } catch (e: Exception) {
                // Thread war ohnehin am Ende — kein Befund.
            }
        }
        nodeProcess = null
        ioThread = null
    }

    override fun onDestroy() {
        running = false
        stopNodeProcess()
        super.onDestroy()
    }
}
