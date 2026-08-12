#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-media-generation.sh — STACK: KREATIV — Skill: design/media-generation
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-media-generation.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "KREATIV media-generation"
emit_user_input_start "chain-media-generation.sh"
cat <<INSTRUCTION
## 🎯 AUFGABE
1. Lade den media-generation Skill via skill-Tool
2. Generiere benötigte Media-Assets (Bilder, Icons, Banner)
3. Achte auf: Konsistenz mit Design-System, passende Auflösungen
4. Self-Check: Alle Assets exportiert, Formate korrekt

## 📤 OUTPUT → $OUTPUT_FILE
```
# Media Generation Log
## Generated Assets: ...
## Formats: ...
## Usage Guidelines: ...
```
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
