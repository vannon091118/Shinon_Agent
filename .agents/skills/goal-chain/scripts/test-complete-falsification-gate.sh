#!/bin/bash
# Regression test for mandatory FalsificationGate enforcement in complete.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
SCHEMA="$REPO_ROOT/.agents/skills/goal-chain/db/schema.sql"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

DB="$TMP/tid-state.db"
ARTIFACT="$TMP/complete-gate-artifact.md"
FAKE_PY="$TMP/fake-python"
FAKE_LOG="$TMP/fake-gate.called"
LEARNINGS="$TMP/learnings"
printf '%s\n' 'test artifact' > "$ARTIFACT"
mkdir -p "$LEARNINGS"

ARTIFACT="$ARTIFACT" python3 - "$DB" "$SCHEMA" <<'PY'
import os
import sqlite3
import sys
from pathlib import Path

db, schema = sys.argv[1:]
conn = sqlite3.connect(db)
conn.executescript(Path(schema).read_text(encoding="utf-8"))
conn.execute(
    """INSERT INTO tasks
       (tid, projekt, run_id, task, goal, phase, phase_section, phase_seq,
        status, skill_name, script_path, output_artifact, template_id)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (
        "T-COMPLETE-GATE", "PZ", "RUN-COMPLETE-GATE", "test", "test",
        "P3", "finishing", 1, "PENDING", "test-skill", "test.sh",
        os.environ["ARTIFACT"], None,
    ),
)
conn.commit()
conn.close()
PY

cat > "$FAKE_PY" <<'PY'
#!/bin/sh
# This wrapper stands in for Python/KARMA and records every invocation.
printf '%s\n' "$*" >> "$FAKE_GATE_LOG"
case "$*" in
  *"-m karma.core.falsification_gate"*)
    case "${FAKE_GATE_RESULT:-pass}" in
      pass)
        printf '%s\n' '{"gate":"FalsificationGate","version":"test","passed":true,"results":[]}'
        exit 0
        ;;
      invalid)
        printf '%s\n' 'not-json'
        exit 0
        ;;
      *)
        printf '%s\n' '{"gate":"FalsificationGate","version":"test","passed":false,"critical_failures":["test_probe"],"results":[]}'
        exit 9
        ;;
    esac
    ;;
  *"-m karma.cli ml simulate"*)
    printf '%s\n' 'SIMULATE_ONLY_OK'
    exit 0
    ;;
  *"-m karma.cli ml train"*)
    printf '%s\n' 'TRAIN_MUST_NOT_BE_CALLED' >&2
    exit 99
    ;;
  *)
    printf '%s\n' "unexpected invocation: $*" >&2
    exit 98
    ;;
esac
PY
chmod +x "$FAKE_PY"

run_case() {
    local expected_status="$1"
    local expected_rc="$2"
    local result="${3:-pass}"
    local expected_gate_rc="${4:-0}"
    local actual_rc=0
    local log_file="$TMP/.goal/RUN-COMPLETE-GATE/falsification-gate-T-COMPLETE-GATE.json"
    rm -f "$FAKE_LOG" "$log_file" "$LEARNINGS/PZ-sessions.jsonl"

    python3 - "$DB" <<'PY'
import sqlite3
import sys
conn = sqlite3.connect(sys.argv[1])
conn.execute("UPDATE tasks SET status='PENDING', completed_at=NULL WHERE tid='T-COMPLETE-GATE'")
conn.commit()
PY

    FAKE_GATE_LOG="$FAKE_LOG" FAKE_GATE_RESULT="$result" \
        SHINON_GOALCHAIN_DB="$DB" \
        SHINON_KARMA_PYTHON="$FAKE_PY" \
        SHINON_GATE_LOG_DIR="$TMP/.goal/RUN-COMPLETE-GATE" \
        SHINON_LEARNINGS_DIR="$LEARNINGS" \
        FAKE_GATE_LOG="$FAKE_LOG" \
        bash "$SCRIPT_DIR/complete.sh" T-COMPLETE-GATE DONE --auto >"$TMP/complete.out" 2>&1 || actual_rc=$?

    [ "$actual_rc" -eq "$expected_rc" ] || {
        echo "FAIL: expected exit $expected_rc, got $actual_rc" >&2
        cat "$TMP/complete.out" >&2 || true
        return 1
    }

    local actual_status
    actual_status=$(python3 - "$DB" <<'PY'
import sqlite3
import sys
conn = sqlite3.connect(sys.argv[1])
print(conn.execute("SELECT status FROM tasks WHERE tid='T-COMPLETE-GATE'").fetchone()[0])
PY
)
    [ "$actual_status" = "$expected_status" ] || {
        echo "FAIL: expected status $expected_status, got $actual_status" >&2
        return 1
    }
    [ -s "$FAKE_LOG" ] || { echo "FAIL: gate runtime was not invoked" >&2; return 1; }

    python3 - "$log_file" "$result" "$expected_gate_rc" "$FAKE_LOG" "$LEARNINGS/PZ-sessions.jsonl" <<'PY'
import json
import sys
from pathlib import Path

payload = json.load(open(sys.argv[1], encoding="utf-8"))
result = sys.argv[2]
expected = result == "pass"
assert payload["passed"] is expected, payload
assert payload["execution_exit_code"] == int(sys.argv[3]), payload
if result == "invalid":
    assert "gate_runtime" in payload["critical_failures"], payload

invocations = Path(sys.argv[4]).read_text(encoding="utf-8").splitlines()
assert any("-m karma.core.falsification_gate" in line for line in invocations)
assert not any("-m karma.cli ml train" in line for line in invocations), invocations
if expected:
    assert any("-m karma.cli ml simulate" in line for line in invocations), invocations
    snapshot = Path(sys.argv[5])
    assert snapshot.exists(), "simulate snapshot was not written"
    record = json.loads(snapshot.read_text(encoding="utf-8").splitlines()[-1])
    assert record["result"] == "DONE", record
PY
}

run_case DONE 0 pass 0
run_case PENDING 1 fail 9
run_case PENDING 1 invalid 0

echo "✅ complete.sh FalsificationGate enforcement tests passed"
