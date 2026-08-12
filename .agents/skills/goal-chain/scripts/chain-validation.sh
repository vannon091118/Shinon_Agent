#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-validation.sh — STACK: LOGISCH — Skill: security/codex-security/validation
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-validation.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

## 🎯 AUFGABE
1. Lade den validation Skill via skill-Tool
2. Validiere den aktuellen Output gegen die Spec
3. Finde Diskrepanzen, Inkonsistenzen, Edge-Cases
4. Self-Check: Jede Abweichung mit Beweis dokumentiert

## 📤 OUTPUT → $OUTPUT_FILE
\`\`\`
# Validation Report
## Spec-Conformance: PASS/FAIL
## Abweichungen: ...
## Edge-Cases getestet: ...
## Empfehlung: ...
\`\`\`
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh"
echo ""
echo "🤖 AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
