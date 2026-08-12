#!/usr/bin/env bash
# Multi-provider live E2E against real Groq + OpenRouter + NVIDIA NIM via LIMEN.
#
# Required env vars (or --key NAME=VALUE for overrides):
#   GROQ_API_KEY       gsk_* — Groq free-tier key
#   OPENROUTER_API_KEY sk-or-v1-* — OpenRouter key
#   NVIDIA_NIM_API_KEY nvapi-* — NVIDIA NIM key
#
# Strategy: edit the existing ~/.config/limen/config.toml to remove non-target
# providers, back it up, run the cycle through all three providers with the
# same LIMEN process, then restore. Each provider gets its own reachability
# probe and one minimal chat call. Failure in one provider does not abort
# the others — the script collects a summary.
#
# Usage:
#   scripts/live_multi_e2e.sh --port 18200
#   scripts/live_multi_e2e.sh --check-only
#   scripts/live_multi_e2e.sh --provider groq --provider openrouter
#   scripts/live_multi_e2e.sh --stream
#   scripts/live_multi_e2e.sh --max-tokens 8
#   scripts/live_multi_e2e.sh --key openrouter=sk-or-v1-xxxxx
set -euo pipefail

LIMEN_REPO="${LIMEN_REPO:-$HOME/Schreibtisch/limen}"
DEFAULT_PORT=18200
DEFAULT_PROMPT="Reply with exactly: LIMEN multi-provider live test passed."
DEFAULT_MAX_TOKENS=4

CHECK_ONLY=0
PORT="$DEFAULT_PORT"
PROMPT="$DEFAULT_PROMPT"
MAX_TOKENS="$DEFAULT_MAX_TOKENS"
STREAM_FLAG=false
KEEP_CONFIG=0
PROMPT_TOKENS=0
declare -a SELECTED_PROVIDERS=()
declare -A PASSED_KEYS=()

usage() {
  cat <<'USAGE'
scripts/live_multi_e2e.sh — LIMEN × 3 providers end-to-end
  --check-only       Pre-flight only; do not start LIMEN or call any provider
  --port N            LIMEN listen port (default 18200)
  --provider NAME     Restrict to one provider: groq|openrouter|nvidia (repeatable)
  --prompt TEXT       Single minimal prompt (default "Reply with exactly: LIMEN...")
  --max-tokens N      Tokens to consume (default 4; cap at 8)
  --stream            Use streaming chat completion (stream: true) per provider
  --keep-config       Leave the modified ~/.config/limen/config.toml behind
  --repo PATH         Override the LIMEN repo path (default ~/Schreibtisch/limen)
  --key NAME=VALUE    Override key for a single provider (NAME: groq|openrouter|nvidia)
USAGE
}

while (($#)); do
  case "$1" in
    --check-only) CHECK_ONLY=1; shift;;
    --port) PORT="${2:?}"; shift 2;;
    --provider) SELECTED_PROVIDERS+=("${2:?}"); shift 2;;
    --prompt) PROMPT="${2:?}"; shift 2;;
    --max-tokens) MAX_TOKENS="${2:?}"; shift 2;;
    --stream) STREAM_FLAG=true; shift;;
    --keep-config) KEEP_CONFIG=1; shift;;
    --repo) LIMEN_REPO="${2:?}"; shift 2;;
    --key)
      kv="${2:?}"
      name="${kv%%=*}"; value="${kv#*=}"
      PASSED_KEYS["$name"]="$value"
      shift 2
      ;;
    -h|--help) usage; exit 0;;
    *) printf 'unknown argument: %s\n' "$1" >&2; usage; exit 1;;
  esac
done

# Hard ceiling on token consumption — live tests must stay cheap.
if ! [[ "$MAX_TOKENS" =~ ^[0-9]+$ ]] || [ "$MAX_TOKENS" -gt 8 ]; then
  printf 'max-tokens must be 0..8; got %s\n' "$MAX_TOKENS" >&2
  exit 1
fi

