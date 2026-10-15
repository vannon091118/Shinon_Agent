# Architektur — Shinon Agent

> Stand: 2026-10-14 · Ausgangsstand `e78ca1a`
> Alle Angaben sind aus dem Code abgeleitet; Dateipfade sind relativ zum Repo-Root.

## 1. Komponenten und Prozessgrenzen

```
┌─────────────────────────── Android-App (APK) ───────────────────────────┐
│                                                                         │
│  ShinonApp : Application            app/src/main/java/…/ShinonApp.kt    │
│    └─ ShinonKeystore (AndroidKeyStore, AES-256-GCM)                     │
│                                                                         │
│  SetupActivity : Activity (LAUNCHER)          …/SetupActivity.kt        │
│    └─ legt filesDir/runtime/ an, setzt setup_done                        │
│                                                                         │
│  MainActivity : Activity                      …/MainActivity.kt         │
│    └─ WebView + BroadcastReceiver(URL_READY, PROCESS_END)               │
│                                                                         │
│  ShinonService : Foreground-Service           …/ShinonService.kt        │
│    ├─ startEngine()  → ProcessBuilder(node …)                           │
│    └─ parseReadyUrl() → Broadcast an MainActivity                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │ spawn (Kindprozess)
                                    ▼
        $filesDir/runtime/shinon-forge/            ← Runtime-Paket (NICHT in der APK)
          ├─ ../node                                ← Node.js ≥ 22 (Bionic!)
          └─ node_modules/.bin/dsh                  ← DSH-Vendor-Entry-Point
                                    │
                                    ▼
                    DSH-Webserver auf 127.0.0.1:<oszillierender Port>
                                    │ HTTP (tokenisierte URL)
                                    ▼
                              WebView (MainActivity)
```

**Grenze 1 — APK ↔ Runtime.** Die APK enthält weder Engine noch Vendor. Das
prüft `SetupActivity`/`ShinonService` zur Laufzeit (`runtime_missing`) und die
CI prüft dasselbe am fertigen Artefakt (Entkopplungsgate). Rationale und
Verifikation: [`DECISIONS.md`](DECISIONS.md) DEC-005, [`TESTING.md`](TESTING.md) Gate 2.

**Grenze 2 — App ↔ Engine.** Übertragen wird nur die READY-URL per Broadcast
(`ShinonService.INTENT_URL_READY`). Kein Dateiaustausch, keine JS-Bridge.

**Grenze 3 — Prozess ↔ UI.** Die Engine läuft als eigener Prozess; die UI
spricht ausschließlich über HTTP mit ihr. Deshalb ist ein Engine-Absturz kein
App-Absturz, sondern ein `PROCESS_END`-Broadcast.

## 2. Datenfluss beim Start (Soll-Ablauf im Code)

| Schritt | Ort | Verhalten |
|---|---|---|
| 1 | `SetupActivity.onCreate` | `setup_done`? → direkt `MainActivity` |
| 2 | `SetupActivity.installRuntime` | legt `filesDir/runtime/` an — **Platzhalter** |
| 3 | `SetupActivity.onCreate` | liest `keystore.getKeyAliasForProvider("agnes")` — **Warnung statt Dialog** |
| 4 | `SetupActivity.onCreate` | setzt `setup_done = true` |
| 5 | `MainActivity.onCreate` | registriert Receiver, `startForegroundService(ACTION_START)` |
| 6 | `ShinonService.startEngine` | prüft `runtime/node` und `runtime/shinon-forge/node_modules/.bin/dsh` |
| 7 | `ShinonService.startEngine` | `ProcessBuilder(node, dsh, --profile mobile, --no-open, --trusted-host …, --port 0)` mit `cwd = runtime/shinon-forge` und `DSH_HOME` = dasselbe Verzeichnis (DSH löst Profile als `$DSH_HOME/profiles/<name>` auf) |
| 8 | `ShinonService.parseReadyUrl` | liest stdout, sucht `dsh web: (http://\S+)`, broadcastet URL |
| 9 | `MainActivity.urlReadyReceiver` | `loadUrl(url)` — nur wenn `http://127.0.0.1`-Präfix |
| 10 | `MainActivity.showError` | bei `runtime_missing`/`crash`/`clean` |

**Ist-Abweichung:** Schritt 2 und 3 sind nicht implementiert; Schritt 4 läuft
trotzdem. Damit erreicht Schritt 6 immer `runtime_missing`. Das ist der
zentrale Funktionsblocker (siehe [`KNOWN-LIMITATIONS.md`](KNOWN-LIMITATIONS.md) B-1).

## 3. Fehlerpfade

