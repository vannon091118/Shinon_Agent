@echo off
REM ════════════════════════════════════════════════════════════════════════
REM ctl.cmd — Windows Lifecycle-Wrapper (thin shim)
REM
REM Leitet ALLES an ctl.py weiter (start/stop/status/restart).
REM UTF-8 für saubere Emoji-Ausgabe.
REM ════════════════════════════════════════════════════════════════════════

chcp 65001 >nul 2>&1

REM Python-IO auf UTF-8 festnageln
set PYTHONIOENCODING=utf-8

setlocal
cd /d "%~dp0"

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python "%~dp0ctl.py" %*
    goto :end
)

where python3 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python3 "%~dp0ctl.py" %*
    goto :end
)

echo [FAIL] Python 3.11+ nicht gefunden.
exit /b 1

:end
endlocal