# ── Provider registry: name -> env-var + base_url + default model + key prefix ──
declare -A PROV_ENV=(
  [groq]="GROQ_API_KEY"
  [openrouter]="OPENROUTER_API_KEY"
  [nvidia]="NVIDIA_NIM_API_KEY"
)
declare -A PROV_BASE=(
  [groq]="https://api.groq.com/openai/v1"
  [openrouter]="https://openrouter.ai/api/v1"
  [nvidia]="https://integrate.api.nvidia.com/v1"
)
declare -A PROV_MODEL=(
  [groq]="llama-3.3-70b-versatile"
  [openrouter]="google/gemma-4-26b-a4b-it:free"
  [nvidia]="nvidia/nemotron-3-ultra-550b-a55b"
)
declare -A PROV_PREFIX=(
  [groq]="gsk_"
  [openrouter]="sk-or-v1-"
  [nvidia]="nvapi-"
)

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
ok()  { log "✓ $*"; }
bad() { log "✗ $*"; }
err() { log "✗ $*"; exit "${2:-1}"; }

# ── Resolve key for a provider, three sources in order: --key, env, key-store ──
KEY_STORE_PATH="${KEY_STORE_PATH:-$HOME/.limen/keys.json}"
declare -A KEY_STORE_CACHE=()

load_key_store() {
  if [ -s "$KEY_STORE_PATH" ] && [ "${#KEY_STORE_CACHE[@]}" -eq 0 ]; then
    while IFS=$'\t' read -r k v; do
      [ -n "$k" ] && KEY_STORE_CACHE["$k"]="$v"
    done < <(jq -r 'to_entries[] | "\(.key)\t\(.value)"' "$KEY_STORE_PATH" 2>/dev/null || true)
  fi
}

key_for() {
  local name="$1"
  if [ -n "${PASSED_KEYS[$name]:-}" ]; then
    printf '%s' "${PASSED_KEYS[$name]}"
    return
  fi
  local envname="${PROV_ENV[$name]}"
  local from_env="${!envname:-}"
  if [ -n "$from_env" ]; then
    printf '%s' "$from_env"
    return
  fi
  load_key_store
  if [ -n "${KEY_STORE_CACHE[$name]:-}" ]; then
    printf '%s' "${KEY_STORE_CACHE[$name]}"
    return
  fi
  # Map common aliases from the store.
  case "$name" in
    nvidia) printf '%s' "${KEY_STORE_CACHE[nvidia_nim]:-}";;
  esac
}

# ── Filter selected_providers or default to all three ──
declare -a RUN_ORDER=()
if [ "${#SELECTED_PROVIDERS[@]}" -eq 0 ]; then
  RUN_ORDER=(groq openrouter nvidia)
else
  for p in "${SELECTED_PROVIDERS[@]}"; do
    if [ -z "${PROV_BASE[$p]:-}" ]; then
      err "unknown provider: $p (allowed: groq, openrouter, nvidia)" 2
    fi
    RUN_ORDER+=("$p")
  done
fi

# ── Pre-flight (always runs) ──
log "===== preflight ====="
log "repo      : $LIMEN_REPO"
log "port      : $PORT"
log "providers : ${RUN_ORDER[*]}"
log "max_tok   : $MAX_TOKENS"
log "stream    : $STREAM_FLAG"

if [ ! -d "$LIMEN_REPO/src/limen" ]; then
  err "LIMEN source not found at $LIMEN_REPO/src/limen"
fi
ok "limen repo located"

for tool in uv curl jq python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    err "$tool missing"
  fi
done
ok "tools: uv, curl, jq, python3"

