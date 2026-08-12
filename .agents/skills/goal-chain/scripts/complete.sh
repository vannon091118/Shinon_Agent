#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# complete.sh v2 — Multi-Way Pipeline completion
# After TID writes output → verify-template → user-checkpoint if required
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"

TID="${1:?Usage: bash complete.sh TID [RESULT]}"
RESULT="${2:-DONE}"
AUTO_FLAG="${3:-}"

ensure_db

# Get TID details (de-duplicated — was duplicated twice)
OUTPUT_FILE=$(task_field "$TID" "output_artifact")
REQUIRES_APPROVAL=$(task_field "$TID" "requires_approval")
RUN_ID=$(task_field "$TID" "run_id")

# Final progress for dashboard snapshot
PROGRESS_SNAPSHOT=$(progress_summary "$RUN_ID")

# Refresh HTML snapshot so /preview reflects new state
SNAPSHOT_GLOB=$(find ".goal/${RUN_ID}"* -name 'snapshot.html' 2>/dev/null | head -1 || true)
if [[ -n "$SNAPSHOT_GLOB" && -x "$SCRIPT_DIR/update-snapshot.sh" ]]; then
    bash "$SCRIPT_DIR/update-snapshot.sh" "$RUN_ID" "TID_${RESULT} · $(progress_summary "$RUN_ID")" > "$SNAPSHOT_GLOB" 2>/dev/null || true
fi

# 1. Auto-verification (DRIFT DETECTION) — NUR bei DONE
#    Bugfix (P0-1): verify-template MUSS VOR tid_done laufen.
#    Bugfix (P0-4): verify-template NUR bei RESULT=DONE ausfuehren.
#    Sonst: FAIL auf partial Output → verify schlaegt fehl → exit 1 → tid_fail nie erreicht.
GATE_RESULT=""
if [[ "$RESULT" == "DONE" && -n "$OUTPUT_FILE" && "$OUTPUT_FILE" != "None" && -f "$OUTPUT_FILE" ]]; then
    echo ""
    echo "── DRIFT-VERIFICATION ──────────────────────────────────────"
    if bash "$SCRIPT_DIR/verify-template.sh" "$TID" "$OUTPUT_FILE"; then
        echo "  ✅ Drift-Check bestanden"
    else
        echo ""
        echo "❌ DRIFT DETECTED — bitte Output korrigieren oder mit --force überschreiben"
        if [[ "${4:-}" == "--force" ]]; then
            echo "  --force flag gesetzt: überschreibe Drift-Detection"
        else
            echo "  Hint: bash $SCRIPT_DIR/verify-template.sh $TID $OUTPUT_FILE --explain"
            exit 1
        fi
    fi
    # Extrahiere Gate-Result (PASS/FAIL) fuer Gate-TIDs
    TID_PHASE=$(task_field "$TID" "phase")
    if [[ "$TID_PHASE" == G* ]]; then
        GATE_RESULT=$(head -1 "$OUTPUT_FILE" 2>/dev/null | grep -oE '^(PASS|FAIL)$' || true)
        echo "  🔀 Gate-Result: ${GATE_RESULT:-UNBEKANNT}"
    fi
fi

# 2. Mark current TID as done (NACH erfolgreicher Verifikation)
if [[ "$RESULT" == "DONE" ]]; then
    tid_done "$TID"

    # ─── POST-TASK AUTO SELF-IMPROVE (1/3-Regel) ──────────────────────
    # Nach jedem erfolgreich abgeschlossenen TID: karma simuliert EINEN
    # Cycle (dry-run, kein State-Mutation) und hängt den Snapshot an
    # .learnings/<proj>-sessions.jsonl an. Das ist die Engine-Seite der
    # "MUSS NACH JEDEM durchgeführten Task automatisch passieren"-Regel.
    #
    # Gating: REAL mutation (`karma ml train`) wird durch das Evil-Twin-
    # Gate-TID reguliert (G2-TID in der Pipeline). Wir rufen hier nur den
    # sicheren simulate-Pfad.
    #
    # Wenn Karma oder venv fehlen, kein Crash — wir wollen den Goal-Chain-
    # Ablauf nicht an einem Self-Improve-Aufruf scheitern lassen.
    if [[ -d ".learnings" ]]; then
        PROJECT_NAME="$(basename "$(pwd)")"
        SESSIONS_FILE=".learnings/${PROJECT_NAME}-sessions.jsonl"
        KARMA_PY=".venv/bin/python3"
        [ -x "$KARMA_PY" ] || KARMA_PY=""
        if [[ -n "$KARMA_PY" ]]; then
            TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
            SKILL_OF_TID=$(task_field "$TID" "skill_name" 2>/dev/null || echo "")
            GOAL_OF_TID=$(task_field "$TID" "goal" 2>/dev/null || echo "")
            # Aufruf mit --output json; falls karma das Flag nicht kennt,
            # fällt es zurück auf stdout und wir wrappen es in JSON.
            RAW=$("$KARMA_PY" -m karma.cli ml simulate \
                --project "$PROJECT_NAME" \
                --cycles 1 2>&1 || true)
            # Wenn RAW leer ist (karma noch ohne ml-patterns), notiere "no-op"
            [ -z "$RAW" ] && RAW='{"simulated_actions": []}'
            # Sanitize: raw in einer einzigen JSON-Zeile, neue Zeilen → \n
            RAW_ESCAPED=$(printf '%s' "$RAW" | python3 -c \
                'import sys,json; print(json.dumps(sys.stdin.read()))' 2>/dev/null \
                || printf '"%s"' "$RAW")
            {
                printf '{"timestamp":"%s","tid":"%s","run_id":"%s","skill":"%s","goal":"%s","result":"DONE","simulate_output":%s}\n' \
                    "$TIMESTAMP" "$TID" "$RUN_ID" "$SKILL_OF_TID" "$GOAL_OF_TID" "$RAW_ESCAPED"
            } >> "$SESSIONS_FILE"
            echo "  ↻ self-improve snapshot → $SESSIONS_FILE ($(wc -l < "$SESSIONS_FILE") Zeilen gesamt)"
        fi
    fi

