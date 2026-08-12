#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# phase-2-writing-plans-v2.sh — TID: P2-writing-plans-v2
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"

RUN_ID="${1:?Usage: bash phase-2-writing-plans-v2.sh RUN_ID TID}"
TID="${2:?}"

ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

INPUT_ARTIFACT=$(task_field "$TID" "input_artifacts")
GOAL=$(task_field "$TID" "goal")
SKILL=$(task_field "$TID" "skill_name")
OUTPUT_FILE=$(task_field "$TID" "output_artifact")
GATE_RESULT=$(db_query "SELECT decision_value FROM dispatcher_decisions WHERE tid LIKE '%-G1-2-verify' AND run_id='$RUN_ID' ORDER BY decision_id DESC LIMIT 1;" | head -1)

agent_header "$TID" "Phase 2.1 — Writing Plans V2 (Gap-Schließung)"
emit_user_input_start "phase-2-writing-plans-v2.sh"

cat <<INSTRUCTION

## 📋 KONTEXT (NUR das brauchst du)

**Input (Original Plan):** $INPUT_ARTIFACT
**Gate 1→2 Ergebnis:** $GATE_RESULT
**Goal:** $GOAL
**Skill zu laden:** $SKILL

## 🎯 AUFGABE

1. Lade den writing-plans Skill via skill-Tool (RE-INVOKE)
2. Lies den aktuellen Plan
3. SCHLIESSE ALLE Lücken aus der Gap-Liste
4. NICHTS auf spätere Phasen verschieben
5. Self-Check: 'Keep refining until all gaps are closed'

## 📤 OUTPUT FORMAT

Schreibe PLAN V2 nach $OUTPUT_FILE.
Gleiches Format wie Plan V1, aber alle Gaps geschlossen.
KEINE 'UNCLEAR', 'UNRESOLVED', 'TBD', 'TODO' im Plan V2.

INSTRUCTION

agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$(task_field "$TID" "output_artifact")"

echo ""
echo "🤖 AGENT: Nachdem du $OUTPUT_FILE geschrieben hast, führe aus:"
echo "   bash $SCRIPT_DIR/complete.sh $TID DONE"
echo ""
