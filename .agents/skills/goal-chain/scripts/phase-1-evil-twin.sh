#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# phase-1-evil-twin.sh — TID: evil-twin-*  (v2.0 — Independent Thinker Spawn)
#
# v2.0 CHANGE: Statt dass der AKTUELLE Agent den Widerspruch selbst
# schreibt, wird thinker-with-files-gemini als UNABHÄNGIGER Spiegel-
# Thinker gespawnt. Gleiche Datenlage, adversarial Prompt, EIGENES
# Reasoning. Kein Selbstreferenz-Artefakt mehr.
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"

RUN_ID="${1:?Usage: bash phase-1-evil-twin.sh RUN_ID TID}"
TID="${2:?}"

ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

# Extract SECTION from DB (TID format: {PROJEKT}-{RUN_ID}-{PHASE}-{SECTION})
SECTION=$(task_field "$TID" "phase_section")
INPUT_ARTIFACT=$(task_field "$TID" "input_artifacts")
GOAL=$(task_field "$TID" "goal")
OUTPUT_FILE=$(task_field "$TID" "output_artifact")

case "$SECTION" in
    evil-twin-1) THINKER="brainstorming (Design)"
        QUESTION="Welche Grundannahmen im Design sind FALSCH? Was wenn das Gegenteil der Design-Entscheidungen wahr ist? Welche Alternative wurde NICHT bedacht?" ;;
    evil-twin-2) THINKER="writing-plans (Implementierungsplan)"
        QUESTION="Warum SCHEITERT dieser Plan? Welche Annahmen über Technologie, Architektur oder Reihenfolge sind falsch? Was wenn der Plan in umgekehrter Reihenfolge ausgeführt werden müsste?" ;;
    evil-twin-3) THINKER="improve-codebase-architecture (Architektur-Review)"
        QUESTION="Ist die Architektur-Richtung FUNDAMENTAL FALSCH? Welche blinden Flecken hat die Analyse? Welche Architektur-Entscheidung wurde als 'offensichtlich' angenommen ohne sie zu hinterfragen?" ;;
    evil-twin-4) THINKER="writing-plans V2 (Gap-Schließung)"
        QUESTION="Wurden die Gaps WIRKLICH geschlossen oder nur umformuliert? Welche neuen blinden Flecken hat der V2-Plan? Was wurde in der Eile übersehen?" ;;
    evil-twin-5) THINKER="systematic-debugging (Root-Cause-Analyse)"
        QUESTION="Ist die Root-Cause-Analyse wirklich die TIEFSTE Ursache? Was wenn das Problem SYMPTOM eines noch tieferen Architekturfehlers ist?" ;;
    evil-twin-6) THINKER="implementer (Code-Implementierung)"
        QUESTION="Implementiert dieser Code das RICHTIGE Problem? Was wenn die Anforderung falsch verstanden wurde? Ist die Implementierung fundamental richtig oder nur technisch korrekt?" ;;
    evil-twin-7) THINKER="documentation-writer (Dokumentation)"
        QUESTION="Was FEHLT in der Doku? Welcher Use-Case wurde vergessen? Welcher Leser-Typ wird an dieser Doku SCHEITERN? Welche Annahme über Vorwissen ist falsch?" ;;
    *) THINKER="Thinker-Agent"
        QUESTION="Welche Grundannahmen wurden getroffen? Was wenn das Gegenteil wahr ist?" ;;
esac

agent_header "$TID" "👯 Evil Twin — nach: $THINKER"

# ─── v2.0: Independent Thinker Spawn ────────────────────────────
# Der Agent soll NICHT selbst den Widerspruch schreiben.
# Stattdessen: thinker-with-files-gemini mit identischer Datenlage spawnen.

# Resolve absolute path for the input artifact
if [[ -n "$INPUT_ARTIFACT" && -f "$INPUT_ARTIFACT" ]]; then
    INPUT_ABS="$(realpath "$INPUT_ARTIFACT" 2>/dev/null || echo "$INPUT_ARTIFACT")"
else
    INPUT_ABS=""
fi

cat <<INSTRUCTION

## 📋 KONTEXT (NUR das brauchst du)

**Original-Thinker-Output:** $INPUT_ARTIFACT
**Goal:** $GOAL

## 🎯 DEINE AUFGABE: INDEPENDENT THINKER SPAWNEN

SPAWNE thinker-with-files-gemini als BÖSEN ZWILLING.
Der Thinker bekommt EXAKT dieselben Daten wie der Original-Thinker,
aber DENKT UNABHÄNGIG — eigenes Reasoning, kein Selbstreferenz-Artefakt.

**Schritte:**

1. Lies das Original-Thinker-Output: $INPUT_ARTIFACT
2. Spawne thinker-with-files-gemini mit:
   - **filePaths:** ["$INPUT_ABS"]
   - **prompt:** (siehe ADVERSARIAL PROMPT unten)
3. Der Thinker schreibt seinen Widerspruch — DU SCHREIBST IHN NICHT SELBST.
4. Nimm den Thinker-Output und speichere ihn NACH $OUTPUT_FILE.
5. Führe dann aus: bash $SCRIPT_DIR/complete.sh $TID DONE

## 👯 ADVERSARIAL PROMPT (an den Thinker)

\`\`\`
Du bist der BÖSE ZWILLING des Thinker-Agents der "$THINKER" ausgeführt hat.
Deine Aufgabe: FINDE DIE FUNDAMENTALEN SCHWACHSTELLEN und WIDERSPRICH.

REGELN:
1. Du hast EXAKT die gleichen Daten, Files und Kontext wie der Original-Thinker.
2. Dein Ziel ist NICHT, Fehler zu finden — sondern die GRUNDANNAHMEN in Frage zu stellen.
3. Denke in die KOMPLETT ENTGEGENGESETZTE RICHTUNG.
4. IGNORIERE: Versionsnummern, Naming, Syntax, Formatierung — das sind KEINE Widersprüche.
5. FINDE: Was wenn das Gegenteil wahr ist? Was wenn der Ansatz komplett falsch ist?
6. FRAGE: Welche stillschweigenden Annahmen wurden getroffen?
7. FORDERE: Beweise, nicht Behauptungen.

FRAGE: $QUESTION

OUTPUT FORMAT:
- ## Fundamentale Widersprüche (max 3)
- ## Bewertung: FUNDAMENTAL / OBERFLÄCHLICH
- ## Synthese-Vorschlag (wenn FUNDAMENTAL)
\`\`\`

INSTRUCTION

agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE (nach thinker-with-files-gemini spawn)"
notify_dashboard "AWAITING_THINKER_SPAWN" "$TID" "$(task_field "$TID" "output_artifact")"

echo ""
echo "🤖 AGENT: Spawne thinker-with-files-gemini mit filePaths=['$INPUT_ABS'] + adversarial prompt."
echo "   Danach: Schreibe Thinker-Output nach $OUTPUT_FILE"
echo "   Danach: bash $SCRIPT_DIR/complete.sh $TID DONE"
echo ""
