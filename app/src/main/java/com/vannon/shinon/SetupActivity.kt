package com.vannon.shinon

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.ProgressBar
import android.widget.TextView
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/**
 * First-run installer. Gate A only: install/hash-check runtime assets.
 * A real provider call is Gate B and is deliberately not required here.
 */
class SetupActivity : Activity() {

    companion object {
        private const val TAG = "SetupActivity"
        private const val PREFS = "shinon_setup"
        private const val KEY_DONE = "setup_done"
        private const val CONNECT_TIMEOUT_MS = 15_000
        private const val READ_TIMEOUT_MS = 30_000
        private const val MAX_RUNTIME_BYTES = 700L * 1024L * 1024L
    }

    private lateinit var status: TextView
    private lateinit var progress: ProgressBar
    private lateinit var retry: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_setup)
        status = findViewById(R.id.setup_status)
        progress = findViewById(R.id.setup_progress)
        retry = findViewById(R.id.setup_retry)
        retry.setOnClickListener { beginInstall() }

        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        if (prefs.getBoolean(KEY_DONE, false) && isRuntimeUsable()) {
            finishToMain()
            return
        }
        // A stale success flag must never conceal a missing runtime.
        prefs.edit().remove(KEY_DONE).apply()
        beginInstall()
    }

    private fun beginInstall() {
        retry.visibility = View.GONE
        progress.visibility = View.VISIBLE
        status.text = "Prüfe Android-Runtime und installiere das Mobile-Profil …"
        Thread({
            try {
                val runtimeAbiSupported = "arm64-v8a" in android.os.Build.SUPPORTED_ABIS ||
                    (android.os.Build.VERSION.SDK_INT >= 35 &&
                        "x86_64" in android.os.Build.SUPPORTED_ABIS)
                require(runtimeAbiSupported) {
                    "Diese Runtime benötigt ARM64 (oder Android 15+ mit ARM64-App-Übersetzung); unterstützt: " +
                        android.os.Build.SUPPORTED_ABIS.joinToString()
                }
                require(NativeLib.probePtrace()) {
                    "Android blockiert ptrace; proot kann auf diesem Gerät nicht gestartet werden."
                }
                installRootfs()
                installProot()
                val runtimeSha = installForgeRuntime()
                File(filesDir, "runtime/.shinon-runtime.json").writeText(
                    "{\"release\":\"" + BuildConfig.SHINON_RUNTIME_RELEASE +
                        "\",\"sha256\":\"" + runtimeSha + "\",\"profile\":\"mobile\",\"node\":\"v22.19.0\"}"
                )
                require(isRuntimeUsable()) { "Runtime-Prüfung nach der Installation fehlgeschlagen." }
                getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(KEY_DONE, true).apply()
                runOnUiThread { finishToMain() }
            } catch (t: Throwable) {
                Log.e(TAG, "Runtime setup failed: " + (t.message ?: t.javaClass.simpleName), t)
                getSharedPreferences(PREFS, MODE_PRIVATE).edit().remove(KEY_DONE).apply()
                runOnUiThread {
                    progress.visibility = View.GONE
                    retry.visibility = View.VISIBLE
                    status.text = "Runtime konnte nicht installiert werden.\n\n" +
                        (t.message ?: t.javaClass.simpleName) +
                        "\n\nBitte Verbindung prüfen und erneut versuchen."
                }
            }
        }, "shinon-runtime-install").start()
    }

    private fun installRootfs() {
        val rootfsDir = File(filesDir, "rootfs")
        val installedNode = File(rootfsDir, "debian/usr/bin/node")
        val marker = File(rootfsDir, ".debian-rootfs.sha256")
        val expected = assets.open("rootfs/debian.tar.xz.sha256").bufferedReader().use { it.readText().trim() }
        require(expected.matches(Regex("[0-9a-fA-F]{64}"))) { "Rootfs-SHA256 fehlt oder ist ungültig." }

        // Reuse only the exact rootfs build pinned into this APK. App upgrades
        // must not silently retain an older Debian/Node image just because node exists.
        if (installedNode.isFile && marker.isFile && marker.readText().trim().equals(expected, ignoreCase = true)) {
            return
        }

        val archive = File(cacheDir, "debian.tar.xz")
        copyAssetIfAbsent("rootfs/debian.tar.xz", archive)
        if (!sha256(archive).equals(expected, ignoreCase = true)) {
            require(archive.delete() || !archive.exists()) { "Beschädigtes Rootfs-Cache-Archiv kann nicht entfernt werden." }
            copyAssetIfAbsent("rootfs/debian.tar.xz", archive)
        }
        require(sha256(archive).equals(expected, ignoreCase = true)) {
            "Rootfs-Asset stimmt nicht mit dem APK-SHA256 überein."
        }
        val result = NativeLib.rootfsVerifyExtract(archive.absolutePath, expected)
        require(result == 0 && installedNode.isFile) {
            "Rootfs-Installation fehlgeschlagen (Code " + result + ")."
        }
        marker.writeText(expected.lowercase())
        archive.delete()
    }

    private fun installProot() {
        val expected = assets.open("proot/proot-arm64.sha256").bufferedReader().use { it.readText().trim() }
        require(expected.matches(Regex("[0-9a-f]{64}"))) { "proot-SHA256 fehlt oder ist ungültig." }
        val proot = File(filesDir, "proot/proot")
        if (proot.isFile && proot.canExecute() && sha256(proot).equals(expected, ignoreCase = true)) return
        proot.parentFile?.mkdirs()
        val part = File(proot.parentFile, "proot-arm64.part")
        assets.open("proot/proot-arm64").use { input ->
            FileOutputStream(part).use { output ->
                input.copyTo(output)
                output.fd.sync()
            }
        }
        require(sha256(part).equals(expected, ignoreCase = true)) {
            "Android-proot-SHA256 stimmt nicht mit dem APK-Marker überein."
        }
        if (proot.exists()) require(proot.delete()) { "Alte proot-Datei kann nicht ersetzt werden." }
        require(part.renameTo(proot)) { "proot-Datei konnte nicht atomar übernommen werden." }
        proot.setExecutable(true, true)
        require(proot.isFile && proot.canExecute()) { "Android-proot fehlt oder ist nicht ausführbar." }
    }

    private fun installForgeRuntime(): String {
        val release = BuildConfig.SHINON_RUNTIME_RELEASE
        require(release.matches(Regex("mobile-runtime-[0-9a-f]{12}"))) {
            "Dieser APK-Build ist nicht an ein gepinntes Runtime-Release gebunden."
        }
        val base = "https://github.com/vannon091118/Shinon_Agent/releases/download/" + release + "/"
        val checksumFile = File(cacheDir, "shinon-forge-mobile-runtime.tar.gz.sha256")
        val archive = File(cacheDir, "shinon-forge-mobile-runtime.tar.gz")
        download(base + checksumFile.name, checksumFile, 4096L)
        val expected = BuildConfig.SHINON_RUNTIME_SHA256
        require(expected.matches(Regex("[0-9a-f]{64}"))) {
            "Dieser APK-Build enthält keinen fest gepinnten Runtime-SHA256."
        }
        val publishedHash = checksumFile.readText().trim().split(Regex("\\s+")).firstOrNull().orEmpty()
        require(publishedHash.equals(expected, ignoreCase = true)) {
            "Release-Prüfsumme stimmt nicht mit dem in die APK eingebauten Pin überein."
        }
        download(base + archive.name, archive, MAX_RUNTIME_BYTES)
        val actual = sha256(archive)
        require(actual.equals(expected, ignoreCase = true)) {
            "Runtime-SHA256 stimmt nicht überein; Archiv wird nicht entpackt."
        }

        val destination = File(filesDir, "runtime/shinon-forge")
        destination.parentFile?.mkdirs()
        val result = NativeLib.extractVerified(archive.absolutePath, expected, destination.absolutePath)
        require(result == 0) {
            "Runtime-Entpacken fehlgeschlagen (Code " + result + "): " + NativeLib.lastExtractError()
        }
        require(File(destination, "node_modules/@deepseek-ai/dsh/lib/bin.js").isFile) {
            "Runtime-Paket enthält keinen erwarteten DSH-Einstieg."
        }
        require(File(destination, "profiles/mobile/package.json").isFile) {
            "Runtime-Paket enthält das gepinnte Mobile-Profil nicht."
        }
        archive.delete()
        checksumFile.delete()
        return actual
    }

    private fun download(url: String, destination: File, maxBytes: Long) {
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            connectTimeout = CONNECT_TIMEOUT_MS
            readTimeout = READ_TIMEOUT_MS
            instanceFollowRedirects = true
            requestMethod = "GET"
            setRequestProperty("Accept", "application/octet-stream")
            setRequestProperty("User-Agent", "Shinon-Android-Runtime")
        }
        try {
            val code = connection.responseCode
            require(code in 200..299) { "Runtime-Download antwortet mit HTTP " + code + "." }
            val announced = connection.contentLengthLong
            require(announced <= 0 || announced <= maxBytes) {
                "Runtime-Datei überschreitet das erlaubte Größenlimit."
            }
            destination.parentFile?.mkdirs()
            val part = File(destination.parentFile, destination.name + ".part")
            var total = 0L
            connection.inputStream.use { input ->
                FileOutputStream(part).use { output ->
                    val buffer = ByteArray(64 * 1024)
                    while (true) {
                        val count = input.read(buffer)
                        if (count < 0) break
                        total += count
                        require(total <= maxBytes) { "Download überschreitet das erlaubte Größenlimit." }
                        output.write(buffer, 0, count)
                    }
                    output.fd.sync()
                }
            }
            require(total > 0) { "Runtime-Download lieferte eine leere Datei." }
            if (destination.exists()) destination.delete()
            require(part.renameTo(destination)) { "Download-Datei konnte nicht atomar übernommen werden." }
        } finally {
            connection.disconnect()
        }
    }

    private fun copyAssetIfAbsent(assetPath: String, destination: File) {
        if (destination.isFile && destination.length() > 0) return
        destination.parentFile?.mkdirs()
        assets.open(assetPath).use { input ->
            FileOutputStream(destination).use { output -> input.copyTo(output) }
        }
    }

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().buffered().use { input ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    private fun isRuntimeUsable(): Boolean {
        val runtime = File(filesDir, "runtime/shinon-forge")
        val marker = File(filesDir, "runtime/.shinon-runtime.json")
        return BuildConfig.SHINON_RUNTIME_RELEASE != "dev-unavailable" &&
            marker.isFile && marker.readText().contains(BuildConfig.SHINON_RUNTIME_RELEASE) &&
            File(filesDir, "rootfs/debian/usr/bin/node").isFile &&
            File(filesDir, "proot/proot").isFile &&
            File(runtime, "node_modules/@deepseek-ai/dsh/lib/bin.js").isFile &&
            File(runtime, "profiles/mobile/package.json").isFile
    }

    private fun finishToMain() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}