# Probe-only mode: report per-provider key status and exit 0
if [ "$CHECK_ONLY" -eq 1 ]; then
  log "===== key status ====="
  if [ -s "$KEY_STORE_PATH" ]; then
    ok "key store present at $KEY_STORE_PATH"
  else
    log "key store: $KEY_STORE_PATH not present"
  fi
  for p in "${RUN_ORDER[@]}"; do
    k="$(key_for "$p")"
    if [ -n "$k" ]; then
      ok "$p: key present (len=${#k}, prefix=${PROV_PREFIX[$p]})"
    else
      log "$p: no key (set ${PROV_ENV[$p]}/--key $p=.../keys.json entry)"
    fi
  done
  log "===== check-only summary ====="
  log "ok to run as: scripts/live_multi_e2e.sh --port $PORT"
  exit 0
fi

LIMEN_CFG="$HOME/.config/limen/config.toml"
LIMEN_CFG_DIR="$(dirname "$LIMEN_CFG")"
ART_DIR=$(mktemp -d -t limen-multi-e2e.XXXXXX)
chmod 700 "$ART_DIR"
LIMEN_PID=""
BACKUP=""
BACKUP_RESTORE=0

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
  if [ "$KEEP_CONFIG" -eq 0 ] && [ "$BACKUP_RESTORE" -eq 1 ] && [ -n "$BACKUP" ] && [ -f "$BACKUP" ]; then
    cp -p "$BACKUP" "$LIMEN_CFG"
    chmod 600 "$LIMEN_CFG"
    ok "restored $LIMEN_CFG from $BACKUP"
  fi
}
trap cleanup EXIT

# ── Port check ──
if command -v ss >/dev/null 2>&1; then
  if ss -ltnH "sport = :$PORT" 2>/dev/null | grep -q "."; then
    err "port $PORT is already in use; free it or use --port" 9
  fi
  ok "port $PORT free (ss -ltn)"
fi

# ── Per-provider preflight: shape, env, key length (no echo) ──
log "===== key check ====="
declare -a PROVIDERS_WITH_KEYS=()
for p in "${RUN_ORDER[@]}"; do
  k="$(key_for "$p")"
  if [ -z "$k" ]; then
    bad "$p: no key (skipping)"
    continue
  fi
  prefix="${PROV_PREFIX[$p]}"
  case "$k" in
    "${prefix}"*) ok "$p: key shape ok (${prefix}*, len=${#k})";;
    *) bad "$p: key does not start with $prefix; skipping"; continue;;
  esac
  PROVIDERS_WITH_KEYS+=("$p")
done

if [ "${#PROVIDERS_WITH_KEYS[@]}" -eq 0 ]; then
  err "no provider has a usable key; abort"
fi

# ── Backup + render per-provider section in config.toml ──
TS=$(date +%Y%m%dT%H%M%S)
mkdir -p "$LIMEN_CFG_DIR"
chmod 700 "$LIMEN_CFG_DIR"
if [ -f "$LIMEN_CFG" ]; then
  BACKUP="$LIMEN_CFG.bak.multi.$TS"
  cp -p "$LIMEN_CFG" "$BACKUP"
  chmod 600 "$BACKUP"
  ok "backed up to $BACKUP"
  BACKUP_RESTORE=1
else
  log "no previous $LIMEN_CFG — fresh create"
fi

# Build a JSON document describing the providers we have keys for, then hand it
# to python3 — heredoc-and-quoting in bash is fragile, here-doc got bitten once.
providers_json_tmp="$ART_DIR/providers.json"
{
  printf '['
  first=1
  for p in "${PROVIDERS_WITH_KEYS[@]}"; do
    k="$(key_for "$p")"
    if [ "$first" -eq 1 ]; then first=0; else printf ','; fi
    jq -nc \
      --arg name "$p" \
      --arg base "${PROV_BASE[$p]}" \
      --arg model "${PROV_MODEL[$p]}" \
      --arg key "$k" \
      '{name:$name, base_url:$base, model:$model, key:$key, priority: 1, account_id: ($name + "-multi-e2e")}'
  done
  printf ']'
} > "$providers_json_tmp"

python3 - "$LIMEN_CFG" "$providers_json_tmp" "$PORT" <<'PY'
import json, re, sys, pathlib
cfg_path = pathlib.Path(sys.argv[1])
providers_path = pathlib.Path(sys.argv[2])
port = int(sys.argv[3])
text = cfg_path.read_text()
providers = json.loads(providers_path.read_text())

