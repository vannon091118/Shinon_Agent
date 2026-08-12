@echo off
REM ════════════════════════════════════════════════════════════════════════
REM install.cmd — Windows-Wrapper für install.py
REM
REM DIESER WRAPPER MACHT NICHTS ANDERES ALS:
REM   1. Projekt-Verzeichnis finden
REM   2. Python (≥3.11) im PATH suchen
REM   3. python install.py %* aufrufen
REM
REM Die eigentliche Installer-Logik lebt in install.py (cross-platform).
REM ════════════════════════════════════════════════════════════════════════

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

echo [FAIL] Python 3.11+ nicht gefunden. Bitte installieren:
echo        https://www.python.org/downloads/
exit /b 1

:end
endlocal
