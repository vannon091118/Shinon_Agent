#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# dispatch.sh — Entry point for /goal runs
# Seeds TIDs, generates HTML snapshot, launches dashboard.
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"

MODE="${1:-}"

# ─── Status Mode ───────────────────────────────────────────────────
if [[ "$MODE" == "--status" ]]; then
    ensure_db
    RUN_ID="$2"
    if [[ -z "$RUN_ID" ]]; then
        echo "══════════════════════════════════════════════════════════"
        echo "  AKTIVE RUNS"
        echo "══════════════════════════════════════════════════════════"
        db_query "SELECT DISTINCT run_id, projekt, substr(goal,1,60) FROM tasks ORDER BY run_id DESC LIMIT 10;" | while IFS='|' read -r rid proj goal_short; do
            done_count=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$rid' AND status='DONE';")
            pending_count=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$rid' AND status IN ('PENDING','IN_PROGRESS');")
            echo "  $rid | $proj | $done_count done, $pending_count pending | $goal_short"
        done
        exit 0
    fi
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  RUN STATUS: $RUN_ID"
    echo "╠══════════════════════════════════════════════════════════╣"
    tids_for_run "$RUN_ID" | while IFS='|' read -r tid phase section status; do
        icon=" "
        case "$status" in DONE) icon="✅" ;; IN_PROGRESS) icon="🔄" ;; FAILED) icon="❌" ;; SKIPPED) icon="⏭️ " ;; ROOT_CAUSE_DONE) icon="🎯" ;; *) icon="⏳" ;; esac
        printf "║  %s  %-55s %s\n" "$icon" "$tid" "$status"
    done
    echo "╚══════════════════════════════════════════════════════════╝"
    NEXT_PENDING=$(next_pending_tid "$RUN_ID")
    if [[ -n "$NEXT_PENDING" ]]; then
        echo ""; echo "▶ NÄCHSTER TID: $NEXT_PENDING"
        echo "  Script: bash $(script_for_tid "$NEXT_PENDING") $RUN_ID $NEXT_PENDING"
        echo "  Snapshot: $(find .goal/${RUN_ID}* -name 'snapshot.html' 2>/dev/null | head -1)"
    fi
    exit 0
fi

# ─── List Mode ─────────────────────────────────────────────────────
if [[ "$MODE" == "--list" ]]; then
    ensure_db
    echo "══════════════════════════════════════════════════════════"
    echo "  ALLE RUNS"
    echo "══════════════════════════════════════════════════════════"
    db_query "SELECT DISTINCT run_id, projekt, goal FROM tasks ORDER BY run_id DESC;" | while IFS='|' read -r rid proj goal; do
        snapshot=$(find .goal/${rid}* -name 'snapshot.html' 2>/dev/null | head -1)
        echo "  $rid | $proj | $goal ${snapshot:+📸 $snapshot}"
    done
    exit 0
fi

# ─── Snapshot Mode (from existing run) ─────────────────────────
if [[ "$MODE" == "--snapshot" ]]; then
    RUN_ID="$2"
    [[ -z "$RUN_ID" ]] && { echo "Usage: dispatch.sh --snapshot RUN_ID"; exit 1; }
    SNAPSHOT=$(find .goal/${RUN_ID}* -name 'snapshot.html' 2>/dev/null | head -1)
    if [[ -n "$SNAPSHOT" ]]; then
        echo "  📸 $SNAPSHOT"
        bash "$SCRIPT_DIR/update-snapshot.sh" "$RUN_ID" "Manual refresh" > "$SNAPSHOT"
        echo "  ✅ regenerated"
    else
        echo "  ❌ No snapshot found for $RUN_ID"
    fi
    exit 0
fi

# ─── Run Mode ──────────────────────────────────────────────────────
GOAL="$MODE"
PROJEKT="${2:-PZ}"

