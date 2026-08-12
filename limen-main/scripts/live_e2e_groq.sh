#!/usr/bin/env bash
# Live E2E against the real Groq endpoint via LIMEN.
# Strict pre-flight then a single minimal completion call. Backups on every
# config write. Idempotent restore on exit.
#
# Usage:
#   scripts/live_e2e_groq.sh --check-only --port 18100
#   scripts/live_e2e_groq.sh --port 18100 --prompt "Reply with exactly: LIMEN live test passed."
#
# Key must come from:
#   1) --key value (off by default; explicit only when intentional)
#   2) env GROQ_API_KEY
#   3) interactive read -rs prompt (default fallback)
#
# This script never prints the key.
set -euo pipefail

LIMEN_REPO="${LIMEN_REPO:-$HOME/Schreibtisch/limen}"
DEFAULT_PORT=18100
DEFAULT_MODEL=llama-3.3-70b-versatile
GROQ_BASE_URL=https://api.groq.com/openai/v1
PROMPT_DEFAULT="Reply with exactly: LIMEN live test passed."
MAX_TOKENS_DEFAULT=4

CHECK_ONLY=0
PORT="$DEFAULT_PORT"
MODEL="$DEFAULT_MODEL"
PROMPT="$PROMPT_DEFAULT"
MAX_TOKENS="$MAX_TOKENS_DEFAULT"
KEEP_CONFIG=0
PASSED_KEY=""
RESPONSE_FILE=""
LIMEN_PID=""
BACKUP=""
BACKUP_RESTORE=0
KEYS=()
STREAM_FLAG=false

usage() {
  cat <<'USAGE'
scripts/live_e2e_groq.sh — LIMEN × real Groq end-to-end
  --check-only       Pre-flight only; do not start LIMEN or call the provider
  --port N            LIMEN listen port (default 18100)
  --model NAME        Model name (default llama-3.3-70b-versatile)
  --prompt TEXT       Single minimal prompt (default: "Reply with exactly: LIMEN live test passed.")
  --max-tokens N      Tokens to consume (default 4; cap at 8)
  --keep-config       Leave the modified ~/.config/limen/config.toml behind
  --repo PATH         Override the LIMEN repo path (default ~/Schreibtisch/limen)
  --key VALUE         Inline key (off by default; prefer env or prompt); repeatable for multi-key
  --stream            Use streaming chat completion (stream: true) instead of non-streaming
USAGE
}

while (($#)); do
  case "$1" in
    --check-only) CHECK_ONLY=1; shift;;
    --port) PORT="${2:?}"; shift 2;;
    --model) MODEL="${2:?}"; shift 2;;
    --prompt) PROMPT="${2:?}"; shift 2;;
    --max-tokens) MAX_TOKENS="${2:?}"; shift 2;;
    --keep-config) KEEP_CONFIG=1; shift;;
    --repo) LIMEN_REPO="${2:?}"; shift 2;;
    --key) PASSED_KEY="${2:?}"; KEYS+=("$PASSED_KEY"); shift 2;;
    --stream) STREAM_FLAG=true; shift;;
    -h|--help) usage; exit 0;;
    *) printf 'unknown argument: %s\n' "$1" >&2; usage; exit 1;;
  esac
done

# Allow max_tokens override but enforce a hard ceiling.
if ! [[ "$MAX_TOKENS" =~ ^[0-9]+$ ]] || [ "$MAX_TOKENS" -gt 8 ]; then
  printf 'max-tokens must be 0..8; got %s\n' "$MAX_TOKENS" >&2
  exit 1
fi

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
ok()  { log "✓ $*"; }
err() { log "✗ $*"; exit "${2:-1}"; }

KEY="$PASSED_KEY"
if [ -z "$KEY" ] && [ -n "${GROQ_API_KEY:-}" ]; then
  KEY="$GROQ_API_KEY"
fi
if [ -z "$KEY" ]; then
  if [ "$CHECK_ONLY" -eq 1 ]; then
    log "no GROQ_API_KEY + no --key; check-only continues"
  else
    printf 'Groq API key: ' >&2
    if ! read -rs KEY < /dev/tty 2>/dev/null; then
      KEY=""
    fi
    echo "" >&2
  fi
