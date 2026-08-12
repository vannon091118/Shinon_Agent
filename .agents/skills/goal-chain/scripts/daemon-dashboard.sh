#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# daemon-dashboard.sh — Launch live-dashboard-server as real daemon
#
# Uses Python double-fork to detach from any controlling terminal.
# The server survives the shell that launched it.  Writes PID file.
#
# Usage:
#   bash daemon-dashboard.sh              # start on default port 4200
#   bash daemon-dashboard.sh 8080         # custom port
#   bash daemon-dashboard.sh status       # is it running?
#   bash daemon-dashboard.sh stop         # kill it
#   bash daemon-dashboard.sh restart      # stop + start
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
cd "$ROOT"

PID_FILE="/tmp/live-dashboard-server.pid"
LOG_FILE="/tmp/live-dashboard-server.log"

MODE="${1:-}"
PORT="${2:-4200}"

# ─── Status check ──────────────────────────────────────────────────
if [[ "$MODE" == "status" ]]; then
    if [[ -f "$PID_FILE" ]]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "✅ Dashboard läuft (PID $PID)"
            echo "   Endpoints:"
            echo "     http://127.0.0.1:$PORT/"
            echo "     http://127.0.0.1:$PORT/events"
            echo "     http://127.0.0.1:$PORT/api/skills"
            echo "     http://127.0.0.1:$PORT/api/state"
            echo "   Log: $LOG_FILE"
            exit 0
        else
            echo "⚠️  PID-File vorhanden ($PID) aber Prozess tot — räume auf"
            rm -f "$PID_FILE"
        fi
    fi
    echo "❌ Kein Dashboard-Server aktiv"
    echo "   Start: bash $0 start"
    exit 1
fi

# ─── Stop ──────────────────────────────────────────────────────────
if [[ "$MODE" == "stop" ]]; then
    if [[ -f "$PID_FILE" ]]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null || true
            sleep 1
            kill -9 "$PID" 2>/dev/null || true
            echo "✅ Dashboard gestoppt (PID $PID)"
        fi
        rm -f "$PID_FILE"
    fi
    pkill -9 -f "live-dashboard-server.py" 2>/dev/null || true
    exit 0
fi

# ─── Restart ───────────────────────────────────────────────────────
if [[ "$MODE" == "restart" ]]; then
    bash "$0" stop
    sleep 1
    bash "$0" start "$PORT"
    exit 0
fi

# ─── Start (default mode) ──────────────────────────────────────────
# Clean up dead PID files
if [[ -f "$PID_FILE" ]]; then
    OLD=$(cat "$PID_FILE")
    if ! kill -0 "$OLD" 2>/dev/null; then
        rm -f "$PID_FILE"
    fi
fi

# Already running?
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "⚠️  Dashboard läuft bereits (PID $PID)"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

# Start via Python daemonizer (double-fork, survives all shell exits)
export PZ_ROOT="$ROOT"
export PZ_PORT="$PORT"
python3 << 'PYEOF' &
import os, sys, time

def daemonize():
    # First fork
    pid = os.fork()
    if pid > 0:
        sys.exit(0)          # Parent exits

    # Child: detach from session
    os.setsid()
    os.umask(0o022)

    # Second fork
    pid = os.fork()
    if pid > 0:
        sys.exit(0)          # First child exits

    # Grandchild: now a real daemon with no controlling terminal
    os.chdir("/tmp")
    sys.stdin = open("/dev/null", "r")
    sys.stdout = open("/tmp/live-dashboard-daemon.log", "a")
    sys.stderr = sys.stdout

daemonize()

# Now launch the real server
import subprocess
log = open("/tmp/live-dashboard-daemon.log", "a")
proc = subprocess.Popen(
    [sys.executable, ".agents/skills/goal-chain/scripts/live-dashboard-server.py", os.environ.get("PZ_PORT", "4200")],
    stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
    cwd=os.environ["PZ_ROOT"],
    start_new_session=True,
)
pid = proc.pid
# Write PID file for status/stop
with open("/tmp/live-dashboard-server.pid", "w") as f:
    f.write(str(pid))
print(f"DAEMON: server PID {pid} started", flush=True)

# Wait for server to start
time.sleep(2)
sys.exit(0)
PYEOF

sleep 3

# Verify
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "✅ LIVE-DASHBOARD läuft als Daemon!"
        echo "   PID:      $PID"
        echo "   Status:  http://127.0.0.1:4200/"
        echo "   Skills:  http://127.0.0.1:4200/api/skills"
        echo "   Events:  http://127.0.0.1:4200/events"
        echo "   Stop:    bash $0 stop"
        echo "   Log:     /tmp/live-dashboard-daemon.log"
        exit 0
    fi
fi

echo "❌ Daemon-Start fehlgeschlagen — prüfe /tmp/live-dashboard-daemon.log"
exit 1
