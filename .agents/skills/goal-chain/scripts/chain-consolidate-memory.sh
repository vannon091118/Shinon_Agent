#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-consolidate-memory.sh — STACK: MEMORY — Skill: agents/consolidate-memory
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-consolidate-memory.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "MEMORY consolidate-memory"
emit_user_input_start "chain-consolidate-memory.sh"
cat <<INSTRUCTION
## 🎯 AUFGABE
1. Lade den consolidate-memory Skill via skill-Tool
2. Analysiere den aktuellen Memory-Stand (KARMA experiences, FactIndex)
3. Konsolidiere: Duplikate mergen, veraltete Facts archivieren, Patterns extrahieren
4. Self-Check: Kein Datenverlust, Konsistenz gewahrt

## 📤 OUTPUT → $OUTPUT_FILE
```
# Memory Consolidation Report
## Merged Facts: ...
## Archived: ...
## New Patterns: ...
## Integrity Check: ...
```
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
