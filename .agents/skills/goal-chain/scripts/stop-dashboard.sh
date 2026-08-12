#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# stop-dashboard.sh — Stoppt den Live-Dashboard Hintergrund-Prozess
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

RUN_ID="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "$RUN_ID" ]]; then
    # Kill all dashboards
    echo "Stopping all goal-chain dashboards..."
    pkill -f "bash $SCRIPT_DIR/dashboard.sh" 2>/dev/null && echo "Killed." || echo "Keine aktiven Dashboards."
    exit 0
fi

PID_FILE=".goal/${RUN_ID}/.dashboard.pid"
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if kill "$PID" 2>/dev/null; then
        echo "✅ Dashboard gestoppt (PID $PID, Run $RUN_ID)"
        rm -f "$PID_FILE"
    else
        echo "⚠️  PID $PID nicht aktiv — räume PID-File auf"
        rm -f "$PID_FILE"
    fi
else
    echo "Kein PID-File für Run $RUN_ID gefunden"
    echo "Versuche allgemeine Suche..."
    pkill -f "dashboard.sh $RUN_ID" 2>/dev/null && echo "Gefunden und gestoppt."
fi