# 1) Force [server] port + bind to loopback so the user's existing config
#    cannot win with port=8000 + bind=0.0.0.0.
text = re.sub(
    r"(?ms)^\[server\]\n(?:.*\n)*?(?=^\[)",
    "[server]\nhost = \"127.0.0.1\"\n"
    f"port = {port}\n"
    "worker_count = 1\n"
    "log_level = \"warning\"\n"
    "max_body_size_kb = 256\n\n",
    text,
    count=1,
)

# 2) Drop existing [providers.*] sections (in case we re-run).
text = re.sub(r"(?ms)^\[providers\..*?(?=^\[(?!providers\.)|\Z)", "", text)

new_block_parts = []
for p in providers:
    block = (
        f"\n[providers.{p['name']}]\n"
        f"enabled = true\n"
        f"base_url = \"{p['base_url']}\"\n"
        f"priority = {p['priority']}\n"
        f"limit_scope = \"key\"\n"
        f"account_id = \"{p['account_id']}\"\n"
        f"keys = [\"{p['key']}\"]\n"
        f"models = [\"{p['model']}\"]\n"
        f"capabilities = [\"chat\"]\n"
    )
    new_block_parts.append(block)
new_block = "".join(new_block_parts)

anchor = text.find("[audit]")
if anchor >= 0:
    text = text[:anchor] + new_block + "\n" + text[anchor:]
else:
    text = text.rstrip() + "\n" + new_block + "\n"
cfg_path.write_text(text)
PY
chmod 600 "$LIMEN_CFG"
ok "wrote $LIMEN_CFG (0600) with ${#PROVIDERS_WITH_KEYS[@]} provider sections (server.port=$PORT)"

# ── limen init + start ──
log "===== limen init ====="
(cd "$LIMEN_REPO" && PYTHONPATH=src uv run --quiet python -m limen.cli init --config "$LIMEN_CFG") \
  >"$ART_DIR/init.log" 2>&1 || err "limen init failed; see $ART_DIR/init.log"
ok "limen init done"

log "===== limen start ====="
(cd "$LIMEN_REPO" && PYTHONPATH=src uv run --quiet python -m limen.cli start --config "$LIMEN_CFG") \
  >"$ART_DIR/limen.log" 2>&1 &
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
  err "limen never came up; log: $ART_DIR/limen.log"
fi
ok "limen healthy after $ready polls"

LIMEN_MODELS=$(curl -s "http://127.0.0.1:${PORT}/v1/models")
ok "limen /v1/models: $(echo "$LIMEN_MODELS" | jq -c '.data | map(.id)')"