fi

if [ "$CHECK_ONLY" -eq 0 ] && [ -z "$KEY" ]; then
  err "groq api key required for full run"
fi

LIMEN_CFG="$HOME/.config/limen/config.toml"
LIMEN_CFG_DIR="$(dirname "$LIMEN_CFG")"
BACKUP=""
LIMEN_PID=""

cleanup() {
  set +e
  if [ -n "$LIMEN_PID" ] && kill -0 "$LIMEN_PID" 2>/dev/null; then
    kill "$LIMEN_PID" 2>/dev/null || true
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      kill -0 "$LIMEN_PID" 2>/dev/null || break
      sleep 0.2
    done
    kill -9 "$LIMEN_PID" 2>/dev/null || true
  fi
  if [ "$KEEP_CONFIG" -eq 0 ] && [ -n "${BACKUP_RESTORE:-}" ] && [ -n "$BACKUP" ] && [ -f "$BACKUP" ]; then
    cp -p "$BACKUP" "$LIMEN_CFG"
    chmod 600 "$LIMEN_CFG"
    ok "restored $LIMEN_CFG from $BACKUP"
  fi
  if [ -n "${RESPONSE_FILE:-}" ] && [ -f "$RESPONSE_FILE" ]; then
    chmod 600 "$RESPONSE_FILE"
  fi
  if [ -n "${RESPONSE_FILE:-}" ] && [ -d "$RESPONSE_FILE" ]; then
    rm -rf "$RESPONSE_FILE"
  fi
}
trap cleanup EXIT

# ────────────────────────────────────────────────────────────────────
# Pre-flight
# ────────────────────────────────────────────────────────────────────
log "===== preflight ====="
log "repo      : $LIMEN_REPO"
log "port      : $PORT"
log "model     : $MODEL"
log "max_tok   : $MAX_TOKENS"
log "stream    : $STREAM_FLAG"
log "key-pres  : $([ -n "$KEY" ] && echo yes || echo no)"
log "multi-key : ${#KEYS[@]} keys registered"

