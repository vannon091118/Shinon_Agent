#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# dashboard.sh — LIVE TUI für goal-chain
# Pollt DB, rendert ASCII-Dashboard mit Progress, Stats, FOLLOW/PRE_TASKS
#
# Usage:
#   bash dashboard.sh RUN_ID [--refresh=1.0] [--once]
#
# Features:
#   - ANSI Cursor-Reposition für flicker-free Updates
#   - Progress bar (% Done)
#   - Current-TID-Highlight
#   - FOLLOW/PRE_TASK-Counts pro TID
#   - User-Checkpoint-Warning wenn bevorstehend
#   - Falls nicht-TTY: static snapshot ausgeben
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"

RUN_ID="${1:?Usage: bash dashboard.sh RUN_ID [--refresh=1.0] [--once]}"
REFRESH=1.0
ONCE=false
for arg in "${@:2}"; do
    case "$arg" in
        --refresh=*) REFRESH="${arg#--refresh=}" ;;
        --once) ONCE=true ;;
    esac
done

ensure_db

# ANSI codes
CLEAR_SCREEN=$'\033[2J'
CURSOR_HOME=$'\033[H'
CLEAR_LINE=$'\033[K'
SAVE_CURSOR=$'\033[s'
RESTORE_CURSOR=$'\033[u'
HIDE_CURSOR=$'\033[?25l'
SHOW_CURSOR=$'\033[?25h'
BOLD=$'\033[1m'
DIM=$'\033[2m'
RESET=$'\033[0m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
RED=$'\033[31m'
CYAN=$'\033[36m'
MAGENTA=$'\033[35m'
BLUE=$'\033[34m'

# Non-TTY fallback
IS_TTY=false
[[ -t 1 ]] && IS_TTY=true

