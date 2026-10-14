# Testing und Gates — Shinon Agent

> Stand: 2026-10-14 · Jedes Ergebnis unten stammt aus einem **hier ausgeführten**
> Kommando. Nicht ausführbare Prüfungen stehen auf `BLOCKED`, nie auf `PASS`.

## 1. Gate-Definition

| Gate | Umfang | Voraussetzung | Kommando | Erwartet | Fehlerstatus | Artefakt |
|---|---|---|---|---|---|---|
| **0** | Repo + Build-Umgebung | Netz, Schreibrechte | `scripts/setup-toolchain.sh` | Toolchain installiert | Abbruch = FAIL | `.local/toolchains`, `.local/android-sdk` |
| **1** | Compiler + statische Integrität | Gate 0 | `scripts/build.sh :app:assembleDebug` | `BUILD SUCCESSFUL` | Compile-Fehler = FAIL | `.local/build*.log` |
| **1b** | Lint | Gate 0 + RAM | `scripts/build.sh :app:lintDebug` | Report erzeugt | — | `app/build/reports/lint-results-debug.*` |
| **2** | APK-Build + Inhalt | Gate 1 | `:app:assembleDebug` + `unzip -l` + Entkopplungsgate | APK existiert, Gate leer | Treffer = FAIL | `app/build/outputs/apk/debug/app-debug.apk` |
| **3** | Runtime-Smoke (Gate A) | Gerät/Emulator + Runtime-Paket | App installieren, Dienst starten | READY-URL erscheint | Timeout/`runtime_missing` = FAIL | Logcat, Screenshot |
| **4** | Provider (Gate B) | Gate 3 + gültige Zugangsdaten | Chat im WebView | echte Antwort; Auth-Fehler unterscheidbar | kein Aufruf = FAIL | Provider-Log |
| **5** | Release | Secrets + Gates 1–4 | CI-Workflow `build` | signiertes APK + Prüfsumme | fehlendes Secret = FAIL (fail-closed) | GitHub-Release |

**Regel:** Gate 3 und Gate 4 sind unabhängig. Ein grüner Runtime-Start färbt
Gate 4 nicht grün und umgekehrt.

## 2. Sicherungsprotokoll (Phase A, ausgeführt)

| Schritt | Datei | Beleg |
|---|---|---|
| Branch + Commits | `.local/backup/HEAD.txt` | `branch: freebuff/26b468caadd46c8f77ba61d9`, `head: e78ca1af…`, `origin/main: e78ca1af…`, `parent-base: be96f2b3…` |
| Uncommitted Patch (binärsicher) | `.local/backup/uncommitted.patch` | `git apply --reverse --check` → **PATCH OK** |
| Vollständiger Status | `.local/backup/status.txt` | |
| Stashes | `.local/backup/stashes.txt` | leer (keine Stashes vorhanden) |
| Refs | `.local/backup/refs.txt` | |
| Untracked Dateien | `.local/backup/untracked-list.txt` + `untracked.tgz` | **0 Einträge** — es existierten keine untracked Dateien außer `.local/` |

Es wurden **keine** destruktiven Befehle verwendet (`reset --hard`, `clean -fd`,
Force-Resets). Alle Sicherungen sind lesbar geprüft.

## 3. Ausgeführte Prüfungen und echte Ergebnisse

### Gate 0 — Repository und Build-Umgebung: **PASS**

```bash
./gradlew --version      # Gradle 8.7, JVM 17.0.20.1 (Temurin)
sdkmanager --list_installed
# build-tools;34.0.0 | platform-tools 37.0.1 | platforms;android-34 (rev 3)
```

### Gate 1 — Compiler: **FAIL → PASS** (nach Reparatur)

| Zeitpunkt | Ergebnis |
|---|---|
| vor der Reparatur | `:app:compileDebugKotlin FAILED` — 5 Fehler in `ShinonApp.kt` (3) und `ShinonService.kt` (2) |
| nach der Reparatur | `scripts/build.sh :app:assembleDebug` → **BUILD SUCCESSFUL in 26s** |

Die Reparaturen sind in [`DECISIONS.md`](DECISIONS.md) DEC-004 und DEC-007
dokumentiert. Der Commit `e78ca1a` trug die Botschaft „Compiler-Fehler beheben“,
der Build war danach trotzdem rot — die Botschaft war unzutreffend.

### Gate 1b — Lint: **BLOCKED**

```
timeout 170 scripts/build.sh :app:lintDebug   →  Killed (Exit 137)
Kernellog: "Memory cgroup out of memory"
```

Lint war in dieser Umgebung **nicht** ausführbar. Das ist ein Umgebungsdefekt,
kein Lint-Befund: es wurde kein Report erzeugt, also ist auch keine Aussage
über Lint-Verstöße möglich. Kein `PASS`.

### Gate 2 — Debug-APK und Inhalt: **PASS**

```
:app:assembleDebug                     →  BUILD SUCCESSFUL
app-debug.apk                          →  5.649.778 Bytes, 889 Einträge
SHA256                                 →  b83615ae2673b844ecb0919312c7a87f36652af8851ef57c481e9405669bcd6f
classes.dex, classes2.dex, classes3.dex, AndroidManifest.xml, resources.arsc   →  vorhanden
res/layout/activity_main.xml, res/layout/activity_setup.xml, ic_launcher*      →  vorhanden
lib/**/*.so                            →  keine (keine nativen Anteile in der App)
```

**Entkopplungsgate, nachgebaut am echten Artefakt:**