if [ -n "$KEY" ]; then
  case "$KEY" in
    gsk_*) ok "key shape (gsk_*)";;
    gsk-*) ok "key shape (gsk-)";;
    *) err "key does not start with gsk_/gsk-; refusing" 2;;
  esac
  KEY_LEN=${#KEY}
  log "key length: $KEY_LEN chars"
else
  log "key absent — only --check-only mode can proceed"
fi

if [ ! -d "$LIMEN_REPO/src/limen" ]; then
  err "LIMEN source not found at $LIMEN_REPO/src/limen"
fi
ok "limen repo located"

if command -v curl >/dev/null 2>&1; then
  ok "curl available"
else
  err "curl missing"
fi

if command -v jq >/dev/null 2>&1; then
  ok "jq available"
else
  err "jq missing"
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
  log "===== preflight summary ====="
  log "limen repo OK, port $PORT candidates."
  log "to run full E2E: scripts/live_e2e_groq.sh --port $PORT --prompt \"...\""
  exit 0
fi

if [ -z "$KEY" ]; then
  err "no key configured" 2
fi

# ── RESPONSE_FILE: temp directory so artefacts don't litter CWD ────
RESPONSE_FILE=$(mktemp -d -t limen-e2e.XXXXXX)
chmod 700 "$RESPONSE_FILE"
log "artefacts  : $RESPONSE_FILE"

# ── Port check: fail early if something already listens ───────────
if command -v ss >/dev/null 2>&1; then
  if ss -ltnH "sport = :$PORT" 2>/dev/null | grep -q "."; then
    err "port $PORT is already in use; free it or use --port" 9
  fi
  ok "port $PORT free (ss -ltn)"
else
  log "ss not found — skipping port check"
fi

# ────────────────────────────────────────────────────────────────────
# Provider reachability + model resolution
# ────────────────────────────────────────────────────────────────────
log "===== provider reachability ====="
PROBE_HEADERS=$(mktemp -t limen-probe-headers.XXXXXX)
trap 'rm -f "$PROBE_HEADERS"; cleanup' EXIT
PROBE_BODY=$(mktemp -t limen-probe-body.XXXXXX)
trap 'rm -f "$PROBE_BODY" "$PROBE_HEADERS"; cleanup' EXIT

status=$(curl -s -o "$PROBE_BODY" -D "$PROBE_HEADERS" -w '%{http_code}' \
  -H "Authorization: Bearer $KEY" \
  "$GROQ_BASE_URL/models" || echo "000")
if [ "$status" != "200" ]; then
  err "Groq /v1/models returned $status — check key or network (body: $(head -c 200 "$PROBE_BODY"))" 5
fi
ok "groq /v1/models reachable (200)"

if ! jq -e --arg m "$MODEL" '.data | map(.id) | index($m) != null' "$PROBE_BODY" >/dev/null; then
  available=$(jq -r '.data | map(.id) | join(", ")' "$PROBE_BODY" | head -c 240)
  err "model $MODEL not in Groq catalog; available (first): $available" 6
fi
ok "model $MODEL exists in groq catalog"

# ────────────────────────────────────────────────────────────────────
# Backup current config (if any)
# ────────────────────────────────────────────────────────────────────
TS=$(date +%Y%m%dT%H%M%S)
mkdir -p "$LIMEN_CFG_DIR"
chmod 700 "$LIMEN_CFG_DIR"
if [ -f "$LIMEN_CFG" ]; then
  BACKUP="$LIMEN_CFG.bak.$TS"
  cp -p "$LIMEN_CFG" "$BACKUP"
  chmod 600 "$BACKUP"
  ok "backed up to $BACKUP"
else
  BACKUP=""
  log "no previous $LIMEN_CFG — fresh config"
fi
BACKUP_RESTORE=1

# ────────────────────────────────────────────────────────────────────
# Render new config with only groq enabled.
# ────────────────────────────────────────────────────────────────────
# Multi-key support: join all keys as TOML array
JOINED_KEYS=""
for k in "${KEYS[@]}"; do
  if [ -z "$JOINED_KEYS" ]; then
    JOINED_KEYS="\"$k\""
  else
    JOINED_KEYS="$JOINED_KEYS, \"$k\""
  fi
done
if [ -z "$JOINED_KEYS" ] && [ -n "$KEY" ]; then
  JOINED_KEYS="\"$KEY\""
fi

cat > "$LIMEN_CFG" <<EOF
[server]
host = "127.0.0.1"
port = ${PORT}
worker_count = 1
log_level = "warning"
max_body_size_kb = 256

[database]
path = "$HOME/.limen/state.db"

[queue]
max_pending = 500
max_wait_seconds = 30

[providers.groq]
enabled = true
base_url = "${GROQ_BASE_URL}"
priority = 1
limit_scope = "unknown"
account_id = "groq-account-main"
keys = [${JOINED_KEYS}]
models = ["${MODEL}"]
capabilities = ["chat"]
soft_rpm = 28
EOF
chmod 600 "$LIMEN_CFG"
ok "wrote $LIMEN_CFG (0600, groq-only, ${#KEYS[@]} keys)"

# ────────────────────────────────────────────────────────────────────
# limen init + start
# ────────────────────────────────────────────────────────────────────
log "===== limen init ====="
(cd "$LIMEN_REPO" && PYTHONPATH=src uv run --quiet python -m limen.cli init --config "$LIMEN_CFG") >>"$RESPONSE_FILE.log" 2>&1 || {
  err "limen init failed; see $RESPONSE_FILE.log" 3
}
BACKUP_RESTORE=1   # restore on error too.
ok "limen init done"

log "===== limen start ====="
(cd "$LIMEN_REPO" && PYTHONPATH=src uv run --quiet python -m limen.cli start --config "$LIMEN_CFG") >"$RESPONSE_FILE.uv.log" 2>&1 &
LIMEN_PID=$!
log "limen pid: $LIMEN_PID"

ready=0
for i in $(seq 1 25); do
  status=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT}/health" 2>/dev/null || echo 000)
  if [ "$status" = "200" ]; then
    ready=$i
    break
  fi
  sleep 0.4
