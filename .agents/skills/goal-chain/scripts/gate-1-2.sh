#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# gate-1-2.sh — TID: G1-2-verify
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"

RUN_ID="${1:?Usage: bash gate-1-2.sh RUN_ID TID}"
TID="${2:?}"

ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

INPUT_ARTIFACT=$(task_field "$TID" "input_artifacts")
GOAL=$(task_field "$TID" "goal")
SKILL=$(task_field "$TID" "skill_name")
OUTPUT_FILE=$(task_field "$TID" "output_artifact")

cat <<INSTRUCTION

## 📋 KONTEXT (NUR das brauchst du)

**Input (Plan):** $INPUT_ARTIFACT
**Goal:** $GOAL
**Skill zu laden:** $SKILL
  → IRON LAW: no completion claim without fresh verification

## 🎯 AUFGABE

1. Lade den verification-before-completion Skill via skill-Tool
2. Lies den Plan aus $INPUT_ARTIFACT
3. Prüfe: Deckt der Plan ALLE Anforderungen des Ziels ab?
4. IRON LAW: no completion claim without fresh verification

## 📤 OUTPUT FORMAT

Schreibe NACH $OUTPUT_FILE — ERSTE ZEILE MUSS SEIN:

\`\`\`
PASS
\`\`\`
ODER:
\`\`\`
FAIL
<Gap 1>
<Gap 2>
...
\`\`\`

## 🔀 ENTSCHEIDUNG

- **PASS** → Phase 2 wird übersprungen. Führe aus:
  \`bash $SCRIPT_DIR/complete.sh $TID DONE\`
  Dann geht es direkt zu Gate 2→3 weiter.

- **FAIL** → Gap-Liste → Phase 2 startet. Führe aus:
  \`bash $SCRIPT_DIR/complete.sh $TID DONE\`
  Die Chain routet automatisch zu Phase 2.

INSTRUCTION

echo ""
echo "🤖 AGENT: Nachdem du $OUTPUT_FILE geschrieben hast UND die ERSTE ZEILE PASS oder FAIL ist:"
echo "   bash $SCRIPT_DIR/complete.sh $TID DONE"
echo ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
