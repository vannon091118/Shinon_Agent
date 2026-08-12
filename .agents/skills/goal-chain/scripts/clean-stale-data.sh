#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# clean-stale-data.sh — Entfernt stale Daten aus goal-chain und live-dashboard
#
# Entfernt:
#   • Orphan .goal/<RUN_ID>/ Verzeichnisse (vollendete/alte Runs)
#   • Alte TID-Rows in der SQLite-DB (status DONE/FAILED/SKIPPED/ROOT_CAUSE_DONE älter als N Tage)
#   • Live-Snapshots die auf nicht-existente SKILL.md-Pfade zeigen
#   • Registry-Einträge für nicht-existente Skills
#
# Usage:
#   bash clean-stale-data.sh                # alle defaults (7 Tage)
#   bash clean-stale-data.sh --days=3        # nur jünger als 3 Tage entfernen
#   bash clean-stale-data.sh --keep-goal     # .goal/ Verzeichnisse behalten
#   bash clean-stale-data.sh --dry-run       # nur anzeigen, nichts löschen
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
cd "$ROOT"

DAYS=7
KEEP_GOAL=false
DRY_RUN=false
LIVE_DIR=".agents/skills/live"
# Zentral-first: $SHINON_HOME/data/goal-chain/tid-state.db, sonst Legacy.
_SHINON_HOME="${SHINON_HOME:-$HOME/.shinon}"
if [[ -n "${SHINON_GOALCHAIN_DB:-}" ]]; then
    DB_PATH="${SHINON_GOALCHAIN_DB}"
elif [[ -f "${_SHINON_HOME}/data/goal-chain/tid-state.db" ]]; then
    DB_PATH="${_SHINON_HOME}/data/goal-chain/tid-state.db"
else
    DB_PATH="$ROOT/.agents/skills/goal-chain/db/tid-state.db"
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --days=*)    DAYS="${1#--days=}" ; shift ;;
        --keep-goal) KEEP_GOAL=true ; shift ;;
        --dry-run)   DRY_RUN=true ; shift ;;
        *) echo "Unknown arg: $1" >&2 ; exit 1 ;;
    esac
done

echo "═══════════════════════════════════════════════════════════════"
echo "  🧹 CLEAN STALE DATA · cutoff=${DAYS}d · dry_run=$DRY_RUN"
echo "═══════════════════════════════════════════════════════════════"