done
if [ "$ready" -eq 0 ]; then
  err "limen never came up; log: $RESPONSE_FILE.uv.log"
fi
ok "limen healthy after $ready polls"
ok "limen /health: $(curl -s "http://127.0.0.1:${PORT}/health")"

models_resp=$(curl -s "http://127.0.0.1:${PORT}/v1/models")
if ! echo "$models_resp" | jq -e --arg m "$MODEL" '.data | map(.id) | index($m) != null' >/dev/null; then
  err "LIMEN /v1/models does not advertise $MODEL"
fi
ok "limen /models advertises $MODEL"

# ── Audit verify: check events table recorded the call ─────────────
log "===== audit verify ====="
AUDIT_TOKEN=$(grep audit_token_secret "$LIMEN_CFG" 2>/dev/null | head -1 | sed 's/.*= *"//'| tr -d '"' || echo "")
if [ -n "$AUDIT_TOKEN" ] && [ "$AUDIT_TOKEN" != "REPLACE_ME_WITH_RANDOM_HEX" ]; then
  EVENTS_RESP=$(curl -s -H "X-Proxy-Audit-Key: $AUDIT_TOKEN" "http://127.0.0.1:${PORT}/v1/_internal/events?since=0" || echo "")
  if echo "$EVENTS_RESP" | grep -q 'task.completed'; then
    ok "audit: task.completed event found"
  else
    log "audit: no task.completed event yet (may be async)"
  fi
else
  log "audit: skipping — no usable audit_token_secret"
fi

# ────────────────────────────────────────────────────────────────────
# One real call
# ────────────────────────────────────────────────────────────────────
log "===== e2e call ====="
START_S=$(date +%s%N | awk '{print int($1/1000000)}')
RESP_HEADERS="$RESPONSE_FILE.headers"
RESP_BODY="$RESPONSE_FILE.json"
PAYLOAD=$(jq -nc --arg m "$MODEL" --arg p "$PROMPT" --argjson mx "$MAX_TOKENS" --argjson stream "$STREAM_FLAG" \
  '{model: $m, messages: [{role: "user", content: $p}], max_tokens: $mx, stream: $stream}')
status=$(curl -s -o "$RESP_BODY" -D "$RESP_HEADERS" -w '%{http_code}' \
  -H 'content-type: application/json' \
  --data "$PAYLOAD" \
  "http://127.0.0.1:${PORT}/v1/chat/completions")
END_S=$(date +%s%N | awk '{print int($1/1000000)}')
ELAPSED=$((END_S - START_S))

if [ "$status" = "200" ]; then
  ok "call status: HTTP $status in ${ELAPSED}ms"
  if [ "$STREAM_FLAG" = true ]; then
    ok "stream   : received SSE stream"
    ok "chunks   : $(grep -c '^data:' "$RESP_BODY" || echo 0) data lines"
    ok "first    : $(grep '^data:' "$RESP_BODY" | head -1 | cut -c7-80)"
  else
    ok "id       : $(jq -r .id "$RESP_BODY")"
    ok "model    : $(jq -r .model "$RESP_BODY")"
    ok "usage    : $(jq -c .usage "$RESP_BODY")"
    ok "content  : $(jq -r '.choices[0].message.content' "$RESP_BODY")"
    ok "stop     : $(jq -r '.choices[0].finish_reason' "$RESP_BODY")"
  fi
  if [ "$KEEP_CONFIG" -eq 0 ]; then
    BACKUP_RESTORE=1
  else
    BACKUP_RESTORE=0
  fi
elif [ "$status" = "401" ] || [ "$status" = "403" ]; then
  err "groq rejected key (HTTP $status); restore original config" 5
elif [ "$status" = "429" ]; then
  retry_after=$(grep -i '^retry-after:' "$RESP_HEADERS" | tr -d '\r' | awk '{print $2}')
  err "groq rate-limited (HTTP 429, retry-after=$retry_after); restore original config" 7
elif [ "$status" -ge 500 ]; then
  err "groq transport failure (HTTP $status); restore original config" 6
else
  err "unexpected HTTP $status from LIMEN; restore original config" 8
fi