if [[ -z "${GOAL// }" ]]; then
    # No goal: list runs with snapshots
    ensure_db
    echo "══════════════════════════════════════════════════════════"
    echo "  /goal — Usage"
    echo "══════════════════════════════════════════════════════════"
    echo "  ./run_goal.sh 'ZIEL'           # Start a new run"
    echo "  ./run_goal.sh --status [RUN]  # Show TIDs"
    echo "  ./run_goal.sh --snapshot RUN  # Refresh HTML snapshot"
    echo "  ./run_goal.sh --list          # All runs+their snapshots"
    echo "  ./run_goal.sh --verify RUN   # Recovery info"
    echo ""
    echo "  Verfügbare Runs mit Snapshots:"
    for d in $(ls -d .goal/R* 2>/dev/null | tail -5); do
        rid=$(basename "$d" | cut -d- -f1-2)
        rid="${rid%%-*}"
        # extract just R<digits>
        rid=$(echo "$(basename "$d")" | grep -oP '^R\d+')
        proj=$(db_query "SELECT DISTINCT projekt FROM tasks WHERE run_id='$rid' LIMIT 1;" | head -1)
        goal=$(db_query "SELECT DISTINCT goal FROM tasks WHERE run_id='$rid' LIMIT 1;" | head -1)
        done_n=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$rid' AND status='DONE';")
        total_n=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$rid';")
        echo "  📸 $d/snapshot.html · $rid | $proj | $done_n/$total_n done | $goal"
    done
    exit 0
fi

ensure_db

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  /goal DISPATCH                                        ║"
echo "║  PROJEKT: $PROJEKT"
echo "║  GOAL:    $GOAL"
echo "╚══════════════════════════════════════════════════════════╝"

# ─── 🔴 DASHBOARD-START (ERSTES, vor allem anderen) ───────────
# Server MUSS als ERSTES laufen. user will Daten sehen während chain arbeitet.
SERVER_PORT=4200
SERVER_SCRIPT="$SCRIPT_DIR/live-dashboard-server.py"

# Kill any previous dashboard (port reuse)
pkill -9 -f "live-dashboard-server.py" 2>/dev/null || true
sleep 0.5

# PID file in a shared location (not per-run, so it survives multiple chains)
PID_FILE=/tmp/live-dashboard-server.pid
rm -f "$PID_FILE"

DASHBOARD_OK=false
if [[ -x "$SERVER_SCRIPT" || -f "$SERVER_SCRIPT" ]]; then
    timeout 10 python3 -c "
import subprocess, sys, os, time
os.chdir('$(pwd)')
p = subprocess.Popen(
    [sys.executable, '$SERVER_SCRIPT', str($SERVER_PORT), 'UNSEEDED'],
    stdout=open('/tmp/dash.log','a'), stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL, start_new_session=True
)
with open('$PID_FILE','w') as f: f.write(str(p.pid))
time.sleep(3)
import socket
s=socket.socket(); s.settimeout(1)
if s.connect_ex(('127.0.0.1',$SERVER_PORT)) == 0:
    print(f'PID={p.pid}')
    sys.exit(0)
else:
    print('TIMEOUT')
    sys.exit(1)
" 2>/dev/null && DASHBOARD_OK=true || DASHBOARD_OK=false
fi

if $DASHBOARD_OK; then
    echo "  🔗 LIVE-DASHBOARD gestartet: http://127.0.0.1:$SERVER_PORT"
    echo "     (läuft ALS ERSTES — zeigt Status während gesamter Chain)"
    echo "     PID: $(cat $PID_FILE 2>/dev/null)"
    echo ""
else
    echo "  ⚠️  LIVE-DASHBOARD konnte nicht gestartet werden"
    echo "     (SANDSTORM/keine Hintergrundprozesse — Server läuft nur"
    echo "      innerhalb dieser Session. Starte manuell falls nötig."
    echo "      Befehl: python3 $SERVER_SCRIPT 4200 &)"
    echo ""