```
unzip -l app-debug.apk | grep -Ei 'node_modules|shinon-forge|/dsh|profile[s]?/mobile'
→ kein Treffer  ⇒  GATE PASS
```

**Signatur (Debug):** `apksigner verify` bestätigt
`CN=Android Debug, O=Android, C=US`, SHA-256
`e01135106fd03903e0772c2d9b809cdcb8591f25aefcc124d91f1fb6ac3a1487`.

**Manifest im APK (`aapt2 dump badging`):**

```
package: name='com.vannon.shinon' versionCode='1' versionName='0.0.1'
sdkVersion:'26'   targetSdkVersion:'34'
uses-permission: INTERNET, FOREGROUND_SERVICE,
                 FOREGROUND_SERVICE_DATA_SYNC, POST_NOTIFICATIONS,
                 com.vannon.shinon.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION
application-label:'Shinon'
```

### Gate 3 — Runtime-Smoke (Gate A): **BLOCKED**

Nicht ausgeführt. Gründe (jeder einzeln ausreichend):

1. **Kein Gerät, kein Emulator:** `avdmanager list avd` ist leer,
   `sdkmanager --list_installed` enthält **kein** `system-images`.
2. **Kein KVM-Zugriff:** `/dev/kvm` existiert (`root:kvm`, Modus `660`), ist für
   diesen Benutzer aber weder lesbar noch schreibbar (`id`: nur Gruppe
   `freebuff`) — ein Hardware-Emulator ist damit nicht möglich.
3. **Kein Runtime-Paket:** `SetupActivity.installRuntime()` ist ein Platzhalter
   und erzeugt nie einen Marker; es gibt kein Bezugsartefakt.
4. **Kein passendes Profil:** Der Dienst startet `--profile mobile`, das in
   `shinon-forge` nicht existiert (dort nur geplant).

**Was ohne Gerät belegbar wäre und trotzdem fehlt:** ein Node-Lauf auf
Desktop-Linux gegen `shinon-forge` würde den READY-Zeilenformat prüfen, aber
**nicht** die Android-Runtime. Es wurde bewusst nicht als Gate-3-Ersatz
gewertet und die App läuft in einer Android-Prozesssandbox, die nicht simuliert
werden kann.

### Gate 4 — Provider (Gate B): **BLOCKED**

Nicht ausgeführt. Ohne Gate 3 gibt es keinen Prozess, der einen Aufruf machen
könnte; es liegen keine Provider-Zugangsdaten vor, und der Schlüsselpfad ist
nicht implementiert (SEC-KEY-001/002). Ein Desktop-Provider-Test würde keinen
Android-Runtime-Start beweisen und wurde deshalb nicht als Ersatz geführt.

### Gate 5 — Release: **PARTIAL** (fail-closed verifiziert)

```
:app:validateSigningRelease
→ BUILD FAILED: "Keystore file '…/app/keystore/release.jks' not found for signing config 'release'."
→ Exit 1

:app:minifyReleaseWithR8
→ BUILD SUCCESSFUL in 2m 5s (28 Tasks, 2 ausgeführt, kein "Missing class")
→ Release-Kompilierung und die geänderten ProGuard-Regeln sind damit belegt
```

Damit ist das **Fail-closed-Verhalten bewiesen**: ohne Keystore-Secrets entsteht
kein Release-Artefakt. Der **Gegenbeweis fehlt**: ein erfolgreich signierter
Release-Lauf wurde nicht ausgeführt (keine Secrets vorhanden, R8-Minifizierung
in dieser Umgebung nicht getestet).

### CI-Beobachtung (nicht selbst ausgeführt)

Laut `https://github.com/vannon091118/Shinon_Agent/actions` sind **alle** dort
angezeigten Läufe fehlgeschlagen, zuletzt Workflow `build` **#10** am
2026-10-14. Diese Angabe stammt aus der GitHub-Oberfläche und ist **nicht** in
dieser Umgebung nachgemessen — sie ist als Beobachtung gekennzeichnet, nicht
als eigenes Testergebnis.

## 4. Testabdeckung

| Bereich | Automatisierte Tests |
|---|---|
| Kotlin-Logik (`ShinonService`, `ShinonApp`, Activities) | **keine** — `app/src/test` existiert nicht |
| Instrumentierte Tests (`app/src/androidTest`) | **keine** |
| Build/Artefakt | Gate 1/2 (lokale Kommandos, kein CI-Job für Debug) |
| Entkopplung | CI-Step + lokaler Nachbau am Artefakt |

Es gibt derzeit **keine** Unit-Tests im Repository. Das ist kein Messergebnis,
sondern ein Befund: jede Verhaltensaussage in der Doku ist damit statisch
(codebasiert) oder gar nicht belegt. Kandidaten für die ersten Tests sind in
[`TRACEABILITY.md`](TRACEABILITY.md) §4 benannt.

## 5. Reproduktion dieser Prüfungen

```bash
scripts/setup-toolchain.sh
source .local/env.sh
scripts/build.sh :app:dependencies --configuration debugRuntimeClasspath   # Gate 1-Vorstufe
scripts/build.sh :app:assembleDebug                                        # Gate 1 + 2
unzip -l app/build/outputs/apk/debug/app-debug.apk \
  | grep -Ei 'node_modules|shinon-forge|/dsh|profile[s]?/mobile' || echo "Entkopplungsgate PASS"
./gradlew :app:validateSigningRelease                                     # Gate 5 fail-closed
./gradlew :app:minifyReleaseWithR8                                        # Release-Code + R8-Regeln
```