| Signal | Auslöser | Reaktion |
|---|---|---|
| `runtime_missing` | `node` oder `dsh` fehlt im Runtime-Paket | Broadcast, Error-Overlay |
| `spawn_failed` | `ProcessBuilder.start()` wirft | Broadcast, Error-Overlay |
| `clean` | Prozess endet mit Exit 0 bei laufendem Dienst | Error-Overlay |
| `crash` | Prozess endet ungleich 0 nach `MAX_RESTART_ATTEMPTS` (3) | Error-Overlay |
| Reconnect | Exit ≠ 0, Versuche < 3 | Neustart nach `RESTART_DELAY_MS` (5 s) |
| Stop | `ACTION_STOP` | `destroy()` → 3 s → `destroyForcibly()` |

**Nicht unterschieden:** fehlende Node-Fassung, fehlendes Modul, native
Ladefehler (`dlopen`) und Auth-Fehler landen alle in „Exit ≠ 0" und damit im
generischen Reconnect-Pfad. Zielbild Punkt 9 (saubere Fehlertrennung) ist
damit offen.

## 4. Persistenz

| Zustand | Ort | Lebensdauer |
|---|---|---|
| `setup_done` | `SharedPreferences "shinon_setup"` | bis App-Daten gelöscht |
| Runtime-Dateien | `filesDir/runtime/` | bis App-Daten gelöscht |
| Provider-Key | Android Keystore (Alias `shinon_<provider>`) | gerätegebunden, nicht exportierbar |
| lokale DSH-URL | nur im Speicher/Broadcast | pro Sitzung |

Es gibt **keinen** Update-Mechanismus und **keine** Rollback-Fähigkeit für das
Runtime-Paket (geplant, siehe [`SCOPE.md`](SCOPE.md) RT-PIN-001).

## 5. Build- und Bereitstellungsschicht

| Datei | Aufgabe |
|---|---|
| `settings.gradle.kts` | Repos `google()`/`mavenCentral()`, Modul `:app`, `FAIL_ON_PROJECT_REPOS` |
| `build.gradle.kts` | AGP 8.5.0, Kotlin 1.9.24 |
| `app/build.gradle.kts` | `compileSdk 34`, `minSdk 26`, `targetSdk 34`, Java/Kotlin 17, Signing aus Env |
| `gradle.properties` | `android.useAndroidX=true`, JVM-Heap 2048m |
| `gradlew` | Wrapper, lädt Gradle 8.7 selbst (Fix: [`DECISIONS.md`](DECISIONS.md) DEC-001) |
| `.github/workflows/build.yml` | Release-Build, Signing, APK-Inhaltsgate, Artefakt, optional Release |

## 6. Externe Abhängigkeiten

**App (Gradle, aufgelöst — verifiziert):** `androidx.core:core-ktx:1.13.1`,
`androidx.appcompat:appcompat:1.7.0`,
`androidx.lifecycle:lifecycle-runtime-ktx:2.8.3`,
`com.google.android.material:material:1.12.0`, `kotlin-stdlib:1.9.24` (transitiv).

**Engine (npm, aus `shinon-forge` main `59a86a4`):** `@deepseek-ai/dsh`
`0.2.1-alpha.1`, `@deepseek-ai/schemastery ~3.18.4`. Node `^22.19.0 || >=24.0.0`.

**Native Anteile der Engine (per `npm view` geprüft, siehe
[`KNOWN-LIMITATIONS.md`](KNOWN-LIMITATIONS.md) B-4):** `koffi 3.1.1`
(`dsh-fs-local`, `dsh-subprocess-local`), `node-pty 1.2.0-beta.15`
(`dsh-subprocess-local`), `sharp ^0.35.3` (`dsh-attachment-local`),
`node-addon-require-builtin ^0.1.6` (`dsh`).

`androidx.webkit:webkit` war deklariert, wurde aber nirgends verwendet und ist
entfernt — samt der zugehörigen ProGuard-Regel. Beleg: [`KNOWN-LIMITATIONS.md`](KNOWN-LIMITATIONS.md) N-4.

## 7. Prozessgrenzen und Android-Restriktionen

- **Ein** Kindprozess (Node). Kein Daemon-Cluster, keine Services-Worker.
- Der Dienst läuft mit `foregroundServiceType="dataSync"` und `START_STICKY`.
- Es ist **keine** `WAKE_LOCK`-Berechtigung mehr deklariert: kein Code hält
  einen Wakelock. Die Service-Laufzeit hängt damit vollständig an
  Doze-/OEM-Regeln — das ist der Ist-Zustand, kein geprüftes Verhalten.
- Ein Kindprozess unter Android erbt die App-Sandbox; ausführbare Dateien aus
  dem privaten Verzeichnis sind zulässig, viele glibc-Binaries aber nicht
  lauffähig (Bionic).