fi

notify_dashboard "RUN_STARTED" "---" "Run=SEEDING Project=$PROJEKT Goal='$GOAL'"

# Run Python seeder (sets RUN_ID, TID_COUNT, RUN_DIR)
SEED_OUTPUT=$(python3 "$SCRIPT_DIR/seed_tids.py" "$PROJEKT" "$GOAL")
eval "$SEED_OUTPUT"

echo "  ✅ $TID_COUNT TIDs seeded for $RUN_ID (20 Phase + 43 Stack-Tools · alle 27 raw skills jetzt chain-integriert)"
echo "  📁 $RUN_DIR"
echo ""

# Trigger dashboard refresh now that TIDs exist
if [[ -f "$PID_FILE" ]]; then
    touch .agents/skills/live/.needs_refresh 2>/dev/null || true
fi

# Generate initial HTML snapshot (legacy, meta-refresh)
SNAPSHOT="$RUN_DIR/snapshot.html"
if bash "$SCRIPT_DIR/update-snapshot.sh" "$RUN_ID" "RUN_STARTED · seeding complete" > "$SNAPSHOT" 2>/dev/null && [[ -s "$SNAPSHOT" ]]; then
    echo "  📸 Meta-Snapshot: $SNAPSHOT"
else
    echo "  ⚠️  Meta-Snapshot fehlgeschlagen"
fi
echo ""

# ─── Show user live-skill registry stats ──────────────────────
LIVE_COUNT=0
if [[ -d ".agents/skills/live" ]]; then
    LIVE_COUNT=$(find ".agents/skills/live" -maxdepth 1 -name "*.md" 2>/dev/null | wc -l)
fi
echo "  🧩 Live-Skill-Registry: $LIVE_COUNT snapshots"
echo "     Dashboard (SSE): http://127.0.0.1:$SERVER_PORT/"
echo "     Skills JSON:     http://127.0.0.1:$SERVER_PORT/api/skills"
echo "     Skills Liste:    bash .agents/skills/live-context.sh --list"
echo "     Re-Discover:     bash $SCRIPT_DIR/migrate-all-skills.sh --force"
echo ""

S=".agents/skills/goal-chain/scripts"
FIRST_TID="${PROJEKT}-${RUN_ID}-P1-brainstorming"
FIRST_SCRIPT="$S/phase-1-brainstorming.sh"

cat <<AGENTEOF

╔══════════════════════════════════════════════════════════════╗
║  🚀 AGENT: STARTE HIER                                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                            ║
║  ▶ Befehl:                                                 ║
║    bash $FIRST_SCRIPT $RUN_ID $FIRST_TID                   ║
║                                                            ║
║  Das Script gibt dir ALLE benötigten Instruktionen.        ║
║  JEDES Script emuliert eine USER INPUT-Nachricht.          ║
║  Du MUSST dem Script folgen — NICHT das Script verändern. ║
║                                                            ║
║  📺 DASHBOARD live: http://127.0.0.1:$SERVER_PORT           ║
║     (in deinem Browser öffnen — zeigt Live-Progress)      ║
║     PID: $(cat $PID_FILE 2>/dev/null || echo 'N/A')        ║
║     Endpoints: /api/skills · /api/state · /event · /       ║
║                                                            ║
║  📸 Meta-Snapshot (statisch): $SNAPSHOT                    ║
║                                                            ║
║  ❓ Status verloren?    bash $0 --status $RUN_ID          ║
║  🔄 Snapshot neu:       bash $0 --snapshot $RUN_ID        ║
║  🩹 Recovery:           bash $SCRIPT_DIR/verify-state.sh $RUN_ID
║  🛑 Dashboard-Stop:     bash $SCRIPT_DIR/stop-dashboard.sh ║
║                                                            ║
╚══════════════════════════════════════════════════════════════╝

AGENTEOF
