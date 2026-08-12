@echo off
REM ════════════════════════════════════════════════════════════════════════
REM shinon.cmd — Windows CLI-Wrapper (thin shim)
REM
REM Leitet ALLES an shinon.py weiter. Die eigentliche Logik lebt in Python.
REM Forward-kompatibel: jedes neue Subcommand in shinon.py funktioniert
REM automatisch über diesen Wrapper.
REM ════════════════════════════════════════════════════════════════════════

setlocal
cd /d "%~dp0"

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python "%~dp0shinon.py" %*
    goto :end
)

where python3 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python3 "%~dp0shinon.py" %*
    goto :end
)

echo [FAIL] Python 3.11+ nicht gefunden. Bitte installieren:
echo        https://www.python.org/downloads/
exit /b 1

:end
endlocal