# ── Per-provider loop: probe + e2e call ──
declare -a SUMMARY=()  # lines of "provider=ok|fail|skip|reason"
run_provider() {
  local p="$1"
  local k="$(key_for "$p")"
  local base="${PROV_BASE[$p]}"
  local model="${PROV_MODEL[$p]}"
  local reason=""

  log "===== $p ====="

  # 1) Upstream reachability probe (live connectivity, NOT LIMEN)
  local probe_body="$ART_DIR/$p.probe.json"
  local probe_status
  probe_status=$(curl -s -o "$probe_body" -w '%{http_code}' \
    -H "Authorization: Bearer $k" \
    "$base/models" || echo 000)
  if [ "$probe_status" != "200" ]; then
    reason="upstream /v1/models = $probe_status"
    bad "  $p probe: $reason"
    SUMMARY+=("$p=skip:$reason")
    return
  fi
  ok "  $p probe: $probe_status"

  # 2) Model exists upstream
  if ! jq -e --arg m "$model" '.data | map(.id) | index($m) != null' "$probe_body" >/dev/null; then
    first_models=$(jq -r '.data | map(.id) | join(", ")' "$probe_body" | head -c 120)
    reason="model $model not in $p catalog (sample: $first_models)"
    bad "  $p: $reason"
    SUMMARY+=("$p=skip:$reason")
    return
  fi
  ok "  $p: model $model found in catalog"

  # 3) LIMEN advertises it
  if ! echo "$LIMEN_MODELS" | jq -e --arg m "$model" '.data | map(.id) | index($m) != null' >/dev/null; then
    reason="LIMEN /v1/models does not list $model"
    bad "  $p: $reason"
    SUMMARY+=("$p=fail:$reason")
    return
  fi
  ok "  $p: LIMEN advertises $model"

  # 4) Real call via LIMEN
  local body="$ART_DIR/$p.response.json"
  local headers="$ART_DIR/$p.headers"
  local payload
  payload=$(jq -nc --arg m "$model" --arg p "$PROMPT" \
    --argjson mx "$MAX_TOKENS" --argjson stream "$STREAM_FLAG" \
    '{model: $m, messages: [{role: "user", content: $p}], max_tokens: $mx, stream: $stream}')
  local t0 t1 ms
  t0=$(date +%s%N | awk '{print int($1/1000000)}')
  local call_status
  call_status=$(curl -s -o "$body" -D "$headers" -w '%{http_code}' \
    -H 'content-type: application/json' \
    --data "$payload" \
    "http://127.0.0.1:${PORT}/v1/chat/completions")
  t1=$(date +%s%N | awk '{print int($1/1000000)}')
  ms=$((t1 - t0))

  if [ "$call_status" = "200" ]; then
    ok "  $p call: HTTP 200 in ${ms}ms"
    if [ "$STREAM_FLAG" = true ]; then
      local chunks
      chunks=$(grep -c '^data:' "$body" 2>/dev/null || echo 0)
      ok "  $p stream: $chunks SSE chunks"
      local first
      first=$(grep '^data:' "$body" | head -1 | cut -c1-100)
      ok "  $p first chunk: $first"
    else
      local reply_model reply_usage reply_stop reply_content has_xreq
      reply_model=$(jq -r '.model // empty' "$body")
      reply_usage=$(jq -c '.usage // empty' "$body")
      reply_stop=$(jq -r '.choices[0].finish_reason // empty' "$body")
      reply_content=$(jq -r '.choices[0].message.content // empty' "$body" | head -c 80)
      has_xreq=$(grep -i '^x-request-id:' "$headers" | tr -d '\r' | awk '{print $2}' || echo "")
      ok "  $p model=$reply_model"
      ok "  $p usage=$reply_usage"
      ok "  $p stop=$reply_stop"
      ok "  $p content: $reply_content"
      ok "  $p X-Request-Id: ${has_xreq:-<none>}"
    fi
    SUMMARY+=("$p=ok:${ms}ms")
  else
    # Try to pull a useful reason out of the JSON envelope.
    local err_type
    err_type=$(jq -r '.error.type // .error.message // "unknown"' "$body" 2>/dev/null || echo "unknown")
    reason="call HTTP $call_status ($err_type)"
    bad "  $p: $reason"
    SUMMARY+=("$p=fail:$reason")
  fi
}

for p in "${PROVIDERS_WITH_KEYS[@]}"; do
  run_provider "$p"
done

# ── Summary ──
log "===== summary ====="
declare -A counts=([ok]=0 [fail]=0 [skip]=0)
for line in "${SUMMARY[@]}"; do
  name="${line%%=*}"; rest="${line#*=}"
  status="${rest%%:*}"
  case "$status" in
    ok) counts[ok]=$((counts[ok] + 1));;
    fail) counts[fail]=$((counts[fail] + 1));;
    skip) counts[skip]=$((counts[skip] + 1));;
  esac
  printf '  %-12s %s\n' "$name" "$line"
done
log "totals: ok=${counts[ok]} fail=${counts[fail]} skip=${counts[skip]}"

if [ "${counts[fail]}" -gt 0 ]; then
  exit 4
fi
