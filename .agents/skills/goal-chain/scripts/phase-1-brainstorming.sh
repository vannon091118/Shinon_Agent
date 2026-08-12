#!/bin/bash
# phase-1-brainstorming.sh — Brainstorming (drift-free)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash phase-1-brainstorming.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
GOAL=$(task_field "$TID" "goal")
SKILL=$(task_field "$TID" "skill_name")
SKILL_PATH="$SKILL_BASE/$SKILL/SKILL.md"
PRE_FOLLOW=$(follow_pre_counts "$TID")

emit_user_input_start "phase-1-brainstorming.sh"
cat <<HEADER

╔══════════════════════════════════════════════════════════════╗
║  TID: $TID
║  Phase: P1 (Planen) | Section: brainstorming
║  Skill: $SKILL → $SKILL_PATH
║  Status: IN_PROGRESS (tee $PRE_FOLLOW)
║  Goal: $GOAL
╚══════════════════════════════════════════════════════════════╝
HEADER

cat <<'TEMPLATE'

═══════════════════════════════════════════════════════════════
📐 OUTPUT-TEMPLATE (GENAU DIESE STRUKTUR)
═══════════════════════════════════════════════════════════════

# Design: <GOAL wiederholen>

## Übersicht
<2-4 Saetze>

## Architektur
- Stack: <z.B. FastAPI+PostgreSQL+React>
- Komponenten: <Liste>
- Datenfluss: <1-2 Saetze>

## Komponenten
| Komponente | Verantwortung | Input | Output |
|---|---|---|---|
| <Name> | <Beschreibung> | ... | ... |

## Datenmodell
- Entities: <Liste>
- Relationships: <Beschreibung>

## Schnittstellen
- API: <z.B. REST/GraphQL>
- Auth: <Strategie>

## Risiken und Annahmen
- Risiko 1: <...> - Mitigation: <...>

## Offene Fragen
- (Wenn keine offen: "Keine - alle Anforderungen klar.")
═══════════════════════════════════════════════════════════════
TEMPLATE

cat <<INSTRUCTION

## KONTEXT
Goal: $GOAL
Skill: $SKILL
Output: $OUTPUT_FILE
Template-ID: design-doc-v1

## Aufgabe (drift-free)
1. Lade brainstorming Skill (skill-Tool).
2. Schreibe Output EXAKT nach Template oben.
3. Ersetze JEDEN Platzhalter durch echten Inhalt.
4. KEINE zusaetzlichen/geloeschten Sektionen.

## DRIFT-WARNING
verify-template.sh prueft 8 SECTION_HEADER. Bei Drift: FAIL mit Diff.
INSTRUCTION

agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: 1) write $OUTPUT_FILE, 2) bash $SCRIPT_DIR/complete.sh $TID DONE"
