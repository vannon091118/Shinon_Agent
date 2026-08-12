#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# verify-state.sh — Recovery: find current state and next step
# Usage: bash verify-state.sh RUN_ID
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"

RUN_ID="${1:?Usage: bash verify-state.sh RUN_ID}"

ensure_db

echo "══════════════════════════════════════════════════════════"
echo "  VERIFY STATE: $RUN_ID"
echo "══════════════════════════════════════════════════════════"

# Find zombie TIDs (IN_PROGRESS but no recent activity)
echo ""
echo "── Zombie-Check ────────────────────────────────────────"
ZOMBIES=$(db_query "SELECT tid, phase_section, updated_at FROM tasks WHERE run_id='$RUN_ID' AND status='IN_PROGRESS';")
if [[ -n "$ZOMBIES" ]]; then
    echo "$ZOMBIES" | while IFS='|' read -r tid section updated; do
        echo "  ⚠️  $tid ($section) — IN_PROGRESS since $updated"
        echo "     → bash $SCRIPT_DIR/complete.sh $tid FAIL  (wenn wirklich gescheitert)"
        echo "     → ODER: bash $(script_for_tid "$tid") $RUN_ID $tid  (wiederholen)"
    done
else
    echo "  ✅ Keine Zombie-TIDs"
fi

# Show all TIDs with status
echo ""
echo "── Status-Übersicht ────────────────────────────────────"
tids_for_run "$RUN_ID" | while IFS='|' read -r tid phase section status; do
    local icon=" "
    case "$status" in
        DONE)    icon="✅" ;;
        IN_PROGRESS) icon="🔄" ;;
        FAILED)  icon="❌" ;;
        SKIPPED) icon="⏭️ " ;;
        ROOT_CAUSE_DONE) icon="🎯" ;;
        *)       icon="⏳" ;;
    esac
    printf "  %s  %-55s %s\n" "$icon" "$tid" "$status"
done

# Find next pending
NEXT_TID=$(next_pending_tid "$RUN_ID")

echo ""
echo "── Nächster Schritt ────────────────────────────────────"
if [[ -z "$NEXT_TID" ]]; then
    echo "  🎉 KEINE ausstehenden TIDs — Run komplett!"
else
    NEXT_SCRIPT=$(script_for_tid "$NEXT_TID")
    echo "  ▶ $NEXT_TID"
    echo "  Befehl: bash $NEXT_SCRIPT $RUN_ID $NEXT_TID"
    
    # Check pre-tasks
    echo ""
    echo "  Pre-Task Status:"
    db_query "SELECT pt.pre_tid, t.status, t.phase_section FROM pre_tasks pt JOIN tasks t ON pt.pre_tid = t.tid WHERE pt.tid='$NEXT_TID';" | while IFS='|' read -r pre status section; do
        local icon="✅"
        [[ "$status" != "DONE" && "$status" != "SKIPPED" && "$status" != "ROOT_CAUSE_DONE" ]] && icon="⏳"
        echo "    $icon $pre ($section): $status"
    done
fi
