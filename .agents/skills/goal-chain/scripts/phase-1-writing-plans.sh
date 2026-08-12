#!/bin/bash
# phase-1-writing-plans.sh
# Synthese-Schritt nach evil-twin-1: liest result.verdict/result.objections aus
# evil-twin-1.result.json (STRUKTUR, nicht Prosa). FUNDAMENTAL → Synthese
# (Kritik in den Plan einarbeiten), OBERFLÄCHLICH → verwerfen.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash phase-1-writing-plans.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
INPUT_ARTIFACT=$(task_field "$TID" "input_artifacts")
GOAL=$(task_field "$TID" "goal")
SKILL=$(task_field "$TID" "skill_name")

# ─── Evil-Twin-Synthese: verdict/points aus .result.json (nicht Prosa) ──
ET_RESULT=$(evil_twin_result_json "$TID")
read_evil_twin_result "$ET_RESULT"

if [[ "$ET_VERDICT" == "FUNDAMENTAL" ]]; then
    ET_DIRECTIVE="## 👯 EVIL-TWIN-SYNTHESE (verdict: FUNDAMENTAL)

Der Böse Zwilling hat FUNDAMENTALE Widersprüche im Design gefunden.
Diese MÜSSEN in den Plan EINFLIESSEN — nicht ignorieren, nicht nur erwähnen.

Kritikpunkte (aus ${ET_RESULT}):
${ET_OBJECTIONS:-(keine konkreten Einwände geliefert — entscheide selbst, ob eine Synthese nötig ist)}

Regel: Jeder Kritikpunkt wird im Plan entweder (a) durch eine konkrete
Planänderung adressiert ODER (b) explizit begründet zurückgewiesen."
    SYNTH_MODE="FUNDAMENTAL"
elif [[ "$ET_VERDICT" == "OBERFLÄCHLICH" ]]; then
    ET_DIRECTIVE="## 👯 EVIL-TWIN-VERWERFUNG (verdict: OBERFLÄCHLICH)

Der Böse Zwilling fand NUR Oberflächliches — kein fundamentaler Widerspruch.
Kritik VERWERFEN. Keine Synthese nötig: plane direkt aus dem Design."
    SYNTH_MODE="OBERFLÄCHLICH"
else
    ET_DIRECTIVE="## 👯 EVIL-TWIN: kein .result.json gefunden

Kein strukturiertes Result vorhanden — plane direkt aus dem Design."
    SYNTH_MODE="NONE"
fi

# Audit-Trail: der Synthese-Schritt loggt den konsumierten Verdict.
record_decision "$TID" "EVIL_TWIN_SYNTHESIS:writing-plans" "$SYNTH_MODE" \
    "writing-plans liest verdict='${ET_VERDICT:-?}' aus ${ET_RESULT:-<kein result.json>}" "" "" || true

agent_header "$TID" "Phase 1.2 Writing Plans (Synthese nach Evil Twin)"
emit_user_input_start "phase-1-writing-plans.sh"
cat <<INSTRUCTION

## Input Design: $INPUT_ARTIFACT
## Goal: $GOAL
## Skill: $SKILL

${ET_DIRECTIVE}

## Aufgabe
1. Lade writing-plans Skill.
2. Lies Design aus $INPUT_ARTIFACT.
3. Erstelle VOLLSTAENDIGEN Implementierungsplan.
4. KEINE TBDs, TODOs, Platzhalter.
5. Self-Check: alle Luecken geschlossen.

Output nach $OUTPUT_FILE:
- # Implementierungsplan
- ## Phase 1 Tasks (Checkboxen)
- ## Phase 2 Tasks
- ## Phase 3 Tasks
- ## Schaetzung pro Task
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
