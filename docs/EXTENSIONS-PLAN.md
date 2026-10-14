# Planung: Erweiterungen jenseits der W4-Shell

> **Klarstellung zuerst:** `Shinon_Agent` ist der **parallele zweite
> Zweig von Shinon Forge** — er konzentriert sich auf die
> **App-Entwicklung** (Android-Shell, WebView, Foreground-Service,
> Release-Flow). Das ist die W4-Abnahme aus `MOBILE-PLAN.md §5`.

Die hier geplante Integration — **Dateimanager, Terminal,
Device-Tools** — ist **kein Teil der W4-Shell**. Sie ist ein
bewusster **Nicht-Ziel von v1** (MOBILE-PLAN.md §7 W4-Nicht-Ziele:
„Kein Dateimanager, kein Terminal, keine privilegierten Device-Tools"),
weil sie drei Dinge bringt, die v1 bewusst weglässt:

- **Angreifungsfläche** — ein Dateimanager und Terminal brauchen
  privilegierte Rechte (`READ_EXTERNAL_STORAGE`, `WRITE_EXTERNAL_STORAGE`,
  `MANAGE_EXTERNAL_STORAGE`), die das Security-Vertrag von v1
  („WebView darf nur auf `http://127.0.0.1:…` navigieren, externe
  Links → Systembrowser") aufbrechen würden.
- **Komplexität** — ein Terminal im WebView-Stapel ist ein zweiter
  Host (kein Node-Prozess mehr, sondern ein Shell-Process-Manager),
  der den simplen Foreground-Service von W4 sprengt.
- **Vertrauensmodell** — die App wäre dann nicht mehr „eine kompatible
  Shinon-Runtime starten und die Weboberfläche rendern", sondern
  „ein volles Android-Device-OS mit privilegierten Tools". Das ist
  ein anderes Produkt, mit anderem Testumfang (Gate `android-device-smoke`
  wird zum Full-Device-Test, nicht nur zum WebView-Smoke).

**Status: Entwurf (nicht umgesetzt, nicht abgenommen, nicht blockierend
für v1).** Die W4-Abnahme ist unverändert:
„Eine Android-App startet eine kompatible Shinon-Runtime, DSH lädt
nachweislich das Mobile-Profil, der lokale Server liefert die
Weboberfläche aus und die App kann den Dienst kontrolliert stoppen
und wieder starten."

---

## 1. Wann diese Erweiterungen in den Fokus kommen

Nicht „nach v1", sondern **nach dem ersten Live-Test** (Gate
`android-build` grün, `v0.0.1`-APK auf einem echten Device
installiert und gelaufen). Konkret:

1. **Gate `android-device-smoke` ist required** (MOBILE-PLAN.md §5 W3:
   „nach stabiler Runner-Verfügbarkeit schrittweise required").
2. **Der erste Update-Mechanismus** (MOBILE-PLAN.md §5 W4: „dann
   Updates mit Prüfsummen, validierter Version und Rollback")
   steht — bevor man neue Host-Features auf eine noch volatile
   Runtime baut.
3. **Die Third-Party-Lizenzen** (MOBILE-PLAN.md §5 W4: „Third-Party-
   Notices im Release-Flow") sind im Release-Flow verdrahtet —
   Dateimanager und Terminal ziehen Libraries (z. B. `Termux`,
   `Android-Storage-Abstraction`), deren Lizenz-Status geprüft sein
   muss.

Bis dahin bleibt v1 beim Nicht-Ziel. Die Planung hier ist die
**Schnittstelle** für den Moment, an dem diese Entscheidungen fallen.

## 2. Dateimanager (Entwurf)

**Was er tut:** Die App zeigt das `filesDir/runtime/shinon-forge/`
und das `filesDir/workspace/` (DSH-Workspace) an, mit Dateideletion
und -Umbenennung (kein `cp`/`mv` auf `/sdcard` — die Engine braucht
kein externes Laufwerk, nur den internen Speicher).

**Schnittstellen (Kotlin):**
- `FileBrowserFragment` (AndroidX `fragment`) — zeigt eine
  `RecyclerView` mit Dateieinträgen (Name, Größe, Datum, Icon).
- `FileOperations.kt` — `delete(path)`, `rename(old, new)`,
  `read(path)` (nur für `filesDir/`, nie `/sdcard`).
- `Manifest`: `READ_EXTERNAL_STORAGE` wird **nicht** angefordert
  (v1-Security-Vertrag bleibt intakt — der Dateimanager ist
  auf den App-internen Speicher beschränkt).

**Gate (neuer Zweig, fail-closed):**
- `android-build`: FileBrowser-Layout + `FileOperations`-Unit-Tests
  (Pfad-Trip, Rechte-Check, leere Verzeichnisse).
- `android-device-smoke`: „Datei wird im Browser korrekt gelistet,
  umbenannt und gelöscht — kein Crash, keine Berechtigungs-
  Abfrage (Permission Denied im Log wäre ein Befund)".

**Security-Vertrag (bewusst, kein Dranbei):**
- `FileOperations` darf **nicht** auf `/sdcard` oder `Environment.
  getExternalStorageDirectory()` zugreifen — nur `filesDir/`.
  Ein Dateidelete auf dem externen Laufwerk wäre ein Bug, nicht
  eine Feature.
- Die WebView bekommt keinen Dateizugriff (`allowFileAccess = false`
  in `MainActivity.kt`, bleibt so).

## 3. Terminal (Entwurf)

**Was es tut:** Ein zweites Host-Element neben dem Foreground-Service
— ein `TerminalFragment` mit `RecyclerView` (Linien) + `EditText`
(Eingabe). Der Terminal-Host ruft `sh -c` (kein `bash`, Android
hat kein glibc-Shell-Ökosystem) auf und zeigt die Ausgabe.

**Schnittstellen (Kotlin):**
- `TerminalHost` (neues Objekt neben `ShinonService`) — startet
  einen `ProcessBuilder("sh", "-c", command)` im internen
  Speicher (`filesDir/`), mit `redirectErrorStream(false)`.
- `TerminalFragment` — zeigt die Ausgabe (max. 500 Zeilen, older
  werden geschnitten), die `EditText` schickt an den Host.
- `Manifest`: **neue Permission** `INTERNET` bleibt, aber
  **keine** privilegierten Rechte — der Terminal ruft nur `sh`
  auf (kein `adb`-Level, kein `system`-Shell).

**Gate (neuer Zweig, fail-closed):**
- `android-build`: `TerminalHost`-Unit-Tests (Kommando-Eingabe,
  langer Output (Zeilen-Schnitt), Prozessende (SIGTERM sauber)).
- `android-device-smoke`: „Terminal zeigt `echo test` korrekt
  (kein Crash, kein leeres Ergebnis), `ls` zeigt den internen
  Speicher (kein `/sdcard`-Aufruf im Log)".

**Security-Vertrag (bewusst, kein Dranbei):**
- Der Terminal ruft **nur** `sh -c` auf — kein `bash`, kein
  `python3` (nicht auf dem Device), kein `adb`-Access.
- Die Ausgabe wird **nicht** in die App-Logs (Secret-Vertrag von
  v1 bleibt intakt — ein Terminal-Output mit API-Keys wäre ein
  Befund).

## 4. Device-Tools (Entwurf)

**Was es tut:** Ein `SettingsFragment` mit Toggle für:
- **Auto-Start nach Reboot** (`BootReceiver` + `Shadows`/`WorkManager`
  — der Foreground-Service startet nach einem Device-Neustart,
  ohne dass der Nutzer die App öffnet).
- **Doze-Modus-Override** (`WAKE_LOCK` bleibt, aber der `WorkManager`
  bekommt einen `Constraints.NETWORK_TYPE_UNMETERED`-Trigger, damit
  der Provider-Aufruf nicht stumm im Doze-Modus stirbt).
- **Crash-Diagnose** (ein `FileWriter` schreibt den letzten
  `Log.d`-Tag an `filesDir/diagnosis/last-crash.txt`, max.
  50 KB, nicht in `/sdcard`).

**Schnittstellen (Kotlin):**
- `BootReceiver` (neue `BroadcastReceiver`) — antwortet auf
  `Intent.ACTION_BOOT_COMPLETED` und startet den `ShinonService`.
- `DiagnosisWriter` (neues Objekt) — schreibt `Log.d`-Zeilen
  in ein lokales Datei-Buffer, beim Crash `System.exit()` wird
  der Buffer nach `filesDir/diagnosis/` gespendet.
- `Manifest`: **neue Permission** `RECEIVE_BOOT_COMPLETED`
  (Android 8+, keine privilegierte Rechtereste — nur der
  Broadcast).

**Gate (neuer Zweig, fail-closed):**
- `android-build`: `BootReceiver`-Unit-Test (Broadcast `ACTION_
  BOOT_COMPLETED` → Service gestartet, kein Crash), `DiagnosisWriter`-
  Unit-Test (Crash → Datei existiert, max. 50 KB, kein `/sdcard`).
- `android-device-smoke`: „Device wird neu gestartet (kein
  Factory Reset), die App startet automatisch den Foreground-Service
  (kein manueller Klick), das `filesDir/diagnosis/last-crash.txt`
  existiert nach einem simulierten Crash (kein leeres Ergebnis)".

**Security-Vertrag (bewusst, kein Dranbei):**
- Der `DiagnosisWriter` schreibt **nur** `filesDir/diagnosis/`
  — nie `/sdcard/diagnosis/` (kein exfiltrierbares Verzeichnis).
- Der `BootReceiver` startet **nur** den `ShinonService` — kein
  zweiter Prozess, keine privilegierten Rechte.

## 5. Abhängigkeiten (wer blockiert wen)

```
W4-Shell (v0.0.1, Live-Test)
   └── Gate android-device-smoke required (Runner steht)
        └── Update-Mechanismus (Prüfsummen + Rollback)
             └── Third-Party-Lizenzen im Release-Flow
                  ├── Dateimanager (FileBrowserFragment + FileOperations)
                  ├── Terminal (TerminalHost + TerminalFragment)
                  └── Device-Tools (BootReceiver + DiagnosisWriter)
```

**Keine der drei Erweiterungen darf vor dem Update-Mechanismus
starten** — sonst hätte man ein Update auf eine App, die neue
Privilegien braucht, ohne dass der Nutzer weiß, welche
Permission neu ist (Security-Vertrag: „niemals im Build, niemals
im Repo, niemals in der URL" gilt auch für den Update-Flow —
ein Update, das neue Permissions anfordert, muss im
Update-Dialog transparent sein, nicht im stillen `WorkManager`).

## 6. Was NIE in Shinon_Agent kommt (bewusst)

- **Capacitor / React Native / Framework-Overhead** (MOBILE-PLAN.md
  §1: „kein Capacitor, kein React Native, kein Framework-Overhead").
- **DSH-Fork** (MOBILE-PLAN.md §1: „kein DSH-Fork" — die Engine
  bleibt `shinon-forge`, die App ist nur die Shell).
- **Dateimanager auf `/sdcard`** (v1-Security-Vertrag: nur
  App-interner Speicher, Bionic, kein glibc-Linux-Binary).
- **Privilegierte Device-Tools** (kein `adb`-Access, kein
  `system`-Shell, kein `root` — der Terminal ruft nur `sh -c`
  auf, kein `bash`).

## 7. Entscheider (wer was freigibt)

| Entscheidung | Wer | Wann |
|---|---|---|
| Dateimanager-Scope (nur `filesDir/`) | Vannon (Indie-Dev) | Vor dem ersten `FileBrowserFragment`-Commit |
| Terminal-Kommandos (nur `sh -c`) | Vannon (Indie-Dev) | Vor dem ersten `TerminalHost`-Commit |
| Device-Tools (Boot, Doze, Crash) | Vannon (Indie-Dev) | Vor dem ersten `BootReceiver`-Commit |
| Neue Permissions (`READ_EXTERNAL_STORAGE`, `RECEIVE_BOOT_COMPLETED`) | Vannon (Indie-Dev) | Vor dem CI-Zweig, der die Extension-Tests (Gate `android-build`) freischaltet |

**Keine der drei Erweiterungen wird abgenommen, bis der W4-Live-
Test (v0.0.1 auf einem echten Device) bestanden ist.** Das ist
bewusst — kein Dranbei-Feature, das einen nicht getesteten
Grundzustand erweitert.

## 8. Nächster Schritt (konkret, kein „irgendwann")

1. **v0.0.1-Release** (CI grün, `gh release create v0.0.1`) —
   das APK ist der einzige, gemessene Live-Test-Punkt.
2. **Erster Live-Test auf einem echten Device** (Gate
   `android-device-smoke` manuell, kein Runner) — der Befund
   („läuft / crash-t / Provider-Aufruf stirbt im Doze-Modus")
   ist der einzige, der die hier geplante Entscheidung
   freigibt (Update-Mechanismus → Lizenzen → Extension).
3. **Erst dann** (nach dem Live-Test): `git tag v0.0.2-pre`
   (v0.0.2-Pre-Alpha mit Dateimanager), Gate `android-build`
   blockiert ab `v0.0.2`, Gate `android-device-smoke` wird
   required (Runner steht), die hier geplante Entscheidung
   (Update-Mechanismus → Lizenzen → Extension) ist gefallen.

**Die W4-Shell (v0.0.1) bleibt die einzige, abgenommene
App-Version. Die hier geplante Extension ist eine Schnittstelle,
kein Teil der v1-Abnahme.**
