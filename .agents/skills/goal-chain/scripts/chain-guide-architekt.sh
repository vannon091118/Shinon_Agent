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

## 🎯 AUFGABE
1. Lade den guide-architekt Skill via skill-Tool
2. Analysiere die Architektur-Anforderungen des Goals
3. Bestimme: Welche Architektur-Patterns passen? Welche Komponenten sind betroffen?
4. Self-Check: Architektur-Entscheidungen dokumentiert, Alternativen erwogen

## 📤 OUTPUT → $OUTPUT_FILE
\`\`\`
# Architecture Guide
## Betroffene Komponenten: ...
## Empfohlene Patterns: ...
## Alternativen: ...
## Risiken: ...
\`\`\`
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh"
echo ""
echo "🤖 AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
