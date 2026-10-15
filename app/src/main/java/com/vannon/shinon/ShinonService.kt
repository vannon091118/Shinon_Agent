package com.vannon.shinon

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.IBinder
import android.os.SystemClock
import android.util.Log
import androidx.core.app.NotificationCompat
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/** Owns the proot process and publishes READY only after a tokenized loopback URL answers HTTP. */
class ShinonService : Service() {
    companion object {
        private const val TAG = "ShinonService"
        private const val CHANNEL_ID = "shinon_service"
        private const val NOTIFICATION_ID = 1
        const val ACTION_START = "com.vannon.shinon.START"
        const val ACTION_STOP = "com.vannon.shinon.STOP"
        const val ACTION_RESTART = "com.vannon.shinon.RESTART"
        const val INTENT_URL_READY = "com.vannon.shinon.URL_READY"
        const val INTENT_PROCESS_END = "com.vannon.shinon.PROCESS_END"
        private const val READY_TIMEOUT_MS = 120_000L
        private const val POLL_MS = 1_000L
        private const val HEALTH_INTERVAL_MS = 5_000L
        private const val MAX_RESTART_ATTEMPTS = 3
    }

    @Volatile private var running = false
    @Volatile private var enginePid = -1
    @Volatile private var supervisor: Thread? = null
    @Volatile private var restartAttempts = 0
    @Volatile private var lastReadyUrl: String? = null
    @Volatile private var stopRequested = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "Shinon Engine", NotificationManager.IMPORTANCE_LOW)
        )
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopRequested = true
                stopEngine()
                return START_NOT_STICKY
            }
            ACTION_RESTART -> {
                stopRequested = false
                stopEngineProcessOnly()
                startForegroundNow("Shinon startet neu")
                startEngine()
            }
            else -> {
                stopRequested = false
                startForegroundNow("Runtime wird gestartet")
                startEngine()
            }
        }
        return START_STICKY
    }

    private fun startForegroundNow(message: String) {
        startForeground(NOTIFICATION_ID, buildNotification(message))
    }

    private fun buildNotification(message: String): Notification =
        NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Shinon Forge")
            .setContentText(message)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true)
            .build()

    @Synchronized
    private fun startEngine() {
        if (running || stopRequested) return
        val runtimeDir = File(filesDir, "runtime/shinon-forge")
        val rootfsNode = File(filesDir, "rootfs/debian/usr/bin/node")
        val proot = File(filesDir, "proot/proot")
        val dshEntry = File(runtimeDir, "node_modules/@deepseek-ai/dsh/lib/bin.js")
        val profile = File(runtimeDir, "profiles/mobile/package.json")
        if (!rootfsNode.isFile || !proot.isFile || !dshEntry.isFile || !profile.isFile) {
            publishEnd("runtime_missing")
            updateNotification("Shinon Runtime fehlt")
            return
        }

        running = true
        lastReadyUrl = null
        val log = File(filesDir, "logs/dsh.log")
        log.parentFile?.mkdirs()
        // A stale READY line from an older process must never satisfy this boot.
        if (log.exists() && !log.delete()) {
            running = false
            publishEnd("spawn_failed")
            updateNotification("Engine-Log nicht erneuerbar")
            return
        }

        val pid = try {
            NativeLib.initNative(filesDir.absolutePath)
            NativeLib.startDsh(runtimeDir.absolutePath, log.absolutePath)
        } catch (t: Throwable) {
            Log.e(TAG, "Native start failed: " + (t.message ?: t.javaClass.simpleName))
            -1
        }
        if (pid <= 0) {
            running = false
            publishEnd("spawn_failed")
            updateNotification("Runtime konnte nicht gestartet werden")
            Log.e(TAG, "Native runtime did not start (code=" + pid + ")")
            return
        }
        enginePid = pid
        Log.i(TAG, "Runtime process spawned pid=" + pid + "; awaiting verified READY")
        supervisor = Thread({ supervise(pid, log) }, "shinon-runtime-supervisor").also { it.start() }
    }

    private fun supervise(pid: Int, log: File) {
        val deadline = SystemClock.elapsedRealtime() + READY_TIMEOUT_MS
        var readyUrl: String? = null
        while (isCurrent(pid) && SystemClock.elapsedRealtime() < deadline) {
            if (processEnded(pid)) {
                handleCrash(pid, "spawn_failed")
                return
            }
            val candidate = readReadyUrl(log)
            if (candidate != null && probeReadyUrl(candidate)) {
                readyUrl = candidate
                break
            }
            try { Thread.sleep(POLL_MS) } catch (_: InterruptedException) { return }
        }
        if (!isCurrent(pid)) return
        if (readyUrl == null) {
            Log.e(TAG, "READY not verified before timeout")
            stopPid(pid)
            publishEnd("ready_timeout")
            updateNotification("Shinon: READY-Timeout")
            return
        }

        // READY means a new process printed the URL, token is present, and that
        // exact URL returned HTTP 2xx. The tokenized URL is never written to logs.
        lastReadyUrl = readyUrl
        updateNotification("Shinon bereit")
        publishUrl(readyUrl)
        Log.i(TAG, "READY verified: loopback HTTP responded on port " + Uri.parse(readyUrl).port)

        var failures = 0
        while (isCurrent(pid)) {
            try { Thread.sleep(HEALTH_INTERVAL_MS) } catch (_: InterruptedException) { return }
            if (!isCurrent(pid)) return
            if (processEnded(pid)) {
                handleCrash(pid, "crash")
                return
            }
            if (lastReadyUrl?.let { probeReadyUrl(it) } == true) failures = 0
            else {
                failures++
                Log.w(TAG, "local health probe failed " + failures + "/3")
                if (failures >= 3) {
                    handleCrash(pid, "health_check_failed")
                    return
                }
            }
        }
    }

    private fun isCurrent(pid: Int): Boolean = running && !stopRequested && enginePid == pid

    private fun processEnded(pid: Int): Boolean {
        return try {
            NativeLib.reapExitStatus(pid) != NativeLib.PROCESS_RUNNING
        } catch (t: Throwable) {
            Log.e(TAG, "Could not read native process status")
            true
        }
    }

    private fun readReadyUrl(log: File): String? {
        if (!log.isFile) return null
        val text = try { log.readText() } catch (_: Exception) { return null }
        val matches = Regex("dsh web: (http://\\S+)").findAll(text)
        return matches.lastOrNull()?.groupValues?.getOrNull(1)?.let { value ->
            if (isAllowedReadyUrl(value)) value else null
        }
    }

    private fun isAllowedReadyUrl(value: String): Boolean {
        return try {
            val uri = Uri.parse(value)
            val host = uri.host?.lowercase()
            uri.scheme == "http" &&
                (host == "127.0.0.1" || host == "localhost") &&
                uri.port in 1..65535 &&
                !uri.getQueryParameter("token").isNullOrBlank() &&
                uri.userInfo == null &&
                uri.fragment == null
        } catch (_: Exception) {
            false
        }
    }

    private fun probeReadyUrl(value: String): Boolean {
        if (!isAllowedReadyUrl(value)) return false
        var connection: HttpURLConnection? = null
        return try {
            connection = URL(value).openConnection() as HttpURLConnection
            connection.connectTimeout = 1_500
            connection.readTimeout = 1_500
            connection.instanceFollowRedirects = false
            connection.requestMethod = "GET"
            connection.setRequestProperty("Cache-Control", "no-cache")
            connection.responseCode in 200..299
        } catch (_: Exception) {
            false
        } finally {
            connection?.disconnect()
        }
    }

    @Synchronized
    private fun handleCrash(pid: Int, reason: String) {
        if (enginePid != pid) return
        enginePid = -1
        running = false
        lastReadyUrl = null
        if (stopRequested) return
        if (restartAttempts >= MAX_RESTART_ATTEMPTS) {
            publishEnd(reason)
            updateNotification("Shinon gestoppt: " + reason)
            return
        }
        restartAttempts++
        Log.w(TAG, "Runtime ended; restart " + restartAttempts + "/" + MAX_RESTART_ATTEMPTS)
        Thread({
            try { Thread.sleep(2_000) } catch (_: InterruptedException) { return@Thread }
            if (!stopRequested) startEngine()
        }, "shinon-runtime-restart").start()
    }

    private fun stopPid(pid: Int) {
        try {
            if (!NativeLib.stopDsh(pid)) Log.w(TAG, "Native stop could not confirm process shutdown")
        } catch (_: Throwable) {
            Log.e(TAG, "Native stop failed")
        }
        if (enginePid == pid) enginePid = -1
        running = false
        lastReadyUrl = null
    }

    private fun stopEngineProcessOnly() {
        running = false
        supervisor?.interrupt()
        supervisor = null
        val pid = enginePid
        enginePid = -1
        lastReadyUrl = null
        if (pid > 0) {
            try {
                if (!NativeLib.stopDsh(pid)) Log.w(TAG, "Native stop did not confirm process shutdown")
            } catch (_: Throwable) {
                Log.e(TAG, "Native stop failed")
            }
        }
    }

    @Synchronized
    private fun stopEngine() {
        stopEngineProcessOnly()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            @Suppress("DEPRECATION")
            stopForeground(true)
        }
        stopSelf()
    }

    private fun publishUrl(value: String) {
        sendBroadcast(Intent(INTENT_URL_READY).putExtra("url", value))
    }

    private fun publishEnd(reason: String) {
        sendBroadcast(Intent(INTENT_PROCESS_END).putExtra("reason", reason))
    }

    private fun updateNotification(message: String) {
        getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID, buildNotification(message))
    }

    override fun onDestroy() {
        stopRequested = true
        stopEngineProcessOnly()
        super.onDestroy()
    }
}
