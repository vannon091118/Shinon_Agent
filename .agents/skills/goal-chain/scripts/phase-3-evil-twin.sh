#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# phase-3-evil-twin.sh — TID: evil-twin-6 (v2.0 — Independent Thinker Spawn)
#
# v2.0 CHANGE: thinker-with-files-gemini wird als UNABHÄNGIGER
# Spiegel-Thinker gespawnt. Nicht mehr vom selben Agent geschrieben.
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash phase-3-evil-twin.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
INPUT_ARTIFACT=$(task_field "$TID" "input_artifacts")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "👯 Evil Twin — Phase 3 (Implementierung)"

# Resolve absolute path
if [[ -n "$INPUT_ARTIFACT" && -f "$INPUT_ARTIFACT" ]]; then
    INPUT_ABS="$(realpath "$INPUT_ARTIFACT" 2>/dev/null || echo "$INPUT_ARTIFACT")"
else
    INPUT_ABS=""
fi

cat <<INSTRUCTION

## 📋 KONTEXT

**Implementierungs-Log:** $INPUT_ARTIFACT
**Goal:** $GOAL

## 🎯 DEINE AUFGABE: INDEPENDENT THINKER SPAWNEN

SPAWNE thinker-with-files-gemini als BÖSEN ZWILLING für Phase 3.
Der Thinker prüft FUNDAMENTALE RICHTIGKEIT (nicht Spec-Konformität —
das macht der spec-reviewer).

**Schritte:**

1. Lies die Implementierung: $INPUT_ARTIFACT
2. Spawne thinker-with-files-gemini mit:
   - **filePaths:** ["$INPUT_ABS"]
   - **prompt:** (siehe ADVERSARIAL PROMPT unten)
3. Der Thinker schreibt seinen Widerspruch — DU SCHREIBST IHN NICHT SELBST.
4. Nimm den Thinker-Output und speichere ihn NACH $OUTPUT_FILE.
5. Führe dann aus: bash $SCRIPT_DIR/complete.sh $TID DONE

## 👯 ADVERSARIAL PROMPT (an den Thinker)

\`\`\`
Du bist der BÖSE ZWILLING des Phase-3-Implementers.
Deine Aufgabe: Prüfe FUNDAMENTALE RICHTIGKEIT.

FRAGE: Implementiert dieser Code das RICHTIGE Problem?
- Was wenn die Anforderung falsch verstanden wurde?
- Ist die Implementierung fundamental richtig oder nur technisch korrekt?
- Was wenn das Feature komplett ANDERS implementiert werden müsste?

REGELN:
1. Gleiche Datenlage wie der Implementer.
2. IGNORIERE Syntax, Naming, Code-Stil.
3. FINDE die tiefsten Annahmen und kehre sie um.

OUTPUT:
- ## Fundamentale Widersprüche (max 3)
- ## Bewertung: FUNDAMENTAL / OBERFLÄCHLICH
- ## Synthese-Vorschlag (wenn FUNDAMENTAL)
\`\`\`

INSTRUCTION

agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE (nach thinker-with-files-gemini spawn)"
notify_dashboard "AWAITING_THINKER_SPAWN" "$TID" "$OUTPUT_FILE"
echo ""
echo "🤖 AGENT: Spawne thinker-with-files-gemini mit filePaths=['$INPUT_ABS'] + adversarial prompt."
echo "   Danach: Schreibe Thinker-Output nach $OUTPUT_FILE"
echo "   Danach: bash $SCRIPT_DIR/complete.sh $TID DONE"
echo ""
