# Shinon Control Plane · Installation auf Windows 11

> **Zielgruppe:** Endanwender mit Windows 11 (oder Windows 10 ab 21H2), die den
> Shinon Control Plane auf ihrem Rechner laufen lassen möchten.
>
> **Voraussichtliche Dauer:** 15–25 Minuten (inkl. Downloads)
>
> **Letzte Aktualisierung:** 2026-08-12 — getestet mit Windows 11 24H2,
> PowerShell 7.5, Python 3.12.6, Node.js 20.18, Rust 1.97 (auto-installiert).

---

## Inhaltsverzeichnis

1.  [Schnellstart (Copy-Paste Variante)](#1-schnellstart-copy-paste-variante)
2.  [Voraussetzungen im Detail](#2-voraussetzungen-im-detail)
    1.  [Python ohne Microsoft Store](#21-python-ohne-microsoft-store)
    2.  [Node.js LTS installieren](#22-nodejs-lts-installieren)
    3.  [Git for Windows](#23-git-for-windows)
    4.  [Rust-Compiler](#24-rust-compiler)
3.  [PATH-Setup persistent machen](#3-path-setup-persistent-machen)
4.  [Repository klonen](#4-repository-klonen)
5.  [Installer ausführen](#5-installer-ausführen)
6.  [Firewall-Hinweise für Ports 4200 / 4300 / 8000](#6-firewall-hinweise)
7.  [Erste Schritte nach der Installation](#7-erste-schritte)
8.  [Troubleshooting](#8-troubleshooting)
9.  [Komplett deinstallieren](#9-komplett-deinstallieren)

---

## 1. Schnellstart (Copy-Paste Variante)

Wenn du **bereits** Python 3.11+, Node.js 18+ und Git installiert hast und
**kein** Microsoft-Store-Python-Alias aktiv ist:

```powershell
# PowerShell 7+ ALS NORMALER BENUTZER (kein Admin nötig)

# 1) Repository klonen
git clone https://github.com/vannon0911/shinon-control-plane.git
cd shinon-control-plane

# 2) Pre-Flight: prüft ob alles Nötige vorhanden ist
.\install.cmd --check

# 3) Vollinstallation (bei Aufforderung "Ja" zu Admin-Prompt geben,
#    wenn Windows nach Berechtigungen fragt; sonst einfach abwarten)
.\install.cmd

# 4) Onboarding-Wizard startet
.\shinon.cmd --setup
```

Fertig. Wenn Schritt 2 mit `Konfiguration OK` durchläuft, ist alles bereit.

---

## 2. Voraussetzungen im Detail

Die folgende Tabelle fasst zusammen, was installiert sein muss:

| Komponente      | Mindestversion | Empfohlen | Woher                                          |
|-----------------|----------------|-----------|------------------------------------------------|
| Python          | 3.11           | 3.12      | python.org (NICHT Microsoft Store!)            |
| Node.js         | 18             | 20 LTS    | nodejs.org oder `winget install OpenJS.NodeJS` |
| Git             | 2.30           | 2.50+     | git-scm.com (kommt mit Git-Bash)               |
| Rust            | stable         | -         | Auto-install via `winget` oder rustup-init.exe |
| Disk            | 800 MB frei    | 2 GB      | -                                              |
| RAM             | 4 GB           | 8 GB      | -                                              |

### 2.1 Python ohne Microsoft Store

> **Wichtig:** Seit Windows 10 (1903) ist eine "App-Installer"-Funktion
> aktiv, die den Befehl `python` in der PATH-Variable **automatisch auf den
> Microsoft Store umleitet** — selbst wenn du Python schon installiert
> hast. Das ist die häufigste Fehlerquelle bei Shinon-Installationen.
> Symptom: `where python` zeigt auf
> `C:\Users\<USER>\AppData\Local\Microsoft\WindowsApps\python.exe`,
> und jeder `python`-Aufruf öffnet den Store statt Code auszuführen.

#### Variante A — App-Installer-Alias deaktivieren (empfohlen)

```
Einstellungen → Apps → Erweiterte App-Einstellungen
   → "App-Installer für App-Pakete auswählen" steht auf "Immer"
      → hier ändern auf "Entscheiden, was zu tun ist"
```

Oder per PowerShell (Admin):

```powershell
# Öffnet direkt die richtige Einstellungsseite
start ms-settings:appsfeatures-app?app=Python.Python.3.12
```

Dann erscheint eine Liste der Python-Aliase. Schalte die Schalter für
`python.exe`, `python3.exe` und `python.exe (Python Launcher)` auf **AUS**.

#### Variante B — Python direkt von python.org holen

1.  <https://www.python.org/downloads/windows/> öffnen
2.  **"Download Python 3.12.x"** klicken (oder 3.11.x, aber ≥ 3.11)
3.  Installer laufen lassen und **am ersten Dialogscreen**
    **`Add python.exe to PATH`** anhaken ✔️ (Default ist **AUS** — das
    vergessen die meisten!)
4.  "Install Now" klicken
5.  Im Sicherheitsdialog "Yes" wählen (UAC fragt nach Admin-Rechten,
    weil Python in `C:\Program Files\` will)

Verify:

```powershell
python --version
# Erwartet: Python 3.12.6  (oder ähnlich)

where.exe python
# Erwartet:   C:\Users\<USER>\AppData\Local\Programs\Python\Python312\python.exe
# NICHT:      C:\Users\<USER>\AppData\Local\Microsoft\WindowsApps\python.exe

python -c "import sys; print(sys.executable)"
# Sollte NICHT zeigen: ... WindowsApps ...
```

#### Variante C — Python via winget (Enterprise-freundlich)

```powershell
# winget ist seit Windows 10 1709 vorinstalliert
winget install --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
```

#### Variante D — Python via Chocolatey (falls installiert)

```powershell
choco install python312 -y
```

### 2.2 Node.js LTS installieren

```powershell
# Variante 1 — winget (Empfehlung)
winget install --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements

# Variante 2 — manueller Download
# https://nodejs.org/en/download → "Windows Installer (.msi)" → 20.x LTS
```

Verify:

```powershell
node --version    # v20.x.x oder höher
npm --version     # 10.x oder höher
```

### 2.3 Git for Windows

Wird für das Klonen gebraucht. Bringt außerdem Git-Bash mit, was die
Installer-Codebase ab und zu intern benutzt.

```powershell
winget install --id Git.Git --accept-package-agreements --accept-source-agreements
```

Verify:

```powershell
git --version
# git version 2.5x.x.windows.1  (oder ähnlich)
```

### 2.4 Rust-Compiler

Nur nötig, wenn eine Python-Bibliothek (z. B. `tiktoken`) für deine
Python-Version kein fertiges **Wheel** hat — das ist bei **Python 3.14
oder frühen 3.13-Patch-Versionen** möglich. Bei Python 3.12 sollten alle
Pakete bereits vorgebaut sein.

**Der Installer versucht Rust automatisch zu installieren**, bevor er
Pip startet. Es gibt zwei Wege, die er probiert (in dieser Reihenfolge):

1.  **`winget install --id Rustlang.Rustup`** — bevorzugt, da auf
    Windows 11 mit aktivem App-Installer vorinstalliert.
2.  **Fallback: Direkter Download von `rustup-init.exe`** von
    <https://win.rustup.rs/x86_64> → lokal ausführen mit `-y`.

Wenn beide Wege scheitern, gibt der Installer eine Warnung aus und versucht
trotzdem, pip laufen zu lassen — das geht durch, solange die Wheels
vorgebaut sind.

**Manuelle Vorab-Installation** (optional, beschleunigt die erste Shinon-Installation):

```powershell
winget install --id Rustlang.Rustup --accept-package-agreements --accept-source-agreements --silent
```

Verify (nach Schließen + Neuöffnen der PowerShell):

```powershell
rustc --version    # rustc 1.97.x (...)
cargo --version    # cargo 1.97.x (...)
where.exe cargo    # C:\Users\<USER>\.cargo\bin\cargo.exe
```

---

## 3. PATH-Setup persistent machen

Bei der **python.org-Installation** wird Python automatisch in den
**Benutzer-PATH** eingetragen (bei der `winget`-Variante leider nicht
immer —Bug in Microsofts Wrapper). Daher empfehle ich, danach
**explizit zu prüfen**, ob die Pfade stimmen:

```powershell
# Aktuellen PATH inspizieren (sehr lange Liste — | findstr hilft)
$env:PATH -split ';' | Where-Object { $_ -match 'Python|node|cargo|git' }

# Falls etwas fehlt, PERMANENT ergänzen (User-Scope, kein Admin nötig)
[System.Environment]::SetEnvironmentVariable(
    'PATH',
    [System.Environment]::GetEnvironmentVariable('PATH', 'User') + ';C:\Users\<USER>\.cargo\bin',
    'User'
)

# Danach PowerShell-Konsole komplett schließen + neue öffnen, damit
# die Änderung wirksam wird. (PATH aus User-Scope wird nur beim Start
# neuer Prozesse geladen.)
```

**Welche Verzeichnisse sollten im `PATH` sein?**

| Variable           | Pfad                                                        | Herkunft                            |
|--------------------|-------------------------------------------------------------|-------------------------------------|
| Python             | `%LocalAppData%\Programs\Python\Python312\`                 | python.org Installer                |
| Python Scripts     | `%LocalAppData%\Programs\Python\Python312\Scripts\`         | python.org Installer                |
| Node               | `%ProgramFiles%\nodejs\`                                    | Node MSI oder winget                |
| npm global         | `%AppData%\npm\`                                            | Node                                |
| git                | `%ProgramFiles%\Git\cmd\`                                   | Git for Windows                     |
| cargo (Rust)       | `%USERPROFILE%\.cargo\bin\`                                 | rustup / winget Rustlang.Rustup     |

### Wichtige ENV-Variable: `PYTHONIOENCODING`

Neuere Windows-Python-Builds (≥3.12) versuchen Unicode-Emojis in stdout
nach cp1252 zu transcoden — mit 🦇 ✅ 🎉 als Ersatz `?`. Auch nach
`chcp 65001` ist das Verhalten nicht garantiert. Die Installer-Shims
(`install.cmd`, `shinon.cmd`, `ctl.cmd`) setzen daher zusätzlich:

```cmd
set PYTHONIOENCODING=utf-8
```

Das zwingt Python, stdout/stderr fest auf UTF-8 — unabhängig von der
Codepage der CMD-Session. Falls du Shinon direkt aus PowerShell startest
(also ohne die `.cmd`-Shims), setze vorher:

```powershell
$env:PYTHONIOENCODING = "utf-8"
```

**Generischer "PATH-Helfer"-Befehl** (fragt nach Bestätigung, wenn Pfade fehlen):

```powershell
$needed = @(
    "$env:LocalAppData\Programs\Python\Python312",
    "$env:LocalAppData\Programs\Python\Python312\Scripts",
    "$env:ProgramFiles\nodejs",
    "$env:AppData\npm",
    "$env:ProgramFiles\Git\cmd",
    "$env:USERPROFILE\.cargo\bin"
)
$missing = $needed | Where-Object { -not (Test-Path $_) }
if ($missing) {
    Write-Warning "Diese Verzeichnisse existieren nicht:`n  $($missing -join "`n  ")"
    Write-Warning "Installiere die fehlenden Tools zuerst (siehe Abschnitt 2)."
} else {
    Write-Host "Alle erwarteten Pfad-Verzeichnisse vorhanden." -ForegroundColor Green
}
```

---

## 4. Repository klonen

```powershell
# In dein Projekt-Verzeichnis wechseln (Beispiel: C:\Projects)
cd C:\Projects

# Repo klonen
git clone https://github.com/vannon0911/shinon-control-plane.git
cd shinon-control-plane

# Verzeichnisstruktur ansehen
dir
# Erwartet: install.cmd, install.py, ctl.py, shinon.cmd, requirements.txt, ...
```

> **Tipp:** Wenn dein Windows-Benutzername **Umlaute** enthält (z. B.
> "Müller") oder der Projektpfad **sehr lang** ist (> 100 Zeichen),
> können `npm install` und `git submodule` Probleme bekommen. Max-Pfade
> in Windows aktivieren hilft:
>
> ```powershell
> # PowerShell als Admin — Windows 10/11 Long-Path-Support einschalten
> Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1
> ```

---

## 5. Installer ausführen

### 5.1 Pre-Flight (schnell, ohne Installation)

```powershell
.\install.cmd --check
```

**Erwartete Ausgabe (Auszug):**

```
═══ Pre-Flight Checks ═══

  ✅ Python 3.12.6 ≥ 3.11
  ✅ Node v20.18.0 ≥ 18.0.0
  ✅ npm v10.9.0
  ✅ PowerShell vorhanden: C:\Program Files\PowerShell\7\pwsh.exe
  ✅ Disk: 47382 MiB frei (≥ 800)
  ⚠️ Nur ~8192 MiB RAM — lahmer Build möglich

  ℹ  Betriebssystem: Windows (10.0.22631)

═══ Schritt 5/5: Smoke-Tests ═══

  ℹ  Python-Imports prüfen …
  ✅ Alle Python-Imports OK
  ℹ  Datenbank-Integrität prüfen …
  ✅ LIMEN: 7 Tabellen, integrity OK
  ...
```

Exit-Codes:

| Code | Bedeutung                                                  |
|------|------------------------------------------------------------|
| 0    | Alles OK                                                   |
| 1    | Pre-Flight fehlgeschlagen (z. B. Python < 3.11)            |
| 2    | Installationsfehler (z. B. pip scheiterte)                 |
| 3    | Smoke-Tests nach der Installation gescheitert              |

### 5.2 Vollständige Installation

```powershell
.\install.cmd
```

Das Skript führt nacheinander aus:

1.  Pre-Flight (8 Prüfungen)
2.  Rust-Installation (falls nötig via `winget`/`rustup-init.exe`)
3.  Python-Virtualenv anlegen in `.venv\`
4.  Pip-Upgrade + `pip install -r requirements.txt`
5.  **Editable** `pip install -e limen-main` und `-e karma-main`
6.  `npm ci` im Frontend (`ShinonLLM-main\frontend`)
7.  Datenbanken initialisieren (`.\data\{shinon,karma,limen}\`)
8.  Configs schreiben (`.\config\*.toml`, mode `0600`)
9.  Smoke-Tests ausführen

**Dauer:** 5–10 Minuten beim ersten Mal (je nach Internet-Geschwindigkeit).

### 5.3 Idempotenz

Der Installer kann ohne Bedenken mehrfach ausgeführt werden — er erkennt,
was schon vorhanden ist, und überspringt es. Praktisch z. B. nach `git pull`:

```powershell
git pull
.\install.cmd        # macht nur was nötig ist
```

### 5.4 Repair-Modus

Wenn du alle Daten löschen willst, aber installierte Pakete behalten:

```powershell
.\install.cmd --repair
# löscht: .\data\*\*.db, .\config\.install-done
# behält: .venv (Pakete), node_modules, installierte System-Tools
```

---

## 6. Firewall-Hinweise

> **Standardverhalten:** Shinon bindet **alle drei Services auf
> `127.0.0.1`** (Loopback-Adresse). Das heißt:
>
> - **Nur Programme auf DIESEM Rechner** können sie erreichen.
> - Andere Geräte im LAN / Internet können sie **nicht** sehen —
>   unabhängig davon, ob eine Firewall-Regel existiert oder nicht.
> - **Die Windows-Firewall braucht KEINE Ausnahmen**, damit Shinon
>   funktioniert. Sie funktioniert out-of-the-box.

Falls du Shinon **von einem anderen Gerät im LAN aus** ansprechen möchtest
(z. B. Tablet im Wohnzimmer ruft die Chat-UI auf dem Desktop auf), musst
du **zwei** Änderungen machen.

### 6.1 Service auf 0.0.0.0 binden (nicht 127.0.0.1)

Bearbeite `.\config\shinon.toml` und passe die `host`-Einträge an. Aktuell
ist die genaue Konfiguration hardcodiert auf `127.0.0.1`; ein Flag
`listen_external = true` ist geplant (TODO-3). Bis dahin bleibt der
LAN-Zugriff deaktiviert — **das ist gewollt** (Defense-in-Depth).

### 6.2 Firewall-Regeln hinzufügen

```powershell
# PowerShell ALS ADMINISTRATOR
# 3 neue eingehende Regeln für die 3 Standardports

New-NetFirewallRule -DisplayName "Shinon Dashboard 4200" `
    -Direction Inbound -Protocol TCP -LocalPort 4200 `
    -Action Allow -Profile Private

New-NetFirewallRule -DisplayName "Shinon UI 4300" `
    -Direction Inbound -Protocol TCP -LocalPort 4300 `
    -Action Allow -Profile Private

New-NetFirewallRule -DisplayName "LIMEN Backend 8000" `
    -Direction Inbound -Protocol TCP -LocalPort 8000 `
    -Action Allow -Profile Private
```

> **Profile `Private`** heißt: nur im Heimnetzwerk erlaubt, nicht in
> öffentlichen WLANs. Für öffentliches WLAN solltest du die Regeln
> entweder **nicht** hinzufügen, oder das Profil auf `Public` ändern.

Kontrolle:

```powershell
Get-NetFirewallRule -DisplayName "Shinon*" | Format-Table DisplayName, Enabled, Direction, LocalPort
```

Regeln wieder entfernen:

```powershell
Remove-NetFirewallRule -DisplayName "Shinon Dashboard 4200"
Remove-NetFirewallRule -DisplayName "Shinon UI 4300"
Remove-NetFirewallRule -DisplayName "LIMEN Backend 8000"
```

### 6.3 Antivirus-Ausnahmen

Windows Defender scannt ausführbare Dateien (`.exe`) während des
`pip install`-Vorgangs. Bei einigen Paketen (insbesondere
`tiktoken`-Build mit Rust) kann das 30–60 Sekunden pro Datei dauern.

**Falls die Installation ungewöhnlich lang hängt**, füge den
Projektordner zur Defender-Ausnahmeliste hinzu:

```powershell
# PowerShell ALS ADMINISTRATOR
Add-MpPreference -ExclusionPath "C:\Projects\shinon-control-plane"
Add-MpPreference -ExclusionPath "C:\Projects\shinon-control-plane\.venv"
Add-MpPreference -ExclusionPath "C:\Projects\shinon-control-plane\ShinonLLM-main\frontend\node_modules"
```

Wieder entfernen:

```powershell
Remove-MpPreference -ExclusionPath "C:\Projects\shinon-control-plane"
Remove-MpPreference -ExclusionPath "C:\Projects\shinon-control-plane\.venv"
Remove-MpPreference -ExclusionPath "C:\Projects\shinon-control-plane\ShinonLLM-main\frontend\node_modules"
```

---

## 7. Erste Schritte nach der Installation

Wenn `install.cmd` durchgelaufen ist, kannst du sofort:

```powershell
# Statusübersicht — zeigt was läuft, was nicht
.\shinon.cmd status

# Alle 3 Services starten (LIMEN, dashboard, shinon-ui)
.\shinon.cmd start

# Onboarding-Wizard (Doctor Mous) — führt dich durch 4 Schritte:
#   1. Provider-Keys (LLM-Provider API-Keys) eingeben
#   2. Persönlichkeits-Score justieren
#   3. Skills-Discovery testen
#   4. Test-Chat abschicken
.\shinon.cmd --setup

# Web-Chat manuell öffnen
.\shinon.cmd chat
# → startet Browser auf http://127.0.0.1:4300/

# Alle Services stoppen
.\shinon.cmd stop

# Doctor Mous: durchsucht das System nach typischen Problemen
.\shinon.cmd --doc
```

Auf einem Desktop-Browser erscheinen die Web-Oberflächen unter:

| Service    | URL                       | Was du dort siehst                  |
|------------|---------------------------|-------------------------------------|
| shinon-ui  | <http://127.0.0.1:4300/>  | Hauptchat + Stats + Settings        |
| dashboard  | <http://127.0.0.1:4200/>  | Komponenten-Übersicht, Logs         |
| LIMEN API  | <http://127.0.0.1:8000/>  | OpenAI-kompatibles `/v1/chat/...`   |

> **Tipp:** Falls dein Browser "Connection refused" zeigt — sind die
> Services gestartet? `.\shinon.cmd status` zeigt es dir. Manche Browser
> cachen das negativ (= "Site nicht erreichbar"); einmal F5 reicht meist.

---

## 8. Troubleshooting

### Problem: `python` öffnet den Microsoft Store

**Symptom:**

```powershell
PS C:\> python --version
# öffnet Store statt Versionsnummer zu zeigen
```

**Lösung:** Siehe Abschnitt [2.1 Python ohne Microsoft Store](#21-python-ohne-microsoft-store).
Der `python`-Befehl ist ein **Alias** auf den Store und nicht dein echtes
Python.

Verify der PATH-Korrektur:

```powershell
where.exe python
# soll:   C:\Users\<USER>\AppData\Local\Programs\Python\Python312\python.exe
# NICHT:  C:\Users\<USER>\AppData\Local\Microsoft\WindowsApps\python.exe
```

### Problem: `'python' is not recognized as a cmdlet`

**Ursache:** Python wurde ohne PATH-Eintrag installiert ODER PATH wurde
nicht neu geladen.

**Lösung:**

```powershell
# PowerShell-Fenster schließen und ein neues öffnen (PATH reload)
exit

# Wenn das nicht hilft — explizit prüfen
[System.Environment]::GetEnvironmentVariable('PATH', 'User') -split ';' |
    Where-Object { $_ -match 'Python' }
```

### Problem: `install.cmd` hängt bei `pip install`

**Mögliche Ursachen:**

1.  **Defender scannt gerade:** siehe [6.3 Antivirus-Ausnahmen](#63-antivirus-ausnahmen)
2.  **Proxy blockiert PyPI:** du bist hinter einer Firmen-Firewall

```powershell
# PIP mit explizitem Proxy
.\install.cmd --python-only --verbose
# Beobachte Output genau. Bei Proxy-Fehler steht dort:
#   "Could not fetch URL https://pypi.org/simple/..."
```

Workaround mit Proxy:

```powershell
$env:HTTPS_PROXY = "http://proxy.firma.de:8080"
.\install.cmd
```

3.  **Rust-Build dauert ewig:** `tiktoken` braucht 5–10 Min Rust-Compile
    beim ersten Mal. Einfach warten — oder Python 3.12 statt 3.14 nehmen.

### Problem: `Port 8000 already in use`

**Symptom:** LIMEN startet nicht, obwohl das die einzige Shinon-Installation ist.

**Diagnose:**

```powershell
# Wer belegt den Port?
Get-NetTCPConnection -LocalPort 8000 -State Listen |
    Select-Object LocalAddress, LocalPort, OwningProcess,
        @{n='Process';e={(Get-Process -Id $_.OwningProcess).ProcessName}}
```

Häufige Übeltäter: IIS (`w3wp.exe`), eine andere Webapp, ein Docker-Container.

**Lösung A — Shinon auf anderen Port umstellen:**

Bearbeite `.\config\limen.toml`:

```toml
[server]
port = 8001   # war 8000
```

Dann `.\shinon.cmd stop`, `.\shinon.cmd start`, fertig.

### Problem: Firewall fragt bei jedem ersten Start

**Symptom:** Windows fragt "Soll Python Netzwerkzugriff erhalten?"

**Antwort:** Ja (✔️ Private Netzwerke, ☐ Öffentliche Netzwerke).
Das ist normal — die Antwort wird gespeichert.

### Problem: Sonderzeichen im Benutzernamen

**Symptom:** Install hängt bei `pip install` mit kryptischen Fehlern, oder
`npm ci` meldet Pfad-Konflikt.

**Ursache:** Manche Python/npm-Pakete kommen nicht mit Profilen klar,
deren Name Umlaute (`Müller`), Leerzeichen (`Anna Schmidt`) oder
Sonderzeichen (`O'Brien`) enthält.

**Workaround:** einen neuen Windows-Benutzer **ohne Sonderzeichen**
anlegen, oder das Projekt nach `C:\dev\shinon\` verschieben
(kurzer Pfad, kein Leerzeichen im Username).

### Problem: `git submodule` fehlt

Falls deine Repo-Variante Submodule hat und `git clone` ohne
`--recurse-submodules` gemacht wurde:

```powershell
git submodule update --init --recursive
```

### Problem: PowerShell Execution-Policy blockt das Skript

**Symptom:**

```
File C:\Projects\shinon-control-plane\install.cmd cannot be loaded because
running scripts is disabled on this system.
```

**Lösung:**

```powershell
# Pro User (empfohlen) — nicht "RemoteSigned"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Problem: Terminal bleibt schwarz / Emojis zeigen als `?`

**Ursache:** Windows 10 mit altem Code-Page + Terminal-Schrift ohne
Unicode.

**Lösung:** wechsle auf **Windows Terminal** (kostenlos im Microsoft
Store) oder **PowerShell 7** — beide rendern UTF-8 standardmäßig.

```powershell
# PowerShell 7 installieren (empfohlen!)
winget install --id Microsoft.PowerShell --accept-package-agreements --accept-source-agreements
```

### Problem: Datenbank korrupt nach Stromausfall

**Symptom:** Beim Start `sqlite3.DatabaseError: database disk image is malformed`

**Lösung:**

```powershell
# 1) Alle Services stoppen
.\shinon.cmd stop

# 2) Backup der korrupten DB machen (für Forensik)
Copy-Item .\data\shinon\memory.db .\data\shinon\memory.db.crash.$(Get-Date -Format 'yyyyMMdd')

# 3) Neu initialisieren — Datenverlust, aber Service läuft wieder
.\install.cmd --repair

# 4) Zukünftig: USV bzw. sauberes Herunterfahren 😉
```

---

## 9. Komplett deinstallieren

```powershell
# 1) Repo-Ordner entfernen — alles ist drin, kein $HOME-State
Remove-Item -Recurse -Force C:\Projects\shinon-control-plane

# 2) (Optional) Global installierte Tools bleiben — die werden separat entfernt:
#    winget uninstall Python.Python.3.12
#    winget uninstall OpenJS.NodeJS.LTS
#    winget uninstall Git.Git
#    winget uninstall Rustlang.Rustup
#    winget uninstall Microsoft.PowerShell

# 3) (Optional) Firewall-Regeln entfernen — siehe Abschnitt 6.2
Remove-NetFirewallRule -DisplayName "Shinon*"
```

Es gibt **keine versteckten State-Verzeichnisse** in `%APPDATA%`,
`%LOCALAPPDATA%` oder `%USERPROFILE%` — Shinon ist **wirklich portabel**:

```powershell
# Verifizieren — sollte KEINE shinon-Treffer geben
Get-ChildItem $env:APPDATA, $env:LOCALAPPDATA, $env:USERPROFILE -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^shinon|^karma|^limen|^ctl' } 2>$null
```

Wenn die Suche leer zurückkommt, ist alles sauber.

---

## Anhang A — Cheat-Sheet (eine Din-A4-Seite)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SHINON · WINDOWS CHEAT SHEET                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  Install:                                                               │
│    git clone https://github.com/vannon0911/shinon-control-plane.git     │
│    cd shinon-control-plane                                              │
│    .\install.cmd                                                        │
│                                                                         │
│  Täglich:                                                               │
│    .\shinon.cmd start        # Services starten                          │
│    .\shinon.cmd status       # Status prüfen                            │
│    .\shinon.cmd stop         # Services stoppen                          │
│    .\shinon.cmd chat         # Browser zum Chat öffnen                  │
│                                                                         │
│  Troubleshooting:                                                       │
│    .\shinon.cmd --doc        # Doctor Mous                               │
│    .\shinon.cmd --setup      # Onboarding-Wizard                        │
│    .\install.cmd --check     # Pre-Flight + Smoke-Tests                  │
│    Get-NetTCPConnection -LocalPort 8000 -State Listen   # wer belegt 8000│
│                                                                         │
│  Pfade (im Projekt, NICHT in $HOME):                                    │
│    .\data\                  # Datenbanken (shinon/, karma/, limen/)     │
│    .\config\                # *.toml-Konfigs (mode 0600)                │
│    .\data\logs\             # Log-Dateien                               │
│    .\data\pids\             # PID-Dateien für Lifecycle                  │
│    .\.venv\                 # Python-Virtualenv                         │
│                                                                         │
│  URLs (loopback only):                                                  │
│    http://127.0.0.1:4300/   # Shinon UI (Hauptchat)                     │
│    http://127.0.0.1:4200/   # Dashboard                                 │
│    http://127.0.0.1:8000/   # LIMEN API (OpenAI-kompatibel)             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

**Fragen oder Bugs?** Bitte ein Issue auf
<https://github.com/vannon0911/shinon-control-plane/issues>
öffnen — das README im Repo-Stamm hat die aktuellen Maintainer-Kontakte.

*Dieses Dokument ist Teil des Shinon Control Plane v1.1.0 Release. Es
spiegelt genau das Verhalten von `install.py` Stand 2026-08-12. Wenn
deine Installation anders aussieht, ist wahrscheinlich ein neuerer Patch
im Spiel — prüfe `git log`.*
