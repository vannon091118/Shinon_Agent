@echo off
REM ════════════════════════════════════════════════════════════════════════
REM install.cmd — Windows-Wrapper für install.py
REM
REM DIESER WRAPPER MACHT NICHTS ANDERES ALS:
REM   1. Codepage auf UTF-8 umschalten
REM   2. PYTHONIOENCODING=utf-8 festnageln (damit Python-Emojis sauber rausgehen)
REM   3. Projekt-Verzeichnis finden
REM   4. Python (≥3.11) im PATH suchen
REM   5. python install.py %* aufrufen
REM
REM Die eigentliche Installer-Logik lebt in install.py (cross-platform).
REM
REM TROUBLESHOOTING-TRIPTYCHON (für Diagnose):
REM   • Python-Aliase:   https://docs.python.org/3/using/windows.html#sudo
REM                       Microsoft Store leitet `python` um — Einstellungen →
REM                       Apps → Erweiterte App-Einstellungen → python.exe AUS.
REM   • ExecutionPolicy: Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Bypass
REM                       (betrifft nur .ps1-Skripte; wir nutzen .cmd, also
REM                       i.d.R. kein Problem — diese Zeile nur falls du später
REM                       mal auf shinon.ps1 o.ä. wechselst.)
REM   • Codepage:        `chcp` zeigt aktuelle Codepage. Falls Emojis als ?
REM                       erscheinen, vor `install.cmd` einmal `chcp 65001`.
REM ════════════════════════════════════════════════════════════════════════

REM UTF-8-Codepage setzen (sonst rendert Windows-CMD Unicode-Emojis als ?)
chcp 65001 >nul 2>&1

REM Python-Output zwingend UTF-8 (Workaround fuer cp1252 default).
set PYTHONIOENCODING=utf-8

setlocal
cd /d "%~dp0"

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python "%~dp0install.py" %*
    goto :end
)

where python3 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python3 "%~dp0install.py" %*
    goto :end
)

echo [FAIL] Python 3.11+ nicht gefunden.
echo        Download: https://www.python.org/downloads/
echo        Windows-11-Falle: Microsoft Store leitet 'python' um.
echo        Loesung: docs/INSTALL-WINDOWS.md Abschnitt 2.1 lesen.
exit /b 1

:end
endlocal
