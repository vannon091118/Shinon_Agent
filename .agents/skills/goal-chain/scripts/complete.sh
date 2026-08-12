#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# complete.sh v2 — Multi-Way Pipeline completion
# After TID writes output → verify-template → FalsificationGate → done
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
# complete.sh is called from different working directories; resolve the repo
# root independently so artifact and audit paths are stable.
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

TID="${1:?Usage: bash complete.sh TID [RESULT]}"
RESULT="${2:-DONE}"
AUTO_FLAG="${3:-}"

ensure_db
OUTPUT_FILE=$(task_field "$TID" "output_artifact")
REQUIRES_APPROVAL=$(task_field "$TID" "requires_approval")
RUN_ID=$(task_field "$TID" "run_id")
PROGRESS_SNAPSHOT=$(progress_summary "$RUN_ID")

# Refresh HTML snapshot so /preview reflects new state.
SNAPSHOT_GLOB=$(find ".goal/${RUN_ID}"* -name 'snapshot.html' 2>/dev/null | head -1 || true)
if [[ -n "$SNAPSHOT_GLOB" && -x "$SCRIPT_DIR/update-snapshot.sh" ]]; then
    bash "$SCRIPT_DIR/update-snapshot.sh" "$RUN_ID" "TID_${RESULT} · $(progress_summary "$RUN_ID")" > "$SNAPSHOT_GLOB" 2>/dev/null || true
fi

GATE_RESULT=""

# 1. Drift verification. Missing artifacts are intentionally not skipped: the
# mandatory FalsificationGate below will record them as a failed probe.
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
    TID_PHASE=$(task_field "$TID" "phase")
    if [[ "$TID_PHASE" == G* ]]; then
        GATE_RESULT=$(head -1 "$OUTPUT_FILE" 2>/dev/null | grep -oE '^(PASS|FAIL)$' || true)
        echo "  🔀 Gate-Result: ${GATE_RESULT:-UNBEKANNT}"
    fi
fi

