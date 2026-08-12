#!/bin/bash
# phase-3-reviewer.sh
# Synthese-Schritt nach evil-twin-6: liest result.verdict/result.objections aus
# evil-twin-6.result.json (STRUKTUR, nicht Prosa). FUNDAMENTAL → Synthese
# (Kritikpunkte in den Code-Review als Pflicht-Prüfung einarbeiten),
# OBERFLÄCHLICH → verwerfen.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash phase-3-reviewer.sh RUN_ID TID}"
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

Der Böse Zwilling hat FUNDAMENTALE Widersprüche in der Implementierung gefunden.
Diese MÜSSEN als Pflicht-Prüfungen in den Code-Review EINFLIESSEN — der
spec-reviewer und der code-quality-reviewer MÜSSEN jeden Kritikpunkt explizit
abklopfen.

Kritikpunkte (aus ${ET_RESULT}):
${ET_OBJECTIONS:-(keine konkreten Einwände geliefert — entscheide selbst, ob eine Synthese nötig ist)}

Regel: Pro Kritikpunkt eine Zeile in der Review-Tabelle mit Status UND Beleg.
Status ohne Beleg = RE-REVIEW."
    SYNTH_MODE="FUNDAMENTAL"
elif [[ "$ET_VERDICT" == "OBERFLÄCHLICH" ]]; then
    ET_DIRECTIVE="## 👯 EVIL-TWIN-VERWERFUNG (verdict: OBERFLÄCHLICH)

Der Böse Zwilling fand NUR Oberflächliches — kein fundamentaler Widerspruch.
Kritik VERWERFEN. Code-Review läuft mit Standard-Prüfungen."
    SYNTH_MODE="OBERFLÄCHLICH"
else
    ET_DIRECTIVE="## 👯 EVIL-TWIN: kein .result.json gefunden

Kein strukturiertes Result vorhanden — Code-Review mit Standard-Prüfungen."
    SYNTH_MODE="NONE"
fi

# Audit-Trail: der Synthese-Schritt loggt den konsumierten Verdict.
record_decision "$TID" "EVIL_TWIN_SYNTHESIS:reviewer" "$SYNTH_MODE" \
    "reviewer liest verdict='${ET_VERDICT:-?}' aus ${ET_RESULT:-<kein result.json>}" "" "" || true

agent_header "$TID" "Phase 3.2 Code Review (Synthese nach Evil Twin)"
emit_user_input_start "phase-3-reviewer.sh"
cat <<INSTRUCTION

## Input Implementierungs-Log: $INPUT_ARTIFACT
## Goal: $GOAL
## Skill: $SKILL

${ET_DIRECTIVE}

## Aufgabe
1. Lade dispatching-parallel-agents Skill.
2. ZWEI Reviewer parallel:
   a. spec-reviewer: passt Code zur Spec?
   b. code-quality-reviewer: patterns, errors, quality, tests
3. Bei FAIL: zurueck zu implementer, RE-REVIEW.
4. Bei PASS: finalisiere Review-Log.

Output nach $OUTPUT_FILE als Tabellen:
- Spec-Review: Task / Status / Issues
- Quality-Review: File / Status / Issues
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
