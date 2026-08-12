#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-python-testing-patterns.sh — STACK: LOGISCH — Skill: testing/python-testing-patterns
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-python-testing-patterns.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "LOGISCH python-testing-patterns"
emit_user_input_start "chain-python-testing-patterns.sh"
cat <<INSTRUCTION
## 🎯 AUFGABE
1. Lade den python-testing-patterns Skill via skill-Tool
2. Analysiere Test-Abdeckung des aktuellen Codes
3. Schreibe/ergänze: Unit-Tests, Integration-Tests, Edge-Cases
4. Self-Check: Coverage > 80%, alle kritischen Pfade getestet

## 📤 OUTPUT → $OUTPUT_FILE
```
# Test Strategy Report
## Current Coverage: ...
## New Tests: ...
## Edge Cases Covered: ...
## CI Integration: ...
```
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
