#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# Pixel 10 Edge Node — Qwen Model Pull
#
# Pulls the target Qwen model via Ollama. Tries the instruct variant first,
# falls back to the base variant if needed. Idempotent: skips the pull when
# the model is already present.
#
# Prerequisites: Ollama installed and `ollama serve` running.
#
# Usage:  bash qwen-model-pull.sh
#         QWEN_MODEL="qwen2.5:0.5b" bash qwen-model-pull.sh  # override
###############################################################################
set -uo pipefail

# --- Colours ---
if [ -t 1 ]; then
  R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' B='\033[0;34m' N='\033[0m'
else
  R='' G='' Y='' B='' N=''
fi

info()  { printf "${B}[INFO]${N}  %s\n" "$*"; }
ok()    { printf "${G}[OK]${N}    %s\n" "$*"; }
warn()  { printf "${Y}[WARN]${N}  %s\n" "$*"; }
fail()  { printf "${R}[FAIL]${N}  %s\n" "$*"; exit 1; }

# --- Configuration ---
PRIMARY_MODEL="${QWEN_MODEL:-qwen2.5:0.5b-instruct}"
FALLBACK_MODEL="${QWEN_FALLBACK_MODEL:-qwen2.5:0.5b}"
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
PULL_TIMEOUT="${QWEN_PULL_TIMEOUT:-900}"  # 15 min default

EDGE_HOME="${HOME}/edge-node"
STATUS_FILE="${EDGE_HOME}/data/qwen-model-status.json"
mkdir -p "${EDGE_HOME}/data"

###############################################################################
# 1. Pre-flight: verify Ollama is reachable
###############################################################################
info "Checking Ollama availability at ${OLLAMA_HOST} ..."

if ! curl -sf --max-time 10 "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
  fail "Ollama is not responding at ${OLLAMA_HOST}. Start it with: ollama serve"
fi
ok "Ollama is running"

###############################################################################
# 2. Check if model is already available
###############################################################################
model_present() {
  local model="$1"
  curl -sf --max-time 10 "${OLLAMA_HOST}/api/tags" 2>/dev/null \
    | grep -q "\"${model}\""
}

if model_present "$PRIMARY_MODEL"; then
  ok "Model ${PRIMARY_MODEL} is already pulled — nothing to do"
  cat > "$STATUS_FILE" <<EOF
{
  "model": "${PRIMARY_MODEL}",
  "status": "ready",
  "source": "cached",
  "checked_at": "$(date -Iseconds)"
}
EOF
  exit 0
fi

if model_present "$FALLBACK_MODEL"; then
  ok "Fallback model ${FALLBACK_MODEL} is already pulled — skipping"
  cat > "$STATUS_FILE" <<EOF
{
  "model": "${FALLBACK_MODEL}",
  "status": "ready",
  "source": "cached_fallback",
  "checked_at": "$(date -Iseconds)"
}
EOF
  exit 0
fi

###############################################################################
# 3. Check disk space (Qwen 0.5B needs ~400 MB)
###############################################################################
info "Checking disk space ..."
FREE_KB=$(df /data 2>/dev/null | tail -1 | awk '{print $4}')
FREE_MB=$(( ${FREE_KB:-0} / 1024 ))

if [ "$FREE_MB" -lt 600 ]; then
  fail "Not enough disk space: ${FREE_MB}MB free, need at least 600MB for Qwen 0.5B"
fi
ok "Disk space OK: ${FREE_MB}MB free"

###############################################################################
# 4. Pull primary model (with timeout)
###############################################################################
pull_model() {
  local model="$1"
  info "Pulling ${model} (timeout: ${PULL_TIMEOUT}s) ..."
  if timeout "$PULL_TIMEOUT" ollama pull "$model" 2>&1; then
    return 0
  else
    local rc=$?
    warn "Pull of ${model} failed (exit code ${rc})"
    return "$rc"
  fi
}

PULLED_MODEL=""

if pull_model "$PRIMARY_MODEL"; then
  ok "Successfully pulled ${PRIMARY_MODEL}"
  PULLED_MODEL="$PRIMARY_MODEL"
else
  warn "Primary model failed — trying fallback: ${FALLBACK_MODEL}"
  if pull_model "$FALLBACK_MODEL"; then
    ok "Successfully pulled fallback ${FALLBACK_MODEL}"
    PULLED_MODEL="$FALLBACK_MODEL"
  else
    cat > "$STATUS_FILE" <<EOF
{
  "model": "${PRIMARY_MODEL}",
  "fallback_model": "${FALLBACK_MODEL}",
  "status": "pull_failed",
  "error": "Both primary and fallback model pulls failed",
  "checked_at": "$(date -Iseconds)"
}
EOF
    fail "Both primary and fallback model pulls failed"
  fi
fi

###############################################################################
# 5. Verify the pulled model
###############################################################################
info "Verifying model is listed ..."
if model_present "$PULLED_MODEL"; then
  ok "Model ${PULLED_MODEL} verified in Ollama model list"
else
  warn "Model pulled but not found in list — Ollama may need a restart"
fi

###############################################################################
# 6. Write status
###############################################################################
cat > "$STATUS_FILE" <<EOF
{
  "model": "${PULLED_MODEL}",
  "status": "ready",
  "source": "fresh_pull",
  "primary_model": "${PRIMARY_MODEL}",
  "fallback_model": "${FALLBACK_MODEL}",
  "disk_free_mb": ${FREE_MB},
  "pulled_at": "$(date -Iseconds)"
}
EOF

ok "Model status written to ${STATUS_FILE}"
echo ""
echo "Model ${PULLED_MODEL} is ready for inference."
echo "Test with:  curl ${OLLAMA_HOST}/api/generate -d '{\"model\":\"${PULLED_MODEL}\",\"prompt\":\"Hello\",\"stream\":false}'"
