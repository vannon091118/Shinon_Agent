#!/usr/bin/env bash
# Queue-Recovery-Test: verify recover_leases() picks up orphaned in_flight tasks.
#
# Flow:
#   1. Create isolated temp DB + config
#   2. limen init (schema creation)
#   3. Inject an in_flight queue entry with expired lease via sqlite3
#   4. Start LIMEN
#   5. Poll /v1/_internal/events for queue.recovery
#   6. Verify task was recovered (status != in_flight)
#   7. Cleanup
#
# No real provider keys needed — the dispatch will fail with
# NoAvailableDeployment, but the recovery itself is testable.
#
# Usage: scripts/recovery_test.sh
set -euo pipefail

LIMEN_REPO="${LIMEN_REPO:-$HOME/Schreibtisch/limen}"
TEST_PORT=19101
TMPDIR=$(mktemp -d -t limen-recovery.XXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
ok()  { log "✓ $*"; }
err() { log "✗ $*"; exit "${2:-1}"; }

# ── 1. Temp-DB + Config ───────────────────────────────────────────
DB_PATH="$TMPDIR/state.db"
CFG_PATH="$TMPDIR/config.toml"
AUDIT_TOKEN="recovery-test-token-$(date +%s)"

cat > "$CFG_PATH" <<EOF
[server]
host = "127.0.0.1"
port = ${TEST_PORT}
worker_count = 1
log_level = "warning"
max_body_size_kb = 256

[database]
path = "${DB_PATH}"

[audit]
audit_token_secret = "${AUDIT_TOKEN}"

[queue]
max_pending = 500
max_wait_seconds = 30
lease_seconds = 60
EOF
chmod 600 "$CFG_PATH"
ok "config written: $CFG_PATH"

# ── 2. limen init ──────────────────────────────────────────────────
(cd "$LIMEN_REPO" && PYTHONPATH=src uv run --quiet python -m limen.cli init --config "$CFG_PATH") 2>&1 || {
  err "limen init failed" 3
}
ok "limen init done ($DB_PATH)"

# ── 3. Inject orphaned in_flight task via Python ──────────────────
TASK_ID="recovery-test-$(date +%s)"

python3 -c "
import sqlite3
from datetime import datetime, timedelta, timezone
now = datetime.now(timezone.utc).isoformat()
expired = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
task_id = '${TASK_ID}'
db = sqlite3.connect('${DB_PATH}')
db.execute('''INSERT INTO queue(id, body_json, target_model, stream_flag, status,
  attempt_count, created_at, correlation_id, picked_up_at, lease_until)
  VALUES (?, ?, ?, 0, \"in_flight\", 1, ?, ?, ?, ?)''',
  (task_id, '{\"model\":\"test\",\"messages\":[{\"role\":\"user\",\"content\":\"recovery\"}]}',
   'test-model', now, 'corr-recovery-01', expired, expired))
db.commit()
count = db.execute('SELECT COUNT(*) FROM queue WHERE id=?', (task_id,)).fetchone()[0]
print('COUNT=' + str(count))
db.close()
"
ok "injected orphaned task $TASK_ID (lease 10 min expired)"

# ── 4. Start LIMEN ────────────────────────────────────────────────
log "===== starting LIMEN ====="
(cd "$LIMEN_REPO" && PYTHONPATH=src uv run --quiet python -m limen.cli start --config "$CFG_PATH") &
LIMEN_PID=$!
log "limen pid: $LIMEN_PID"

# Wait for healthy
ready=0
for i in $(seq 1 25); do
  status=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${TEST_PORT}/health" 2>/dev/null || echo 000)
  if [ "$status" = "200" ]; then
    ready=$i
    break
  fi
  sleep 0.4
done
if [ "$ready" -eq 0 ]; then
  kill "$LIMEN_PID" 2>/dev/null || true
  err "LIMEN never came up" 5
fi
ok "limen healthy after $ready polls"

# ── 5. Check recovery event directly in DB ──────────────────────
log "===== checking recovery ===="
sleep 3  # give worker time to recover + attempt dispatch
HAS_RECOVERY=$(python3 -c "
import sqlite3, json
db = sqlite3.connect('${DB_PATH}')
rows = db.execute('SELECT payload_json FROM events WHERE event_type=\"queue.recovery\"').fetchall()
if rows:
    payload = json.loads(rows[0][0])
    print('recovered_count=' + str(payload.get('recovered_count', 0)))
else:
    print('MISSING')
db.close()
")
if echo "$HAS_RECOVERY" | grep -q 'recovered_count='; then
  RECOVERED_COUNT=$(echo "$HAS_RECOVERY" | cut -d= -f2)
  ok "queue.recovery event found (recovered_count=$RECOVERED_COUNT)"
else
  err "queue.recovery event MISSING from events table" 5
fi

# ── 6. Verify task status changed ─────────────────────────────────
sleep 2  # give worker loop time to process
STATUS=$(python3 -c "
import sqlite3
db = sqlite3.connect('${DB_PATH}')
row = db.execute('SELECT status FROM queue WHERE id=?', ('${TASK_ID}',)).fetchone()
print(row[0] if row else 'MISSING')
db.close()
" 2>/dev/null || echo "MISSING")
log "task $TASK_ID status after recovery: $STATUS"

case "$STATUS" in
  pending|done|dead)
    ok "task recovered — status changed from in_flight to $STATUS"
    ;;
  in_flight)
    err "task NOT recovered — still in_flight" 6
    ;;
  MISSING)
    err "task vanished from queue" 7
    ;;
  *)
    ok "task status: $STATUS (unexpected but not in_flight)"
    ;;
esac

# Show queue depth
QDEPTH=$(python3 -c "
import sqlite3
db = sqlite3.connect('${DB_PATH}')
row = db.execute('SELECT COUNT(*) FROM queue WHERE status=\"pending\"').fetchone()
print(row[0] if row else 0)
db.close()
" 2>/dev/null || echo "?")
log "queue pending: $QDEPTH"

# ── 7. Cleanup ────────────────────────────────────────────────────
kill "$LIMEN_PID" 2>/dev/null || true
for _ in 1 2 3 4 5; do
  kill -0 "$LIMEN_PID" 2>/dev/null || break
  sleep 0.2
done
kill -9 "$LIMEN_PID" 2>/dev/null || true
ok "LIMEN stopped"
rm -rf "$TMPDIR"
log "===== recovery test PASSED ====="
