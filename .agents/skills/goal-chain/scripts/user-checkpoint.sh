#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# user-checkpoint.sh — INTERACTIVE USER DECISION POINT (multi-way)
# User wählt zwischen mehreren Alternativen oder globale Optionen.
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"

AFTER_TID="${1:?Usage: bash user-checkpoint.sh AFTER_TID [--auto=A|B|C|M|S|X]}"
AUTO_FLAG="${2:-}"

ensure_db

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  🛑 USER CHECKPOINT — MULTI-WAY DECISION                    ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  TID soeben abgeschlossen: $AFTER_TID"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Get TID info via Python (avoids bash pipe-subshell variables bug)
TID_INFO=$(python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()
row = cur.execute('SELECT phase, phase_section, status, output_artifact, skill_name, run_id FROM tasks WHERE tid=?', ('$AFTER_TID',)).fetchone()
for f in row:
    print(str(f) if f is not None else '')
conn.close()
")
TID_PHASE=$(echo "$TID_INFO" | sed -n '1p')
TID_SECTION=$(echo "$TID_INFO" | sed -n '2p')
TID_STATUS=$(echo "$TID_INFO" | sed -n '3p')
TID_OUTPUT=$(echo "$TID_INFO" | sed -n '4p')
TID_SKILL=$(echo "$TID_INFO" | sed -n '5p')
TID_RUN=$(echo "$TID_INFO" | sed -n '6p')

echo "── Abgeschlossenes TID ───────────────────────────────────────"
echo "  Phase:    $TID_PHASE"
echo "  Section:  $TID_SECTION"
echo "  Status:   $TID_STATUS"
echo "  Skill:    $TID_SKILL"
echo "  Output:   $TID_OUTPUT"
echo ""

if [[ -f "$TID_OUTPUT" ]]; then
    LINES=$(wc -l < "$TID_OUTPUT" 2>/dev/null || echo 0)
    echo "  Output-Datei: ✅ existiert ($LINES Zeilen)"
else
    echo "  Output-Datei: ❌ FEHLT — Drift detected, retry nötig"
fi
echo ""

# Load alternatives via Python
echo "── Multi-Way Optionen ───────────────────────────────────────"
ALTS_RAW=$(python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()
rows = cur.execute('''
    SELECT ap.path_label, ap.target_tid, t.phase, t.phase_section, t.skill_name, ap.rationale, ap.tradeoffs
    FROM alternative_paths ap
    JOIN tasks t ON ap.target_tid = t.tid
    WHERE ap.source_tid = ?
    ORDER BY ap.ranking, ap.path_label
''', ('$AFTER_TID',)).fetchall()
for label, target, phase, section, skill, rat, tof in rows:
    print(f'{label}|{target}|{phase}|{section}|{skill}|{rat}|{tof}')
conn.close()
" 2>/dev/null)

if [[ -z "$ALTS_RAW" ]]; then
    echo "  Keine alternativen Pfade definiert → continue mit nächstem PENDING TID"
    DEFAULT_NEXT=$(next_pending_tid "$TID_RUN")
    echo "  Next: $DEFAULT_NEXT"
    db_exec "INSERT INTO user_decisions (after_tid, decision) VALUES ('$AFTER_TID', 'CONTINUE');"
    echo ""
    echo "🤖 AGENT: bash $SCRIPT_DIR/complete.sh $AFTER_TID DONE"
    exit 0
fi

OPTIONS_LIST=()
echo "  Folgende Pfade sind verfügbar:"
echo ""
while IFS='|' read -r label target phase section skill rat tof; do
    [[ -z "$label" ]] && continue
    echo "  [$label] → $target"
    echo "       Phase/Section: $phase:$section"
    echo "       Skill: $skill"
    [[ -n "$rat" ]] && echo "       Warum: $rat"
    [[ -n "$tof" ]] && echo "       Tradeoff: $tof"
    echo ""
    OPTIONS_LIST+=("$label:$target")
done <<< "$ALTS_RAW"

echo "── Globale Optionen ─────────────────────────────────────────"
echo "  [C] CONTINUE — Default folgen (Option A wenn vorhanden)"
echo "  [M] MODIFY — selbst Hand anlegen am Output, dann fortfahren"
echo "  [S] SKIP — nächsten TID überspringen"
echo "  [X] ABORT — Pipeline stoppen"
echo ""

# Get decision
if [[ "$AUTO_FLAG" =~ --auto= ]]; then
    DECISION="${AUTO_FLAG#--auto=}"
    echo "  (AUTO-MODE: $DECISION)"
elif [[ -t 0 ]]; then
    echo ""
    read -r -p "🎯 Deine Entscheidung [A/B/C/M/S/X]: " DECISION
else
    DECISION="${OPTIONS_LIST[0]%%:*}"
    echo "  (NON-INTERACTIVE: default → $DECISION)"
fi

DECISION=$(echo "$DECISION" | tr '[:lower:]' '[:upper:]')

SELECTED_TID=""
RATIONALE=""
case "$DECISION" in
    A|B|C|D|E)
        for opt in "${OPTIONS_LIST[@]}"; do
            if [[ "${opt%%:*}" == "$DECISION" ]]; then
                SELECTED_TID="${opt#*:}"
                RATIONALE="User chose path $DECISION"
                break
            fi
        done
        if [[ -z "$SELECTED_TID" ]]; then
            echo "❌ Ungültige Option: $DECISION"
            exit 1
        fi
        ;;
    C|CONTINUE)
        DEFAULT_OPT="${OPTIONS_LIST[0]}"
        if [[ -n "$DEFAULT_OPT" ]]; then
            SELECTED_TID="${DEFAULT_OPT#*:}"
            RATIONALE="User chose CONTINUE → default path"
        else
            RATIONALE="No path available"
        fi
        ;;
    M|MODIFY)
        echo ""
        echo "  MODIFY-Modus: User bearbeitet Output selbst."
        echo "    Output: $TID_OUTPUT"
        echo "    Empfehlung: Edit → bash $SCRIPT_DIR/verify-template.sh $AFTER_TID $TID_OUTPUT → dann complete.sh"
        echo ""
        SELECTED_TID=""
        RATIONALE="User wants to MODIFY output before continuing"
        ;;
    S|SKIP)
        SELECTED_TID=""
        RATIONALE="User SKIPPED future branch"
        ;;
    X|ABORT)
        echo ""
        echo "🛑 PIPELINE ABORTED by user"
        db_exec "INSERT INTO user_decisions (after_tid, decision, user_rationale) VALUES ('$AFTER_TID', 'ABORT', 'User aborted via checkpoint');"
        db_exec "UPDATE tasks SET status='FAILED' WHERE run_id='$TID_RUN' AND status='PENDING';"
        exit 0
        ;;
    *)
        echo "❌ Ungültige Option: $DECISION"
        exit 1
        ;;
esac

# Record decision
db_exec "INSERT INTO user_decisions (after_tid, decision, selected_tid, user_rationale) VALUES ('$AFTER_TID', '$DECISION', '$SELECTED_TID', '$RATIONALE');"

echo ""
echo "✅ Decision recorded: $DECISION"
if [[ -n "$SELECTED_TID" ]]; then
    echo "   Selected next TID: $SELECTED_TID"
    echo ""
    echo "🤖 AGENT:"
    echo "   1. bash $SCRIPT_DIR/complete.sh $AFTER_TID DONE"
    echo "   2. bash $(script_for_tid "$SELECTED_TID") $TID_RUN $SELECTED_TID"
else
    echo ""
    echo "🤖 AGENT: bash $SCRIPT_DIR/complete.sh $AFTER_TID DONE"
fi
