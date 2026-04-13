#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# Pixel 10 Edge Node — Qwen Health Probe
#
# Lightweight, cron-friendly probe that checks:
#   1. Ollama process is alive
#   2. Qwen model is listed
#   3. Inference returns a non-empty response
#
# Designed to be called by the watchdog (every 15 min) or a dedicated cron
# entry. Writes a one-line JSON result suitable for telemetry aggregation.
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more checks failed
#
# Usage:
#   bash qwen-health-probe.sh             # human-readable
#   bash qwen-health-probe.sh --quiet     # exit-code only
#   bash qwen-health-probe.sh --json      # single-line JSON
###############################################################################
set -uo pipefail

MODE="human"
case "${1:-}" in
  --quiet) MODE="quiet" ;;
  --json)  MODE="json"  ;;
esac

# --- Configuration (inherit from environment or use defaults) ---
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
PRIMARY_MODEL="${QWEN_MODEL:-qwen2.5:0.5b-instruct}"
FALLBACK_MODEL="${QWEN_FALLBACK_MODEL:-qwen2.5:0.5b}"
PROBE_TIMEOUT="${QWEN_PROBE_TIMEOUT:-15}"

EDGE_HOME="${HOME}/edge-node"
PROBE_LOG="${EDGE_HOME}/logs/qwen-probe.log"
mkdir -p "${EDGE_HOME}/logs" "${EDGE_HOME}/data"

TIMESTAMP=$(date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S')
CHECKS_PASSED=0
CHECKS_TOTAL=3
DETECTED_MODEL=""
PROBE_LATENCY=""

log() {
  echo "[$TIMESTAMP] $*" >> "$PROBE_LOG"
  [ "$MODE" = "human" ] && echo "$*"
}

###############################################################################
# Check 1: Ollama process
###############################################################################
OLLAMA_ALIVE=false
if curl -sf --max-time 5 "${OLLAMA_HOST}/" >/dev/null 2>&1 || \
   curl -sf --max-time 5 "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
  OLLAMA_ALIVE=true
  CHECKS_PASSED=$((CHECKS_PASSED + 1))
  log "PASS  ollama_alive"
else
  log "FAIL  ollama_alive — ${OLLAMA_HOST} not responding"
fi

###############################################################################
# Check 2: Qwen model present
###############################################################################
MODEL_PRESENT=false
if [ "$OLLAMA_ALIVE" = true ]; then
  TAGS=$(curl -sf --max-time 5 "${OLLAMA_HOST}/api/tags" 2>/dev/null || echo '{}')
  if echo "$TAGS" | grep -q "\"${PRIMARY_MODEL}\""; then
    MODEL_PRESENT=true
    DETECTED_MODEL="$PRIMARY_MODEL"
  elif echo "$TAGS" | grep -q "\"${FALLBACK_MODEL}\""; then
    MODEL_PRESENT=true
    DETECTED_MODEL="$FALLBACK_MODEL"
  fi

  if [ "$MODEL_PRESENT" = true ]; then
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
    log "PASS  model_present (${DETECTED_MODEL})"
  else
    log "FAIL  model_present — neither ${PRIMARY_MODEL} nor ${FALLBACK_MODEL} found"
  fi
else
  log "SKIP  model_present — ollama not alive"
fi

###############################################################################
# Check 3: Inference responds
###############################################################################
INFERENCE_OK=false
if [ "$MODEL_PRESENT" = true ]; then
  START_MS=$(date +%s%3N 2>/dev/null || date +%s)
  RESP=$(curl -sf --max-time "$PROBE_TIMEOUT" \
    "${OLLAMA_HOST}/api/generate" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"${DETECTED_MODEL}\",\"prompt\":\"ping\",\"stream\":false}" \
    2>/dev/null || echo "")
  END_MS=$(date +%s%3N 2>/dev/null || date +%s)
  PROBE_LATENCY=$(( END_MS - START_MS ))

  if [ -n "$RESP" ] && echo "$RESP" | grep -q '"response"'; then
    INFERENCE_OK=true
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
    log "PASS  inference_ok (${PROBE_LATENCY}ms)"
  else
    log "FAIL  inference_ok — empty or invalid response"
  fi
else
  log "SKIP  inference_ok — model not present"
fi

###############################################################################
# Result
###############################################################################
HEALTHY=false
[ "$CHECKS_PASSED" -eq "$CHECKS_TOTAL" ] && HEALTHY=true

RESULT_JSON="{\"healthy\":${HEALTHY},\"checks_passed\":${CHECKS_PASSED},\"checks_total\":${CHECKS_TOTAL},\"model\":\"${DETECTED_MODEL}\",\"latency_ms\":${PROBE_LATENCY:-null},\"ollama_alive\":${OLLAMA_ALIVE},\"model_present\":${MODEL_PRESENT},\"inference_ok\":${INFERENCE_OK},\"timestamp\":\"${TIMESTAMP}\"}"

# Write latest probe result for telemetry
echo "$RESULT_JSON" > "${EDGE_HOME}/data/qwen-probe-latest.json"

case "$MODE" in
  json)  echo "$RESULT_JSON" ;;
  human)
    echo ""
    if [ "$HEALTHY" = true ]; then
      echo "Qwen health probe: ALL PASSED (${CHECKS_PASSED}/${CHECKS_TOTAL})"
    else
      echo "Qwen health probe: DEGRADED (${CHECKS_PASSED}/${CHECKS_TOTAL})"
    fi
    ;;
esac

[ "$HEALTHY" = true ] && exit 0 || exit 1
