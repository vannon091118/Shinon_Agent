#!/bin/bash
# phase-2-debugging.sh
# Synthese-Schritt nach evil-twin-4: liest result.verdict/result.objections aus
# evil-twin-4.result.json (STRUKTUR, nicht Prosa). FUNDAMENTAL → Synthese
# (Kritikpunkte in die Root-Cause-Analyse einarbeiten), OBERFLÄCHLICH → verwerfen.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash phase-2-debugging.sh RUN_ID TID}"
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

Der Böse Zwilling hat FUNDAMENTALE Widersprüche im Plan V2 gefunden.
Diese MÜSSEN in die Root-Cause-Analyse EINFLIESSEN — nicht ignorieren,
nicht nur erwähnen. Jeder Kritikpunkt MUSS als eigener Gap-Block auftauchen.

Kritikpunkte (aus ${ET_RESULT}):
${ET_OBJECTIONS:-(keine konkreten Einwände geliefert — entscheide selbst, ob eine Synthese nötig ist)}

Regel: Jeder Kritikpunkt wird in der Root-Cause-Analyse entweder (a) durch
eine konkrete Ursachen-Hypothese adressiert ODER (b) explizit begründet
zurückgewiesen."
    SYNTH_MODE="FUNDAMENTAL"
elif [[ "$ET_VERDICT" == "OBERFLÄCHLICH" ]]; then
    ET_DIRECTIVE="## 👯 EVIL-TWIN-VERWERFUNG (verdict: OBERFLÄCHLICH)

Der Böse Zwilling fand NUR Oberflächliches — kein fundamentaler Widerspruch.
Kritik VERWERFEN. Root-Cause-Analyse direkt aus Plan V2."
    SYNTH_MODE="OBERFLÄCHLICH"
else
    ET_DIRECTIVE="## 👯 EVIL-TWIN: kein .result.json gefunden

Kein strukturiertes Result vorhanden — Root-Cause-Analyse direkt aus Plan V2."
    SYNTH_MODE="NONE"
fi

# Audit-Trail: der Synthese-Schritt loggt den konsumierten Verdict.
record_decision "$TID" "EVIL_TWIN_SYNTHESIS:debugging" "$SYNTH_MODE" \
    "debugging liest verdict='${ET_VERDICT:-?}' aus ${ET_RESULT:-<kein result.json>}" "" "" || true

agent_header "$TID" "Phase 2.2 Systematic Debugging (Synthese nach Evil Twin)"
emit_user_input_start "phase-2-debugging.sh"
cat <<INSTRUCTION

## Input Plan V2: $INPUT_ARTIFACT
## Goal: $GOAL
## Skill: $SKILL

${ET_DIRECTIVE}

## Aufgabe
1. Lade systematic-debugging Skill.
2. Finde Root-Cause fuer jede ungeloeste Gap im Plan V2.
3. Self-Check: Document root cause.

Output nach $OUTPUT_FILE:
- # Root-Cause-Analyse
- ## Gap 1: Symptom / Root-Cause / Empfehlung
- ## Gap 2 ...
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