# 2. Mandatory KARMA FalsificationGate. This is fail-closed and happens before
# tid_done. No --force flag bypasses this governance decision.
FALSIFICATION_LOG=""
if [[ "$RESULT" == "DONE" ]]; then
    TID_PHASE="${TID_PHASE:-$(task_field "$TID" "phase")}"
    TID_SECTION=$(task_field "$TID" "phase_section" 2>/dev/null || true)
    TID_SKILL=$(task_field "$TID" "skill_name" 2>/dev/null || true)
    GATE_PROJECT="$(basename "$REPO_ROOT")"
    GATE_STEP="${TID_SECTION:-${TID_PHASE:-$TID}}"
    GATE_SKILL="${TID_SKILL:-unknown}"
    GATE_OUTPUT="$OUTPUT_FILE"
    if [[ -n "$GATE_OUTPUT" && "$GATE_OUTPUT" != /* ]]; then
        GATE_OUTPUT="$REPO_ROOT/$GATE_OUTPUT"
    fi
    GATE_ARTIFACT_SHA256=""
    if [[ -n "$GATE_OUTPUT" && -f "$GATE_OUTPUT" ]]; then
        GATE_ARTIFACT_SHA256=$(sha256sum "$GATE_OUTPUT" | awk '{print $1}')
    fi

    GATE_LOG_DIR="${SHINON_GATE_LOG_DIR:-$REPO_ROOT/.goal/$RUN_ID}"
    mkdir -p "$GATE_LOG_DIR"
    FALSIFICATION_LOG="$GATE_LOG_DIR/falsification-gate-${TID}.json"
    GATE_STDOUT=$(mktemp)
    GATE_STDERR=$(mktemp)
    GATE_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    KARMA_PY="${SHINON_KARMA_PYTHON:-$REPO_ROOT/.venv/bin/python3}"
    if [[ ! -x "$KARMA_PY" ]]; then
        KARMA_PY="$(command -v python3 || true)"
    fi

    echo ""
    echo "── KARMA FALSIFICATION-GATE ───────────────────────────────"
    echo "  Project:  $GATE_PROJECT"
    echo "  Step:     $GATE_STEP"
    echo "  Skill:    $GATE_SKILL"
    echo "  Artifact: ${GATE_OUTPUT:-<missing>}"
    echo "  Log:      $FALSIFICATION_LOG"

    GATE_RC=127
    if [[ -n "$KARMA_PY" ]]; then
        # KARMA's middleware persistence is isolated under the central Shinon
        # home. An explicit caller override remains authoritative.
        SHINON_HOME_FOR_KARMA="${SHINON_HOME:-$HOME/.shinon}"
        export LLM_MIDDLEWARE_ROOT="${LLM_MIDDLEWARE_ROOT:-$SHINON_HOME_FOR_KARMA/data/karma}"
        set +e
        PYTHONPATH="$REPO_ROOT/karma-main${PYTHONPATH:+:$PYTHONPATH}" \
            "$KARMA_PY" -m karma.core.falsification_gate \
            "$GATE_PROJECT" "$GATE_STEP" "$GATE_SKILL" "$GATE_OUTPUT" --json \
            >"$GATE_STDOUT" 2>"$GATE_STDERR"
        GATE_RC=$?
        set -e
    else
        printf '%s\n' "KARMA Python runtime not found" >"$GATE_STDERR"
    fi

    # Persist complete structured results plus diagnostics. Crashes or invalid
    # JSON become an explicit gate_runtime failure, never an implicit pass.
    python3 - "$GATE_STDOUT" "$GATE_STDERR" "$FALSIFICATION_LOG" \
        "$GATE_RC" "$GATE_PROJECT" "$GATE_STEP" "$GATE_SKILL" "$GATE_OUTPUT" \
        "$GATE_ARTIFACT_SHA256" "$GATE_STARTED_AT" "$TID" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

stdout_path, stderr_path, log_path, rc, project, step, skill, output, artifact_sha256, started, tid = sys.argv[1:]
try:
    raw = Path(stdout_path).read_text(encoding="utf-8")
except OSError:
    raw = ""
try:
    stderr = Path(stderr_path).read_text(encoding="utf-8")
except OSError:
    stderr = ""
try:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("gate JSON is not an object")
except Exception as exc:
    payload = {
        "gate": "FalsificationGate",
        "version": "unknown",
        "passed": False,
        "critical_failures": ["gate_runtime"],
        "results": [],
        "parse_error": str(exc),
        "raw_stdout": raw,
    }
payload.update({
    "project": payload.get("project", project),
    "tid": payload.get("tid", tid),
    "step": payload.get("step", step),
    "skill": payload.get("skill", skill),
    "output_file": payload.get("output_file", output),
    "artifact_sha256": payload.get("artifact_sha256", artifact_sha256),
    "execution_exit_code": int(rc),
    "started_at": started,
    "finished_at": datetime.now(timezone.utc).isoformat(),
})
if stderr:
    payload["stderr"] = stderr
if int(rc) != 0:
    payload["passed"] = False
Path(log_path).parent.mkdir(parents=True, exist_ok=True)
Path(log_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

    rm -f "$GATE_STDOUT" "$GATE_STDERR"
    GATE_PASSED=$(python3 - "$FALSIFICATION_LOG" <<'PY'
import json
import sys
try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        print("true" if json.load(handle).get("passed") is True else "false")
except Exception:
    print("false")
PY
)
    if [[ "$GATE_RC" -ne 0 || "$GATE_PASSED" != "true" ]]; then
        echo "❌ FALSIFICATION-GATE FAILED (exit $GATE_RC, passed=$GATE_PASSED) — TID bleibt offen"
        echo "   Vollständiger Befund: $FALSIFICATION_LOG"
        exit 1
    fi
    echo "  ✅ Falsification-Gate bestanden"
fi

# 3. Only now transition to DONE. The following self-improvement hook is
# explicitly simulation-only; completion.sh never invokes `ml train`.
if [[ "$RESULT" == "DONE" ]]; then
    tid_done "$TID" "$FALSIFICATION_LOG"

    LEARNINGS_DIR="${SHINON_LEARNINGS_DIR:-$REPO_ROOT/.learnings}"
    if [[ -d "$LEARNINGS_DIR" ]]; then
        PROJECT_NAME="$(basename "$REPO_ROOT")"
        SESSIONS_FILE="$LEARNINGS_DIR/${PROJECT_NAME}-sessions.jsonl"
        KARMA_PY="${SHINON_KARMA_PYTHON:-$REPO_ROOT/.venv/bin/python3}"
        [ -x "$KARMA_PY" ] || KARMA_PY=""
        if [[ -n "$KARMA_PY" ]]; then
            TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
            SKILL_OF_TID=$(task_field "$TID" "skill_name" 2>/dev/null || echo "")
            GOAL_OF_TID=$(task_field "$TID" "goal" 2>/dev/null || echo "")
            RAW=$("$KARMA_PY" -m karma.cli ml simulate \
                --project "$PROJECT_NAME" \
                --cycles 1 2>&1 || true)
            [ -z "$RAW" ] && RAW='{"simulated_actions": []}'
            RECORD=$(RAW="$RAW" python3 - "$TIMESTAMP" "$TID" "$RUN_ID" "$SKILL_OF_TID" "$GOAL_OF_TID" <<'PY'
import json
import os
import sys
print(json.dumps({
    "timestamp": sys.argv[1],
    "tid": sys.argv[2],
    "run_id": sys.argv[3],
    "skill": sys.argv[4],
    "goal": sys.argv[5],
    "result": "DONE",
    "simulate_output": os.environ.get("RAW", ""),
}, ensure_ascii=False))
PY
)
            printf '%s\n' "$RECORD" >> "$SESSIONS_FILE"
            echo "  ↻ self-improve snapshot → $SESSIONS_FILE ($(wc -l < "$SESSIONS_FILE") Zeilen gesamt)"
        fi
    fi
elif [[ "$RESULT" == "ROOT_CAUSE" ]]; then
    rc_reason="${4:-Gate verified: no gap to fill}"
    echo "❌ ROOT_CAUSE completion is not an execution authorization. Run the FalsificationGate first; no valid gate decision → execution impossible." >&2
    exit 1
elif [[ "$RESULT" == "FAIL" ]]; then
    FAIL_REASON="${4:-Agent reported failure}"
    tid_fail "$TID" "$FAIL_REASON"
fi

notify_dashboard "TID_${RESULT}" "$TID" "$PROGRESS_SNAPSHOT"

# Record completion/gate decisions for the audit trail.
if [[ -n "$GATE_RESULT" ]]; then
    record_decision "$TID" "GATE_RESULT" "$GATE_RESULT" "Gate ${TID_PHASE:-?} evaluated: ${GATE_RESULT}" "" ""
elif [[ "$AUTO_FLAG" != "--auto" ]]; then
    if [[ "$RESULT" == "FAIL" ]]; then
        record_decision "$TID" "COMPLETION" "${RESULT}" "FAIL: ${FAIL_REASON:-Agent reported failure}" "" ""
    else
        record_decision "$TID" "COMPLETION" "${RESULT}" "Agent completed TID" "" ""
    fi
fi

# Gate routing occurs after completion state is valid and before user checkpoint.
TID_PHASE=$(task_field "$TID" "phase")
if [[ "$TID_PHASE" == G* && -n "$GATE_RESULT" ]]; then
    _GATE_NEXT=$(next_pending_tid_after_gate "$RUN_ID" "$TID_PHASE" "$GATE_RESULT" "$OUTPUT_FILE" "$FALSIFICATION_LOG" "$TID")
    echo "  🔀 Gate-Routing: ${GATE_RESULT} → next=${_GATE_NEXT:-NONE}"
fi

if [[ "$REQUIRES_APPROVAL" == "1" ]]; then
    echo ""
    echo "🛑 USER APPROVAL REQUIRED — rufe user-checkpoint.sh"
    echo ""
    bash "$SCRIPT_DIR/user-checkpoint.sh" "$TID" "$AUTO_FLAG"
    exit 0
fi

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
