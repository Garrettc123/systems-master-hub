#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# Pixel 10 Edge Node — Qwen Endpoint Check
#
# Validates that the Qwen model is loaded and the Ollama inference endpoint
# responds correctly. Designed for integration into the watchdog or as a
# standalone readiness gate.
#
# Exit codes:
#   0 — endpoint healthy, model loaded, inference working
#   1 — endpoint unreachable or model not loaded
#   2 — endpoint reachable but inference failed
#
# Usage:  bash qwen-endpoint-check.sh
#         bash qwen-endpoint-check.sh --json   # machine-readable output
###############################################################################
set -uo pipefail

JSON_MODE=false
[ "${1:-}" = "--json" ] && JSON_MODE=true

# --- Colours ---
if [ -t 1 ] && [ "$JSON_MODE" = false ]; then
  R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' B='\033[0;34m' N='\033[0m'
else
  R='' G='' Y='' B='' N=''
fi

info()  { [ "$JSON_MODE" = false ] && printf "${B}[INFO]${N}  %s\n" "$*"; }
ok()    { [ "$JSON_MODE" = false ] && printf "${G}[OK]${N}    %s\n" "$*"; }
warn()  { [ "$JSON_MODE" = false ] && printf "${Y}[WARN]${N}  %s\n" "$*"; }

# --- Configuration ---
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
PRIMARY_MODEL="${QWEN_MODEL:-qwen2.5:0.5b-instruct}"
FALLBACK_MODEL="${QWEN_FALLBACK_MODEL:-qwen2.5:0.5b}"
INFERENCE_TIMEOUT="${QWEN_INFERENCE_TIMEOUT:-30}"

EDGE_HOME="${HOME}/edge-node"
STATUS_FILE="${EDGE_HOME}/data/qwen-endpoint-status.json"
mkdir -p "${EDGE_HOME}/data"

RESULT_MODEL=""
RESULT_STATUS="unknown"
RESULT_DETAIL=""
RESULT_LATENCY=""

write_status() {
  cat > "$STATUS_FILE" <<EOF
{
  "model": "${RESULT_MODEL}",
  "status": "${RESULT_STATUS}",
  "detail": "${RESULT_DETAIL}",
  "inference_latency_ms": ${RESULT_LATENCY:-null},
  "ollama_host": "${OLLAMA_HOST}",
  "checked_at": "$(date -Iseconds)"
}
EOF
  if [ "$JSON_MODE" = true ]; then
    cat "$STATUS_FILE"
  fi
}

###############################################################################
# 1. Check Ollama API
###############################################################################
info "Checking Ollama API at ${OLLAMA_HOST} ..."

if ! curl -sf --max-time 10 "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
  RESULT_STATUS="ollama_unreachable"
  RESULT_DETAIL="Ollama API not responding at ${OLLAMA_HOST}"
  write_status
  warn "Ollama is not reachable at ${OLLAMA_HOST}"
  exit 1
fi
ok "Ollama API reachable"

###############################################################################
# 2. Check if a Qwen model is loaded
###############################################################################
TAGS_JSON=$(curl -sf --max-time 10 "${OLLAMA_HOST}/api/tags" 2>/dev/null || echo '{}')

detect_model() {
  local model="$1"
  echo "$TAGS_JSON" | grep -q "\"${model}\""
}

if detect_model "$PRIMARY_MODEL"; then
  RESULT_MODEL="$PRIMARY_MODEL"
  ok "Found primary model: ${PRIMARY_MODEL}"
elif detect_model "$FALLBACK_MODEL"; then
  RESULT_MODEL="$FALLBACK_MODEL"
  ok "Found fallback model: ${FALLBACK_MODEL}"
else
  RESULT_STATUS="model_not_found"
  RESULT_DETAIL="Neither ${PRIMARY_MODEL} nor ${FALLBACK_MODEL} found in Ollama"
  write_status
  warn "No Qwen model found. Run qwen-model-pull.sh first."
  exit 1
fi

###############################################################################
# 3. Smoke-test inference
###############################################################################
info "Testing inference on ${RESULT_MODEL} (timeout: ${INFERENCE_TIMEOUT}s) ..."

START_MS=$(date +%s%3N 2>/dev/null || date +%s)
INFER_RESPONSE=$(curl -sf --max-time "$INFERENCE_TIMEOUT" \
  "${OLLAMA_HOST}/api/generate" \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"${RESULT_MODEL}\",\"prompt\":\"Say hello in one sentence.\",\"stream\":false}" \
  2>/dev/null || echo "")
END_MS=$(date +%s%3N 2>/dev/null || date +%s)

if [ -n "$INFER_RESPONSE" ]; then
  # Check for a non-empty response field
  RESPONSE_TEXT=$(echo "$INFER_RESPONSE" | grep -o '"response":"[^"]*"' | head -1 || echo "")
  if [ -n "$RESPONSE_TEXT" ]; then
    RESULT_LATENCY=$(( END_MS - START_MS ))
    RESULT_STATUS="healthy"
    RESULT_DETAIL="Inference OK"
    ok "Inference succeeded (${RESULT_LATENCY}ms)"
  else
    RESULT_STATUS="inference_empty"
    RESULT_DETAIL="Model responded but returned empty response"
    RESULT_LATENCY=$(( END_MS - START_MS ))
    write_status
    warn "Inference returned empty response"
    exit 2
  fi
else
  RESULT_STATUS="inference_failed"
  RESULT_DETAIL="Inference request timed out or failed"
  write_status
  warn "Inference request failed"
  exit 2
fi

###############################################################################
# 4. Write status and report
###############################################################################
write_status

echo ""
echo "Qwen endpoint is healthy."
echo "  Model:   ${RESULT_MODEL}"
echo "  Latency: ${RESULT_LATENCY}ms"
echo "  Host:    ${OLLAMA_HOST}"
