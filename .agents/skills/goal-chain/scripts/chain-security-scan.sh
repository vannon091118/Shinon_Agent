#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-security-scan.sh — STACK: GOVERNANCE — Skill: security/codex-security/security-scan
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-security-scan.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

## 🎯 AUFGABE
1. Lade den security-scan Skill via skill-Tool
2. Scanne den aktuellen Code-Stand auf Security-Lücken
3. Kategorisiere: CRITICAL / HIGH / MEDIUM / LOW
4. Self-Check: Jeder Fund hat CVE-Referenz oder OWASP-Kategorie

## 📤 OUTPUT → $OUTPUT_FILE
\`\`\`
# Security Scan Report
## Critical: ...
## High: ...
## Medium: ...
## Low: ...
## Recommendations: ...
\`\`\`
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh"
echo ""
echo "🤖 AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
