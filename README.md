# Shinon Agent

Android-Shell für **[Shinon Forge](https://github.com/vannon091118/shinon-forge)** (Engine) und **DSH**.
Die App startet die Engine als Foreground-Service und zeigt die Weboberfläche
in einer WebView. Die App ist **nicht** die Engine: Engine und Vendor
(`node_modules`) liegen zur Laufzeit im App-Speicher, nie in der APK.

- Kotlin-Shell: `app/src/main/java/com/vannon/shinon/`
- Paket: `com.vannon.shinon` · `minSdk 26` · `targetSdk 34` · `compileSdk 34`
- Lizenz: MIT (`LICENSE`)

## Status — Stand 2026-10-14

**Ausgangsstand:** `e78ca1a` (== `origin/main`).
**Aussagekraft:** Jeder Status unten ist am Code oder durch einen ausgeführten
Befehl belegt. Was nicht ausgeführt werden konnte, steht auf `BLOCKED` und
nicht auf `PASS`. Details: [`docs/TESTING.md`](docs/TESTING.md).

| Gate | Umfang | Status | Nachweis |
|---|---|---|---|
| 0 | Repository + Build-Umgebung | **PASS** | JDK 17.0.20.1, Android SDK 34, Gradle 8.7, Kommando läuft |
| 1 | Compiler + statische Integrität | **PASS** | `:app:assembleDebug` kompiliert; 5 Fehler behoben |
| 1b | Lint | **BLOCKED** | Prozess im Container per OOM-Killer beendet (Exit 137) |
| 2 | Debug-APK + Inhalt | **PASS** | `app-debug.apk`, 5.649.778 Bytes, SHA256 `b83615ae…cd6f` |
| 3 | Runtime-Smoke (Gate A) auf Android | **BLOCKED** | kein Gerät, `/dev/kvm` nicht zugänglich, kein `mobile`-Profil |
| 4 | Provider-Aufruf (Gate B) | **BLOCKED** | keine Zugangsdaten, keine laufende Runtime |
| 5 | Release | **PARTIAL** | Fail-closed verifiziert, R8-Lauf grün; kein signiertes APK (keine Secrets) |

**Kurzfassung des ehrlichen Stands:** Die App **baut** und erzeugt ein
installierbares Debug-APK. Sie **startet die Engine noch nicht**: Die
Runtime-Installation ist ein Platzhalter, der API-Key erreicht den Prozess
nicht, und das im Code fest verdrahtete Profil `mobile` existiert in
`shinon-forge` noch nicht (dort nur geplant, siehe `docs/KNOWN-LIMITATIONS.md`).

## Voraussetzungen

| Werkzeug | Fassung | Warum |
|---|---|---|
| JDK | 17 | AGP 8.5 / Kotlin 1.9 (`compileOptions` VERSION_17) |
| Android SDK | `platforms;android-34`, `build-tools;34.0.0`, `platform-tools` | `compileSdk 34` |
| Gradle | 8.7 (über `./gradlew`) | `gradle/wrapper/gradle-wrapper.properties` |
| Node.js (nur Engine-Seite) | `^22.19.0 \|\| >=24.0.0` | `engines.node` von `shinon-forge` |

## Build

```bash
scripts/setup-toolchain.sh     # einmalig: JDK 17 + Android SDK nach .local/
source .local/env.sh          # JAVA_HOME/ANDROID_HOME setzen

./gradlew :app:assembleDebug  # Debug-APK (empfohlen mit Speicherdeckel: s. u.)
scripts/build.sh :app:assembleDebug
```

Ausgabe: `app/build/outputs/apk/debug/app-debug.apk`

**Speicherhinweis:** `gradle.properties` setzt `-Xmx2048m`. In Umgebungen mit
wenig RAM beendet der OOM-Killer den Build (Exit 137). `scripts/build.sh` deckelt
Heap und Worker-Anzahl und ist in dieser Umgebung verifiziert durchgelaufen.
Details: [`docs/SETUP-AND-RUNTIME.md`](docs/SETUP-AND-RUNTIME.md).

**Release** ist fail-closed: ohne `SHINON_KEYSTORE_*`-Secrets bricht der Build
ab und es wird **kein** ungesigniertes APK erzeugt. Siehe
[`docs/CI-AND-RELEASE.md`](docs/CI-AND-RELEASE.md).

## Was die App tut

1. `SetupActivity` legt `filesDir/runtime/` an und setzt das `setup_done`-Flag.
2. `MainActivity` startet den `ShinonService` und lädt die READY-URL in die WebView.
3. `ShinonService` startet `node` gegen `filesDir/runtime/shinon-forge/` und
   wartet auf die READY-Zeile `dsh web: http://…`.
4. `ShinonApp`/`ShinonKeystore` soll den Provider-Schlüssel im Android Keystore halten.

## Was die App bewusst nicht ist

- Kein Dateimanager, kein Terminal, keine Device-Tools (v1-Nicht-Ziele,
  [`docs/EXTENSIONS-PLAN.md`](docs/EXTENSIONS-PLAN.md)).
- Kein Capacitor/React Native, kein DSH-Fork.
- Kein Runtime-Binary und kein `node_modules` in der APK
  (Entkopplungsvertrag, [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)).

## Dokumentation

| Datei | Inhalt |
|---|---|
| [`docs/SCOPE.md`](docs/SCOPE.md) | Muss/Soll/Später/Nicht + Scope-Matrix mit IDs |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Komponenten, Prozessgrenzen, Datenfluss, Fehlerpfade |
| [`docs/SETUP-AND-RUNTIME.md`](docs/SETUP-AND-RUNTIME.md) | Toolchain, Build, Runtime-Pfade, Logs, Wiederherstellung |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Key-Lebenszyklus, Keystore, WebView, Logging, Bedrohungsmodell |
| [`docs/TESTING.md`](docs/TESTING.md) | Gates 0–5, ausgeführte Kommandos, echte Ergebnisse |
| [`docs/CI-AND-RELEASE.md`](docs/CI-AND-RELEASE.md) | Workflow, Signing, Artefakte, Release-Gates |
| [`docs/KNOWN-LIMITATIONS.md`](docs/KNOWN-LIMITATIONS.md) | Offene Blocker + konkrete nächste Schritte |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Architekturentscheidungen (ADR), offene Entscheidungen |
| [`docs/TRACEABILITY.md`](docs/TRACEABILITY.md) | Anforderungs-ID → Code → Test → Gate |
| [`docs/EXTENSIONS-PLAN.md`](docs/EXTENSIONS-PLAN.md) | Entwurf für Erweiterungen nach v1 |
| [`docs/archive/S0-BESTANDS-AUFNAHME.md`](docs/archive/S0-BESTANDS-AUFNAHME.md) | Historische Bestandsaufnahme (überholt, archiviert) |
