#!/bin/bash
# phase-1-architecture.sh
# Synthese-Schritt nach evil-twin-2: liest result.verdict/result.objections aus
# evil-twin-2.result.json (STRUKTUR, nicht Prosa). FUNDAMENTAL → Synthese
# (Kritik in die Architektur einarbeiten), OBERFLÄCHLICH → verwerfen.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash phase-1-architecture.sh RUN_ID TID}"
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

Der Böse Zwilling hat FUNDAMENTALE Widersprüche im Plan V1 gefunden.
Diese MÜSSEN in die Architektur EINFLIESSEN — nicht ignorieren, nicht nur erwähnen.

Kritikpunkte (aus ${ET_RESULT}):
${ET_OBJECTIONS:-(keine konkreten Einwände geliefert — entscheide selbst, ob eine Synthese nötig ist)}

Regel: Jeder Kritikpunkt wird in der Architektur entweder (a) durch eine
konkrete Architektur-Anpassung adressiert ODER (b) explizit begründet
zurückgewiesen."
    SYNTH_MODE="FUNDAMENTAL"
elif [[ "$ET_VERDICT" == "OBERFLÄCHLICH" ]]; then
    ET_DIRECTIVE="## 👯 EVIL-TWIN-VERWERFUNG (verdict: OBERFLÄCHLICH)

Der Böse Zwilling fand NUR Oberflächliches — kein fundamentaler Widerspruch.
Kritik VERWERFEN. Keine Synthese nötig: baue die Architektur direkt aus dem Plan."
    SYNTH_MODE="OBERFLÄCHLICH"
else
    ET_DIRECTIVE="## 👯 EVIL-TWIN: kein .result.json gefunden

Kein strukturiertes Result vorhanden — Architektur direkt aus dem Plan ableiten."
    SYNTH_MODE="NONE"
fi

# Audit-Trail: der Synthese-Schritt loggt den konsumierten Verdict.
record_decision "$TID" "EVIL_TWIN_SYNTHESIS:architecture" "$SYNTH_MODE" \
    "architecture liest verdict='${ET_VERDICT:-?}' aus ${ET_RESULT:-<kein result.json>}" "" "" || true

agent_header "$TID" "Phase 1.3 Architecture Review (Synthese nach Evil Twin)"
emit_user_input_start "phase-1-architecture.sh"
cat <<INSTRUCTION

## Input Plan: $INPUT_ARTIFACT
## Goal: $GOAL
## Skill: $SKILL

${ET_DIRECTIVE}

## Aufgabe
1. Lade improve-codebase-architecture Skill.
2. Analysiere Codebase-Architektur im Kontext des Goals.
3. Finde passende Architektur-Kandidaten.
4. Self-Check: grilling loop, domain model current.

Output als HTML nach $OUTPUT_FILE:
- Architektur-Uebersicht
- Betroffene Komponenten
- Aenderungs-Vorschlaege
- Risiko-Bewertung
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
