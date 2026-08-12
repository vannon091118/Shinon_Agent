#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# phase-2-writing-plans-v2.sh — TID: P2-writing-plans-v2
# Synthese-Schritt (Gap-Schließung): konsumiert zusätzlich zum Gate-Result
# auch result.verdict/result.objections aus evil-twin-2.result.json (STRUKTUR,
# nicht Prosa). FUNDAMENTAL → Synthese, OBERFLÄCHLICH → verwerfen.
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"

RUN_ID="${1:?Usage: bash phase-2-writing-plans-v2.sh RUN_ID TID}"
TID="${2:?}"

ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

INPUT_ARTIFACT=$(task_field "$TID" "input_artifacts")
GOAL=$(task_field "$TID" "goal")
SKILL=$(task_field "$TID" "skill_name")
OUTPUT_FILE=$(task_field "$TID" "output_artifact")
GATE_RESULT=$(db_query "SELECT decision_value FROM dispatcher_decisions WHERE tid LIKE '%-G1-2-verify' AND run_id='$RUN_ID' ORDER BY decision_id DESC LIMIT 1;" | head -1)

# ─── Evil-Twin-Synthese: verdict/points aus .result.json (nicht Prosa) ──
ET_RESULT=$(evil_twin_result_json "$TID")
read_evil_twin_result "$ET_RESULT"

if [[ "$ET_VERDICT" == "FUNDAMENTAL" ]]; then
    ET_DIRECTIVE="## 👯 EVIL-TWIN-SYNTHESE (verdict: FUNDAMENTAL)

Der Böse Zwilling hat FUNDAMENTALE Widersprüche im Plan V1 gefunden.
Diese MÜSSEN in Plan V2 EINFLIESSEN — nicht ignorieren, nicht nur erwähnen.

Kritikpunkte (aus ${ET_RESULT}):
${ET_OBJECTIONS:-(keine konkreten Einwände geliefert — entscheide selbst, ob eine Synthese nötig ist)}

Regel: Jeder Kritikpunkt wird in Plan V2 entweder (a) durch eine konkrete
Änderung adressiert ODER (b) explizit begründet zurückgewiesen."
    SYNTH_MODE="FUNDAMENTAL"
elif [[ "$ET_VERDICT" == "OBERFLÄCHLICH" ]]; then
    ET_DIRECTIVE="## 👯 EVIL-TWIN-VERWERFUNG (verdict: OBERFLÄCHLICH)

Der Böse Zwilling fand NUR Oberflächliches am Plan V1 — kein fundamentaler
Widerspruch. Kritik VERWERFEN, keine Synthese nötig."
    SYNTH_MODE="OBERFLÄCHLICH"
else
    ET_DIRECTIVE="## 👯 EVIL-TWIN: kein .result.json gefunden

Kein strukturiertes Result vorhanden — schließe nur die Gate-Gaps."
    SYNTH_MODE="NONE"
fi

record_decision "$TID" "EVIL_TWIN_SYNTHESIS" "$SYNTH_MODE" \
    "writing-plans-v2 liest verdict='${ET_VERDICT:-?}' aus ${ET_RESULT:-<kein result.json>}" "" "" || true

agent_header "$TID" "Phase 2.1 — Writing Plans V2 (Gap-Schließung)"
emit_user_input_start "phase-2-writing-plans-v2.sh"

cat <<INSTRUCTION

## 📋 KONTEXT (NUR das brauchst du)

**Input (Original Plan):** $INPUT_ARTIFACT
**Gate 1→2 Ergebnis:** ${GATE_RESULT:-UNBEKANNT}
**Goal:** $GOAL
**Skill zu laden:** $SKILL

${ET_DIRECTIVE}

## 🎯 AUFGABE

1. Lade den writing-plans Skill via skill-Tool (RE-INVOKE)
2. Lies den aktuellen Plan
3. SCHLIESSE ALLE Lücken aus der Gap-Liste
4. NICHTS auf spätere Phasen verschieben
5. Self-Check: 'Keep refining until all gaps are closed'

## 📤 OUTPUT FORMAT

Schreibe PLAN V2 nach $OUTPUT_FILE.
Gleiches Format wie Plan V1, aber alle Gaps geschlossen.
KEINE 'UNCLEAR', 'UNRESOLVED', 'TBD', 'TODO' im Plan V2.

INSTRUCTION

agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$(task_field "$TID" "output_artifact")"

echo ""
echo "🤖 AGENT: Nachdem du $OUTPUT_FILE geschrieben hast, führe aus:"
echo "   bash $SCRIPT_DIR/complete.sh $TID DONE"
echo ""
