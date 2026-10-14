# Setup und Runtime — Shinon Agent

> Stand: 2026-10-14 · Alle Kommandos wurden in dieser Umgebung ausgeführt,
> sofern nicht anders markiert.

## 1. Toolchain ohne Root installieren

Die Umgebung hat kein `sudo` (`no new privileges`). JDK und Android SDK werden
deshalb benutzerlokal abgelegt (von `.gitignore` gedeckt):

```bash
scripts/setup-toolchain.sh    # lädt Temurin JDK 17 + Android cmdline-tools,
                             # installiert platform-34/build-tools 34.0.0,
                             # schreibt local.properties (sdk.dir=…)
source .local/env.sh         # JAVA_HOME, ANDROID_HOME, ANDROID_SDK_ROOT, PATH
```

Nach einem Wechsel der Maschine/einem Restore ist `.local/` leer und der
Gradle-Cache leer — dann `setup-toolchain.sh` erneut ausführen (ca. 900 MB
Download) und den Build wiederholen. `node_modules`-Caches und `.local/` sind
bewusst **nicht** versioniert.

Installierte Fassungen (verifiziert):

| Komponente | Fassung |
|---|---|
| Temurin JDK | 17.0.20.1 |
| Android SDK Build-Tools | 34.0.0 |
| Android SDK Platform | android-34 (rev 3) |
| Platform-Tools | 37.0.1 |
| Gradle | 8.7 (`gradle/wrapper/gradle-wrapper.properties`) |
| Android Gradle Plugin | 8.5.0 |
| Kotlin | 1.9.24 |

## 2. Build — verifizierte Kommandos

```bash
# 1) Abhängigkeiten auflösen (verteilt keine APK)
scripts/build.sh :app:dependencies --configuration debugRuntimeClasspath
#    → BUILD SUCCESSFUL

# 2) Kompilieren + Debug-APK bauen
scripts/build.sh :app:assembleDebug
#    → BUILD SUCCESSFUL, app/build/outputs/apk/debug/app-debug.apk
```

**Speicherdeckel — warum `scripts/build.sh` existiert.**
`gradle.properties` setzt `org.gradle.jvmargs=-Xmx2048m`. In dieser
Umgebung (3,8 GB RAM, davon ~2,4 GB Page-Cache in derselben Memory-Cgroup)
beendet der OOM-Killer den Build: Kernel-Log `Memory cgroup out of memory`,
Shell-Exit 137. `scripts/build.sh` setzt `-Xmx768m`, `MaxMetaspaceSize=256m`,
`--max-workers=1`, Kotlin `in-process` und `org.gradle.vfs.watch=false`.
Damit läuft `:app:assembleDebug` reproduzierbar durch.
Die Überschreibung wurde am laufenden Daemon kontrolliert
(`ps -eo cmd | grep GradleDaemon` zeigte `-Xmx768m`).

**Grenze der Umgebung:** `:app:lintDebug` wurde ebenfalls versucht und vom
OOM-Killer beendet (Exit 137) — Lint ist hier **nicht** ausführbar. Das ist
ein Umgebungsdefekt, kein Lint-Befund; auf einem Runner mit mehr RAM gehört
Lint in Gate 1.

## 3. Runtime-Pfade (Soll)

| Pfad | Inhalt | Wer schreibt |
|---|---|---|
| `filesDir/runtime/` | Runtime-Wurzel | `SetupActivity` |
| `filesDir/runtime/node` | Node-Binary (ARM64, Bionic) | geplant: Runtime-Installation |
| `filesDir/runtime/shinon-forge/` | Engine (`cwd` des Kindprozesses) | geplant |
| `filesDir/runtime/shinon-forge/node_modules/.bin/dsh` | DSH-Entry-Point | geplant |

Der Kindprozess startet mit `cwd = filesDir/runtime/shinon-forge`. DSH erwartet
laut `bin/shinon.mjs` `DSH_HOME=<Repo-Root>`; **die App setzt `DSH_HOME` nicht**.
Das ist ein offener Punkt (siehe [`KNOWN-LIMITATIONS.md`](KNOWN-LIMITATIONS.md) B-3).

## 4. Engine-Seite (shinon-forge) — geprüfter Stand

Quelle: Klon von `https://github.com/vannon091118/shinon-forge` (main `59a86a4`,
nur zum Lesen nach `.local/audit/` kopiert, nicht im Repo):

| Punkt | Befund |
|---|---|
| `engines.node` | `^22.19.0 \|\| >=24.0.0` |
| Start-Einstieg | `bin/shinon.mjs` → `node <bin.js> --profile <aktiv>`, `DSH_HOME=Repo-Root` |
| Exit-Code bei Umgebungsfehler | `2` (fail-closed) |
| Profile vorhanden | `profiles/shinon`, `profiles/headless` |
| Profil `mobile` | **existiert nicht** — nur in `docs/MOBILE-PLAN.md` als Plan (W1) |
| Ältere Pin-Angabe `develop@d7d38ce` | **nicht existent**: `ls-remote` kennt keinen Branch `develop`, der Commit liefert 404 |

## 5. Starten und Stoppen (Soll)

- Start: `MainActivity` → `startForegroundService(ACTION_START)`.
- Stopp: `ACTION_STOP` → `destroy()` → 3 s Frist → `destroyForcibly()`.
- Neustart: `ACTION_RESTART` bzw. automatisch bei Exit ≠ 0, max. 3 Versuche.
- Status: `ACTION_STATUS` ist als Konstante vorhanden, aber **nicht**
  implementiert (kein Zweig in `onStartCommand`).

## 6. Logs und Diagnose

- Engine-stdout wird zeilenweise gelesen und mit `maskSecrets()` maskiert ins
  Logcat geschrieben; die READY-URL selbst wird **nicht** geloggt (nur der Port).
- Bei `runtime_missing` nennt das Log die geprüften Pfade und deren Existenz —
  die direkteste Diagnose für Gate 3.
- Es gibt keine Datei-Logs und keinen Crash-Report (geplant, siehe
  [`EXTENSIONS-PLAN.md`](EXTENSIONS-PLAN.md) §4).

## 7. Wiederherstellung

| Situation | Vorgehen |
|---|---|
| Build bricht mit Exit 137 ab | `scripts/build.sh` verwenden (Speicherdeckel) |
| `./gradlew` findet Gradle nicht | Wrapper-Defekt, Fix in [`DECISIONS.md`](DECISIONS.md) DEC-001 |
| `sdk.dir` fehlt / falscher Pfad | `scripts/setup-toolchain.sh` erneut ausführen |
| APK bauen, aber Runtime fehlt | erwartet: App meldet `runtime_missing` (kein Absturz) |
| Repo-Zustand zurücksetzen | Sicherung in `.local/backup/` (siehe [`TESTING.md`](TESTING.md) §Sicherung) |
