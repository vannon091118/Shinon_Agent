package com.vannon.shinon

import android.Manifest
import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.View
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.core.content.ContextCompat
import android.widget.Button
import android.widget.TextView

/** WebView shell for the tokenized loopback URL proven by ShinonService. */
class MainActivity : Activity() {

    companion object {
        private const val REQUEST_POST_NOTIFICATIONS = 1
        private const val TAG = "MainActivity"
    }

    private lateinit var webView: WebView
    private lateinit var splashView: View
    private lateinit var errorView: View
    private lateinit var retryButton: Button
    private lateinit var errorMessage: TextView
    private var engineOrigin: Uri? = null

    private val urlReadyReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val value = intent.getStringExtra("url") ?: return
            loadUrl(value)
        }
    }

    private val processEndReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val reason = intent.getStringExtra("reason") ?: "unknown"
            showError(reason)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        webView = findViewById(R.id.webview)
        splashView = findViewById(R.id.splash_view)
        errorView = findViewById(R.id.error_view)
        retryButton = findViewById(R.id.retry_button)
        errorMessage = findViewById(R.id.error_message)

        configureWebView()
        retryButton.setOnClickListener { startService() }
        showSplash()
        ContextCompat.registerReceiver(this, urlReadyReceiver, IntentFilter(ShinonService.INTENT_URL_READY), ContextCompat.RECEIVER_NOT_EXPORTED)
        ContextCompat.registerReceiver(this, processEndReceiver, IntentFilter(ShinonService.INTENT_PROCESS_END), ContextCompat.RECEIVER_NOT_EXPORTED)
        requestNotificationPermissionIfNeeded()
        startService()
    }

    override fun onDestroy() {
        unregisterReceiver(urlReadyReceiver)
        unregisterReceiver(processEndReceiver)
        webView.destroy()
        super.onDestroy()
    }

    private fun configureWebView() {
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.allowFileAccess = false
        webView.settings.javaScriptCanOpenWindowsAutomatically = false

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val target = request.url
                val origin = engineOrigin
                if (origin != null &&
                    target.scheme == "http" &&
                    target.host == origin.host &&
                    target.port == origin.port
                ) {
                    return false
                }
                startActivity(Intent(Intent.ACTION_VIEW, target))
                return true
            }
        }
    }

    private fun loadUrl(value: String) {
        val parsed = Uri.parse(value)
        val host = parsed.host?.lowercase()
        val valid = parsed.scheme == "http" &&
            (host == "127.0.0.1" || host == "localhost") &&
            parsed.port in 1..65535 &&
            !parsed.getQueryParameter("token").isNullOrBlank() &&
            parsed.userInfo == null &&
            parsed.fragment == null
        if (!valid) {
            showError("invalid_ready_url")
            return
        }
        engineOrigin = parsed
        webView.loadUrl(value)
        webView.visibility = View.VISIBLE
        splashView.visibility = View.GONE
        errorView.visibility = View.GONE
    }

    private fun showSplash() {
        splashView.visibility = View.VISIBLE
        errorView.visibility = View.GONE
        webView.visibility = View.GONE
    }

    private fun showError(reason: String) {
        val readable = when (reason) {
            "runtime_missing" -> "Runtime-Dateien fehlen. Setup erneut ausführen."
            "spawn_failed" -> "Die native Runtime konnte nicht gestartet werden. Geräte-Log prüfen."
            "ready_timeout" -> "Die Runtime hat nicht rechtzeitig geantwortet. Kein READY wurde bestätigt."
            "health_check_failed" -> "Der lokale Engine-Endpunkt antwortet nicht mehr."
            "crash" -> "Die Runtime wurde unerwartet beendet."
            "invalid_ready_url" -> "Die Engine lieferte eine ungültige lokale READY-Adresse."
            "clean" -> "Die Runtime wurde beendet."
            else -> "Runtime-Fehler: " + reason
        }
        errorMessage.text = readable
        errorView.visibility = View.VISIBLE
        splashView.visibility = View.GONE
        webView.visibility = View.GONE
        engineOrigin = null
        webView.loadUrl("about:blank")
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) return
        requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), REQUEST_POST_NOTIFICATIONS)
    }

    private fun startService() {
        showSplash()
        val intent = Intent(this, ShinonService::class.java).setAction(ShinonService.ACTION_START)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(intent) else startService(intent)
    }
}