elif [[ "$RESULT" == "ROOT_CAUSE" ]]; then
    # Agent hat Root-Cause-Analyse durchgeführt statt blind zu skippen
    rc_reason="${4:-Gate verified: no gap to fill}"
    tid_root_cause_done "$TID" "$rc_reason"
elif [[ "$RESULT" == "FAIL" ]]; then
    FAIL_REASON="${4:-Agent reported failure}"
    tid_fail "$TID" "$FAIL_REASON"
fi

# Notify live dashboard
notify_dashboard "TID_${RESULT}" "$TID" "$PROGRESS_SNAPSHOT"

# Record decision — ONLY for actual gate results (PASS/FAIL from gate evaluation).
# Worker.sh records its own decisions (CHAIN_SCRIPT_FAILED, EMPTY_OUTPUT, PROMPT_CAPTURED)
# via --auto mode. complete.sh's GATE_RESULT is only meaningful when a gate TID
# produced a real PASS/FAIL evaluation.
if [[ -n "$GATE_RESULT" ]]; then
    record_decision "$TID" "GATE_RESULT" "$GATE_RESULT" "Gate ${TID_PHASE:-?} evaluated: ${GATE_RESULT}" "" ""
elif [[ "$AUTO_FLAG" != "--auto" ]]; then
    # Manual/interactive mode — record the result for audit trail
    if [[ "$RESULT" == "FAIL" ]]; then
        record_decision "$TID" "COMPLETION" "${RESULT}" "FAIL: ${FAIL_REASON:-Agent reported failure}" "" ""
    else
        record_decision "$TID" "COMPLETION" "${RESULT}" "Agent completed TID" "" ""
    fi
fi

# 3. Gate-Phase-Skip (Bugfix P0-2): MUSS VOR user-checkpoint laufen,
#    da user-checkpoint mit exit 0 beendet und die Gate-Logik sonst nie erreicht wird.
TID_PHASE=$(task_field "$TID" "phase")
if [[ "$TID_PHASE" == G* && -n "$GATE_RESULT" ]]; then
    _GATE_NEXT=$(next_pending_tid_after_gate "$RUN_ID" "$TID_PHASE" "$GATE_RESULT" "$OUTPUT_FILE")
    echo "  🔀 Gate-Routing: ${GATE_RESULT} → next=${_GATE_NEXT:-NONE}"
fi

# 4. User Checkpoint (if this TID requires approval)
if [[ "$REQUIRES_APPROVAL" == "1" ]]; then
    echo ""
    echo "🛑 USER APPROVAL REQUIRED — rufe user-checkpoint.sh"
    echo ""
    bash "$SCRIPT_DIR/user-checkpoint.sh" "$TID" "$AUTO_FLAG"
    exit 0
fi

# 5. Find next TID (default linear — gate-skip already applied above)
NEXT_TID=$(next_pending_tid "$RUN_ID")

if [[ -z "$NEXT_TID" ]]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  🎉 ALLE TIDs ABGESCHLOSSEN!                           ║"
    echo "║  Run $RUN_ID ist komplett.                              ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    exit 0
fi

NEXT_SCRIPT=$(script_for_tid "$NEXT_TID")
echo ""
echo "────────────────────────────────────────────────────────"
echo "  ✅ $TID → $RESULT"
echo "  ▶ NÄCHSTER TID (linear): $NEXT_TID"
echo "────────────────────────────────────────────────────────"
echo ""

cat <<NEXTEOF

╔══════════════════════════════════════════════════════════════╗
║  🤖 AGENT: FÜHRE AUS                                       ║
╠══════════════════════════════════════════════════════════════╣
║                                                            ║
║  Befehl:                                                   ║
║    bash $NEXT_SCRIPT $RUN_ID $NEXT_TID                     ║
║                                                            ║
╚══════════════════════════════════════════════════════════════╝

NEXTEOF