render_static() {
    python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()

# Overall stats
total = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=?', ('$RUN_ID',)).fetchone()[0]
done = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=? AND status=\"DONE\"', ('$RUN_ID',)).fetchone()[0]
inprog = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=? AND status=\"IN_PROGRESS\"', ('$RUN_ID',)).fetchone()[0]
pending = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=? AND status=\"PENDING\"', ('$RUN_ID',)).fetchone()[0]
failed = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=? AND status=\"FAILED\"', ('$RUN_ID',)).fetchone()[0]
skipped = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=? AND status=\"SKIPPED\"', ('$RUN_ID',)).fetchone()[0]
root_cause = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=? AND status=\"ROOT_CAUSE_DONE\"', ('$RUN_ID',)).fetchone()[0]
goal = cur.execute('SELECT goal FROM tasks WHERE run_id=? LIMIT 1', ('$RUN_ID',)).fetchone()[0]
projekt = cur.execute('SELECT projekt FROM tasks WHERE run_id=? LIMIT 1', ('$RUN_ID',)).fetchone()[0]

# Recent activity
recent = cur.execute('''
    SELECT tid, phase_section, status, completed_at
    FROM tasks WHERE run_id=? AND status IN ('DONE','IN_PROGRESS','FAILED')
    ORDER BY COALESCE(completed_at, updated_at) DESC LIMIT 6
''', ('$RUN_ID',)).fetchall()

# Next pending
next_tid = cur.execute('''
    SELECT t.tid FROM tasks t WHERE t.run_id=? AND t.status='PENDING'
    AND NOT EXISTS (SELECT 1 FROM pre_tasks pt JOIN tasks pt2 ON pt.pre_tid=pt2.tid WHERE pt.tid=t.tid AND pt2.status NOT IN ('DONE','SKIPPED','ROOT_CAUSE_DONE'))
    ORDER BY t.phase_seq LIMIT 1
''', ('$RUN_ID',)).fetchone()

# Per-phase breakdown
phases = cur.execute('''
    SELECT phase, status, COUNT(*) FROM tasks WHERE run_id=?
    GROUP BY phase, status ORDER BY phase
''', ('$RUN_ID',)).fetchall()

# Next user checkpoint
next_checkpoint = cur.execute('''
    SELECT t.tid, t.phase_section FROM tasks t
    WHERE t.run_id=? AND t.requires_approval=1 AND t.status IN ('PENDING')
    AND NOT EXISTS (SELECT 1 FROM pre_tasks pt JOIN tasks pt2 ON pt.pre_tid=pt2.tid WHERE pt.tid=t.tid AND pt2.status NOT IN ('DONE','SKIPPED','ROOT_CAUSE_DONE'))
    ORDER BY t.phase_seq LIMIT 1
''', ('$RUN_ID',)).fetchone()

percent = (done * 100 // total) if total > 0 else 0
bar_width = 50
filled = bar_width * done // total if total > 0 else 0
bar = '█' * filled + '░' * (bar_width - filled)

print('╔══════════════════════════════════════════════════════════════╗')
print('║  🔗 GOAL-CHAIN LIVE DASHBOARD                              ║')
print('╠══════════════════════════════════════════════════════════════╣')
print(f'║  Goal:    {goal[:50]:<50}  ║')
print(f'║  Run:     {(\"$RUN_ID\"):<50}  ║')
print(f'║  Project: {projekt:<50}  ║')
print('╠══════════════════════════════════════════════════════════════╣')
print(f'║  PROGRESS: {done}/{total} TIDs ({percent}%)'.ljust(58) + '║')
print(f'║  {bar}  ║')
print('╠══════════════════════════════════════════════════════════════╣')
icon = {'DONE':'✅', 'IN_PROGRESS':'🔄', 'FAILED':'❌', 'SKIPPED':'⏭ ', 'ROOT_CAUSE_DONE':'🎯', 'PENDING':'⏳'}
status_line = f\"  ✅ {done} done  🔄 {inprog} active  ⏳ {pending} pending  ❌ {failed} failed  ⏭  {skipped} skipped  🎯 {root_cause} root-cause\"
print(f'║{status_line:<58}║')

# Current TID
if next_tid:
    tid_info = cur.execute('SELECT phase, phase_section, skill_name FROM tasks WHERE tid=?', (next_tid[0],)).fetchone()
    print('╠══════════════════════════════════════════════════════════════╣')
    print(f'║  ▶ NÄCHSTER TID: {next_tid[0]:<41} ║')
    print(f'║     Phase:  {tid_info[0]:<8} | Section: {tid_info[1]:<21} ║')
    print(f'║     Skill:  {tid_info[2]:<43} ║')

print('╠══════════════════════════════════════════════════════════════╣')
print('║  RECENT ACTIVITY                                           ║')
if recent:
    for r in recent:
        icon_x = {'DONE':'✅', 'IN_PROGRESS':'🔄', 'FAILED':'❌'}.get(r[2], '⏳')
        ts = r[3] if r[3] else 'pending'
        print(f'║   {icon_x} {r[1]:<25} → {r[2]:<13} ({ts:<10})    ║')
else:
    print('║   (keine Aktivität)                                       ║')

print('╠══════════════════════════════════════════════════════════════╣')
if next_checkpoint:
    print(f'║  🛑 USER CHECKPOINT in: {next_checkpoint[1]:<15}              ║')
    print(f'║     TID: {next_checkpoint[0]:<47} ║')
else:
    print('║  ✅ Keine User-Checkpoints ausstehend                      ║')

print('╠══════════════════════════════════════════════════════════════╣')
print('║  PER-PHASE BREAKDOWN                                       ║')
agg = {}
for phase, status, cnt in phases:
    agg.setdefault(phase, {})[status] = cnt
for phase in ['P1','P2','P3','P4','G1-2','G2-3','STACK']:
    if phase in agg:
        a = agg[phase]
        d = a.get('DONE', 0)
        i = a.get('IN_PROGRESS', 0)
        p = a.get('PENDING', 0)
        x = a.get('FAILED', 0)
        print(f'║   {phase:<6}  ✅{d}  🔄{i}  ⏳{p}  ❌{x}                                  ║')

print('╚══════════════════════════════════════════════════════════════╝')
print(f'  Refresh: $REFRESH s · Press q to quit · Run: $RUN_ID')
conn.close()
"
}

# Static mode
if ! $IS_TTY || $ONCE; then
    render_static
    exit 0
fi

# Live TTY mode
cleanup() {
    echo "$SHOW_CURSOR"
    echo "$CURSOR_HOME"
    echo ""
}
trap cleanup EXIT

echo "$HIDE_CURSOR"
echo "$CLEAR_SCREEN"

while true; do
    echo "$CURSOR_HOME"
    render_static
    sleep "$REFRESH"
done
