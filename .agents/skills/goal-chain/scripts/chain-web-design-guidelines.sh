#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-web-design-guidelines.sh — STACK: GOVERNANCE — Skill: design/web-design-guidelines
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-web-design-guidelines.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

## 🎯 AUFGABE
1. Lade den web-design-guidelines Skill via skill-Tool
2. Prüfe das aktuelle Design gegen etablierte Guidelines
3. Finde Abweichungen und schlage Korrekturen vor
4. Self-Check: Jede Guideline-Verletzung hat konkreten Fix-Vorschlag

## 📤 OUTPUT → $OUTPUT_FILE
\`\`\`
# Design Guidelines Check
## Verletzungen: ...
## Korrekturen: ...
## Best Practices: ...
\`\`\`
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh"
echo ""
echo "🤖 AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