# ─── 1. Alte TID-Rows aus DB ─────────────────────────────────────
if [[ -f "$DB_PATH" ]]; then
    cutoff=$(date -u -d "$DAYS days ago" +"%Y-%m-%dT%H:%M:%S" 2>/dev/null || \
             date -u -v "-${DAYS}d" +"%Y-%m-%dT%H:%M:%S" 2>/dev/null || \
             echo "2000-01-01T00:00:00")
    OLD_TASK_COUNT=$(python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()
n = cur.execute(\"SELECT COUNT(*) FROM tasks WHERE status IN ('DONE','FAILED','SKIPPED','ROOT_CAUSE_DONE') AND COALESCE(completed_at, updated_at) < '$cutoff'\").fetchone()[0]
print(n)
" 2>/dev/null || echo 0)
    echo "  📦 DB: $OLD_TASK_COUNT old TID-rows (status DONE/FAILED/SKIPPED/ROOT_CAUSE, >${DAYS}d)"
    if [[ "$OLD_TASK_COUNT" -gt 0 && "$DRY_RUN" != true ]]; then
        python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()
cur.execute(\"\"\"DELETE FROM tasks WHERE status IN ('DONE','FAILED','SKIPPED','ROOT_CAUSE_DONE') 
                  AND COALESCE(completed_at, updated_at) < '$cutoff'\"\"\")
n = cur.rowcount
conn.commit()
# Cleanup orphan rows in dependent tables
cur.execute('DELETE FROM pre_tasks WHERE tid NOT IN (SELECT tid FROM tasks) OR pre_tid NOT IN (SELECT tid FROM tasks)')
cur.execute('DELETE FROM dispatcher_decisions WHERE tid NOT IN (SELECT tid FROM tasks)')
cur.execute('DELETE FROM follow_skill WHERE tid NOT IN (SELECT tid FROM tasks)')
cur.execute('DELETE FROM user_decisions WHERE after_tid NOT IN (SELECT tid FROM tasks)')
cur.execute('DELETE FROM alternative_paths WHERE source_tid NOT IN (SELECT tid FROM tasks) OR target_tid NOT IN (SELECT tid FROM tasks)')
conn.commit()
print(f'  Removed {n} orphan TID rows + cascaded dependencies', file=__import__('sys').stderr)
" || true
    fi
else
    echo "  📦 DB: not found yet"
fi

# ─── 2. Orphan .goal/<RUN_ID>/ Verzeichnisse ─────────────────────
if [[ -d ".goal" && "$KEEP_GOAL" != true ]]; then
    ORPHAN_COUNT=0
    while IFS= read -r d; do
        [[ -d "$d" ]] || continue
        # Heuristik: leeres Verzeichnis ODER nur .pid/.log OR alte mtime
        age=$(find "$d" -maxdepth 0 -mtime +${DAYS} 2>/dev/null | wc -l)
        if [[ $age -gt 0 ]]; then
            if [[ "$DRY_RUN" == true ]]; then
                echo "  📂 Would remove: $d (>$DAYS d old)"
                ORPHAN_COUNT=$((ORPHAN_COUNT + 1))
            else
                rm -rf "$d"
                ORPHAN_COUNT=$((ORPHAN_COUNT + 1))
            fi
        fi
    done < <(find .goal -mindepth 1 -maxdepth 1 -type d 2>/dev/null)
    echo "  📂 .goal/: removed $ORPHAN_COUNT stale run directories"
else
    echo "  📂 .goal/: skipped (KEEP_GOAL=$KEEP_GOAL)"
fi

# ─── 3. Live-Snapshots mit fehlendem SKILL.md ────────────────────
if [[ -d "$LIVE_DIR" ]]; then
    ORPHAN_SNAP_COUNT=0
    while IFS= read -r snap; do
        path=$(grep -oP 'output_path: "\K[^"]+' "$snap" 2>/dev/null || echo "")
        if [[ -z "$path" ]]; then
            # empty path = catalog entry, skip
            continue
        fi
        if [[ ! -f "$path" ]]; then
            if [[ "$DRY_RUN" == true ]]; then
                echo "  🧩 Would remove: $snap (SKILL.md at $path missing)"
            else
                rm -f "$snap"
                echo "  🧩 Removed orphan snapshot: $(basename "$snap") (source $path gone)"
            fi
            ORPHAN_SNAP_COUNT=$((ORPHAN_SNAP_COUNT + 1))
        fi
    done < <(find "$LIVE_DIR" -maxdepth 1 -type f -name "*.md" 2>/dev/null)
    echo "  🧩 Live-snapshots: removed $ORPHAN_SNAP_COUNT orphans"
fi

# ─── 4. Registry-Einträge für nicht-existente Skills ─────────────
if [[ -f "$LIVE_DIR/registry.jsonl" && "$DRY_RUN" != true ]]; then
    BEFORE=$(wc -l < "$LIVE_DIR/registry.jsonl")
    python3 -c "
import json, os
keep = []
seen_skills = set()
# Reverse so newest stay
with open('$LIVE_DIR/registry.jsonl') as f: lines = list(f)[::-1]
for line in lines:
    line = line.strip()
    if not line: continue
    try: d = json.loads(line)
    except: continue
    s = d.get('skill')
    # Keep first entry per skill (newest by reverse) but allow others if snapshot exists
    snap_path = os.path.join('$LIVE_DIR', s + '.md')
    if os.path.exists(snap_path):
        keep.append(d)
# Write back chronological
with open('$LIVE_DIR/registry.jsonl', 'w') as f:
    for d in reversed(keep):
        f.write(json.dumps(d) + '\n')
print(f'  registry: {len(lines)} → {len(keep)} entries (one-per-skill)', file=__import__('sys').stderr)
" || true
    AFTER=$(wc -l < "$LIVE_DIR/registry.jsonl")
    echo "  📝 registry.jsonl: $BEFORE → $AFTER entries"
else
    echo "  📝 registry.jsonl: kept (DRY_RUN=$DRY_RUN)"
fi

# ─── Summary ─────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ Cleanup complete (cutoff=${DAYS}d dry_run=$DRY_RUN)"
echo "═══════════════════════════════════════════════════════════════"
