#!/usr/bin/env bash
# Phase 1 Reset-Gate Smoke (deterministisch, ohne echten Provider-Key).
#
# Zweck:  bestätigt, dass das `limen`-Binary den kanonischen Aufsatz aus
#         `docs/phase1-reset-gate.md` deterministisch erfüllt, bevor ein
#         echter Provider-Key oder Goose ins Spiel kommt.
# Output: exit 0 = alle Checks grün, 2xx = einzelne Assertion verletzt.
#
# Override:
#   LIMEN_PORT=19090 ./scripts/phase1_smoke.sh
set -euo pipefail

PORT="${LIMEN_PORT:-18180}"
HOST="127.0.0.1"
BASE="http://${HOST}:${PORT}"
TMP_DIR="$(mktemp -d -t limen-phase1-XXXXXX)"
LOG_DIR="${TMP_DIR}/logs"
CONFIG_PATH="${TMP_DIR}/config.toml"
DB_PATH="${TMP_DIR}/state.db"
SERVER_LOG="${LOG_DIR}/limen.log"
SERVER_PID=""
PY_BIN="${PYTHONPATH:-}"

PASS=0
FAIL=0

cleanup() {
  set +e
  if [[ -n "${SERVER_PID}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
    kill "${SERVER_PID}" 2>/dev/null || true
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
        break
      fi
      sleep 0.2
    done
    kill -9 "${SERVER_PID}" 2>/dev/null || true
  fi
  if [[ "${KEEP_TMP:-0}" -ne 1 ]]; then
    rm -rf "${TMP_DIR}"
  fi
}
trap cleanup EXIT

note() { printf '  • %s\n' "$*"; }
ok()   { printf '  ✓ %s\n' "$*"; PASS=$((PASS + 1)); }
bad()  { printf '  ✗ %s\n' "$*" >&2; FAIL=$((FAIL + 1)); }

require_tool() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'precondition failed: %s not installed\n' "$1" >&2
    exit 1
  fi
}

assert_eq() {
  local label="$1" expected="$2" got="$3"
  if [[ "${expected}" == "${got}" ]]; then
    ok "${label} == ${expected}"
  else
    bad "${label}: expected=${expected} got=${got}"
  fi
}

assert_contains() {
  local label="$1" needle="$2" hay="$3"
  if [[ "${hay}" == *"${needle}"* ]]; then
    ok "${label} contains ${needle}"
  else
    bad "${label}: '${hay}' does not contain '${needle}'"
  fi
}

assert_absent() {
  local label="$1" needle="$2" hay="$3"
  if [[ "${hay}" != *"${needle}"* ]]; then
    ok "${label} does not leak ${needle}"
  else
    bad "${label}: '${hay}' leaked '${needle}'"
  fi
}

printf '\n[1/4] Preconditions\n'
require_tool uv
require_tool curl
require_tool python
require_tool chmod

if [[ ! -f "$CONFIG_PATH" ]] || [[ ! -f "$DB_PATH" ]] || [[ ! -d "$LOG_DIR" ]]; then
  mkdir -p "${LOG_DIR}"
fi

printf '\n[2/4] Config & DB setup\n'
cat > "${CONFIG_PATH}" <<EOF
[server]
host = "${HOST}"
port = ${PORT}
worker_count = 1
log_level = "warning"
max_body_size_kb = 256

[database]
path = "${DB_PATH}"

[providers.bogus]
enabled = true
base_url = "https://provider.invalid/v1"
priority = 10
limit_scope = "unknown"
account_id = "phase1-smoke"
keys = ["smoke-test-key"]
models = ["phase1-reference-model"]
capabilities = ["chat"]
EOF
chmod 600 "${CONFIG_PATH}"

PYTHONPATH=src uv run python -m limen.cli init --config "${CONFIG_PATH}" > "${LOG_DIR}/init.log" 2>&1
assert_eq "limen init exit" "0" "$?"

declare -a SIDE=("${DB_PATH}" "${DB_PATH}-wal" "${DB_PATH}-shm")
for path in "${SIDE[@]}"; do
  if [[ -f "${path}" ]]; then
    mode="$(stat -c '%a' "${path}")"
    assert_eq "$(basename "${path}") mode" "600" "${mode}"
  fi
done

printf '\n[3/4] Start LIMEN (background)\n'
PYTHONPATH=src uv run python -m limen.cli start --config "${CONFIG_PATH}" > "${SERVER_LOG}" 2>&1 &
SERVER_PID=$!
note "limen pid=${SERVER_PID}, log=${SERVER_LOG}"

ready=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  code="$(curl -s -o "${TMP_DIR}/probe.json" -w '%{http_code}' "${BASE}/health" || true)"
  if [[ "${code}" == "200" ]]; then
    ready=1
    break
  fi
  sleep 0.5
done
if [[ "${ready}" -ne 1 ]]; then
  printf '\n--- server log ---\n' >&2
  cat "${SERVER_LOG}" >&2
  bad "limen never came up on ${BASE}/health"
  exit 2
fi
ok "limen listening on ${BASE}"

printf '\n[4/4] Endpoint assertions\n'

# /health
response="$(curl -sS -o "${TMP_DIR}/health.json" -w '%{http_code}' "${BASE}/health")"
assert_eq "GET /health" "200" "${response}"
body="$(cat "${TMP_DIR}/health.json")"
assert_contains "/health body" '"status":"ok"' "${body}"
assert_contains "/health body" '"db_writable":true' "${body}"

# /v1/models
response="$(curl -sS -o "${TMP_DIR}/models.json" -w '%{http_code}' "${BASE}/v1/models")"
assert_eq "GET /v1/models" "200" "${response}"
body="$(cat "${TMP_DIR}/models.json")"
assert_contains "/v1/models body" 'phase1-reference-model' "${body}"

# /v1/chat/completions: unknown model -> 400 unknown_model
response="$(curl -sS -o "${TMP_DIR}/unknown.json" -w '%{http_code}' \
  -H 'content-type: application/json' \
  -d '{"model":"made-up","messages":[{"role":"user","content":"x"}]}' \
  "${BASE}/v1/chat/completions")"
assert_eq "POST ? unknown model" "400" "${response}"
body="$(cat "${TMP_DIR}/unknown.json")"
assert_contains "unknown_model envelope" '"type":"unknown_model"' "${body}"

# /v1/chat/completions: stream=true -> 400 request_invalid
response="$(curl -sS -o "${TMP_DIR}/stream.json" -w '%{http_code}' \
  -H 'content-type: application/json' \
  -d '{"model":"phase1-reference-model","stream":true,"messages":[{"role":"user","content":"x"}]}' \
  "${BASE}/v1/chat/completions")"
assert_eq "POST ? stream=true" "400" "${response}"
body="$(cat "${TMP_DIR}/stream.json")"
assert_contains "request_invalid envelope" '"type":"request_invalid"' "${body}"

# /v1/chat/completions: valid model, unreachable provider -> 502 provider_unreachable
response="$(curl -sS -D "${TMP_DIR}/hdrs.txt" -o "${TMP_DIR}/upstream.json" -w '%{http_code}' \
  -H 'content-type: application/json' \
  -d '{"model":"phase1-reference-model","messages":[{"role":"user","content":"ping"}]}' \
  "${BASE}/v1/chat/completions")"
assert_eq "POST ? unreachable provider" "502" "${response}"
body="$(cat "${TMP_DIR}/upstream.json")"
assert_contains "provider_unreachable envelope" '"type":"provider_unreachable"' "${body}"
hdrs="$(cat "${TMP_DIR}/hdrs.txt")"
assert_absent "upstream headers" "X-Provider-Stuff" "${hdrs}"
assert_absent "upstream headers" "Set-Cookie" "${hdrs}"

# Oversized body (>256 KiB) -> 413 Request body too large
oversize_path="${TMP_DIR}/oversize.json"
python - <<PY > "${oversize_path}"
import json
content = "x" * 300_000
print(json.dumps({"model": "phase1-reference-model", "messages": [{"role": "user", "content": content}]}))
PY
response="$(curl -sS -o /dev/null -w '%{http_code}' \
  -H 'content-type: application/json' \
  --data-binary "@${oversize_path}" \
  "${BASE}/v1/chat/completions")"
assert_eq "POST ? oversize body" "413" "${response}"

# Invalid Content-Length -> 400 Invalid Content-Length
response="$(printf 'content-garbage' | curl -sS -o /dev/null -w '%{http_code}' \
  -H 'content-type: application/json' \
  -H 'content-length: not-a-number' \
  --data-binary @- \
  "${BASE}/v1/chat/completions")"
assert_eq "POST ? invalid content-length" "400" "${response}"

printf '\nSummary: %d passed, %d failed (port=%s, log=%s)\n' "${PASS}" "${FAIL}" "${PORT}" "${SERVER_LOG}"
if [[ "${FAIL}" -gt 0 ]]; then
  if [[ "${KEEP_TMP:-0}" -eq 1 ]]; then
    printf 'KEEP_TMP=1 is set; artefacts kept at %s\n' "${TMP_DIR}" >&2
  fi
  exit 2
fi
