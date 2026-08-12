#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-guide-architekt.sh — STACK: AUTONOM — Skill: agents/guide-architekt
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-guide-architekt.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "AUTONOM guide-architekt"
emit_user_input_start "chain-guide-architekt.sh"
cat <<INSTRUCTION
## 🎯 AUFGABE
1. Lade den guide-architekt Skill via skill-Tool
2. Analysiere die Architektur-Anforderungen des Goals
3. Bestimme: Welche Architektur-Patterns passen? Welche Komponenten sind betroffen?
4. Self-Check: Architektur-Entscheidungen dokumentiert, Alternativen erwogen

## 📤 OUTPUT → $OUTPUT_FILE
```
# Architecture Guide
## Betroffene Komponenten: ...
## Empfohlene Patterns: ...
## Alternativen: ...
## Risiken: ...
```
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
