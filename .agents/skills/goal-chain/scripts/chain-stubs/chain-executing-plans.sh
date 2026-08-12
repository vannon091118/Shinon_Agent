#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-executing-plans.sh — STACK: AUTONOM — Skill: agents/executing-plans
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-executing-plans.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "AUTONOM executing-plans"
emit_user_input_start "chain-executing-plans.sh"
cat <<INSTRUCTION
## 🎯 AUFGABE
1. Lade den executing-plans Skill via skill-Tool
2. Prüfe den aktuellen Execution-Plan auf Vollständigkeit
3. Identifiziere: Was wurde umgesetzt? Was fehlt? Was ist blockiert?
4. Self-Check: Jeder Task hat klaren Next-Step

## 📤 OUTPUT → $OUTPUT_FILE
```
# Execution Log
## Completed: ...
## In Progress: ...
## Blocked: ...
## Next Steps: ...
```
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
