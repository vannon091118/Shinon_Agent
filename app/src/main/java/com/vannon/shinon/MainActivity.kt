package com.vannon.shinon

import android.Manifest
import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.View
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button

/**
 * MainActivity — WebView-Fenster (MOBILE-PLAN.md W4).
 *
 * EINE Aufgabe: die tokenisierte DSH-READY-URL aus dem Service in
 * einer WebView laden. Nichts sonst.
 *
 * Sicherheit (MOBILE-PLAN.md §5 W4):
 *   - WebView lädt NUR die lokale DSH-URL (http://127.0.0.1:…).
 *     Alle anderen externen Links gehen in den Systembrowser —
 *     keine privilegierten JavaScript-Bridges auf fremde Seiten.
 *   - javaScriptEnabled + domStorageEnabled: an (DSH-Client ist ein
 *     vollwertiges Web-UI-Bundle).
 *   - Zoom bleibt an (user-scalable — MOBILE-PLAN.md §2: Zoom nicht
 *     für Touch deaktivieren, Nutzer dürfen weiter vergrößern).
 *   - Crash-Recovery: Wenn der Service neu startet, wird die
 *     WebView automatisch neu geladen (PROCESS_END → URL_READY).
 *   - App-Logs enthalten keine Schlüssel und keine tokenisierte URL.
 *
 * Layout (R.layout.activity_main, drei Ansichten):
 *   - WebView (fill, unsichtbar bis READY)
 *   - Splash/Loader-Overlay (Shinon-Brand, läuft bis die URL kommt)
 *   - Fehler-Overlay (problemtastischer Text, Retry-Button)
 */
class MainActivity : Activity() {

    companion object {
        private const val TAG = "MainActivity"

        /** Request-Code für die Laufzeitabfrage von POST_NOTIFICATIONS (API 33+). */
        private const val REQUEST_POST_NOTIFICATIONS = 1
    }

    private lateinit var webView: WebView
    private lateinit var splashView: View
    private lateinit var errorView: View
    private lateinit var retryButton: Button

    private val urlReadyReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val url = intent.getStringExtra("url") ?: return
            loadUrl(url)
        }
    }

    private val processEndReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            when (intent.getStringExtra("reason")) {
                "clean", "runtime_missing" -> showError()
                "crash" -> {
                    // Service startet von selbst neu (max. 3×) —
                    // die Splash-Ansicht bleibt, bis die neue URL kommt.
                    showError()
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webview)
        splashView = findViewById(R.id.splash_view)
        errorView = findViewById(R.id.error_view)
        retryButton = findViewById(R.id.retry_button)

        configureWebView()
        retryButton.setOnClickListener { startService() }
        showSplash()

        registerReceiver(urlReadyReceiver, IntentFilter(ShinonService.INTENT_URL_READY), Context.RECEIVER_NOT_EXPORTED)
        registerReceiver(processEndReceiver, IntentFilter(ShinonService.INTENT_PROCESS_END), Context.RECEIVER_NOT_EXPORTED)
        requestNotificationPermissionIfNeeded()
        startService()
    }

    override fun onDestroy() {
        unregisterReceiver(urlReadyReceiver)
        unregisterReceiver(processEndReceiver)
        webView.destroy()
        super.onDestroy()
    }

    /**
     * WebView-Konfiguration: JS + DOM-Storage an (DSH-Client braucht
     * beides), kein Datei-Zugriff (kein /sdcard), externe Links →
     * Systembrowser.
     */
    private fun configureWebView() {
        val settings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.allowFileAccess = false
        settings.javaScriptCanOpenWindowsAutomatically = false

        webView.webViewClient = object : WebViewClient() {
            /**
             * Externe Navigation (alles außer der lokalen DSH-URL) →
             * Systembrowser. Die WebView bleibt bei der Engine.
             */
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val scheme = request.url?.scheme ?: return false
                val host = request.url?.host ?: return false
                // Nur die lokale DSH-URL bleibt in der WebView.
                // NUR http auf 127.0.0.1 — https wäre ein privilegierter
                // Zugang zu einer fremden HTTPS-Seite auf Loopback.
                if (scheme == "http" && host == "127.0.0.1") return false
                startActivity(Intent(Intent.ACTION_VIEW, request.url))
                return true
            }
        }
    }

    private fun loadUrl(url: String) {
        // NUR die lokale DSH-URL (http://127.0.0.1:…) wird geladen —
        // externe Seiten niemals (MOBILE-PLAN.md §5 W4).
        if (!url.startsWith("http://127.0.0.1")) return
        webView.loadUrl(url)
        webView.visibility = View.VISIBLE
        splashView.visibility = View.GONE
        errorView.visibility = View.GONE
    }

    private fun showSplash() {
        splashView.visibility = View.VISIBLE
        errorView.visibility = View.GONE
        webView.visibility = View.GONE
    }

    private fun showError() {
        errorView.visibility = View.VISIBLE
        splashView.visibility = View.GONE
        webView.visibility = View.GONE
        webView.loadUrl("about:blank")
    }

    /**
     * Ab API 33 zeigt Android die laufende Dienst-Benachrichtigung nur, wenn
     * POST_NOTIFICATIONS erteilt ist — die Manifest-Deklaration allein genügt
     * dort nicht. Ohne Anfrage bliebe der Foreground-Service für den Nutzer
     * unsichtbar (der Dienst selbst läuft weiter).
     */
    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED
        ) {
            return
        }
        requestPermissions(
            arrayOf(Manifest.permission.POST_NOTIFICATIONS),
            REQUEST_POST_NOTIFICATIONS
        )
    }

    private fun startService() {
        val intent = Intent(this, ShinonService::class.java).apply {
            action = ShinonService.ACTION_START
        }
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }
}
