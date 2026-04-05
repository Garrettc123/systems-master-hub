#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# Pixel 10 Edge Node — Watchdog / Health Check
#
# Checks critical services and restarts them if down.
# Designed to be run by cron (every 15 min) or manually.
#
# Usage:  bash watchdog.sh            # check + auto-heal
#         bash watchdog.sh --check    # check only, no restarts
###############################################################################
set -uo pipefail

CHECK_ONLY=false
[ "${1:-}" = "--check" ] && CHECK_ONLY=true

LOG_DIR="${HOME}/edge-node/logs"
mkdir -p "$LOG_DIR"

NOW=$(date '+%Y-%m-%d %H:%M:%S')
ISSUES=0

log() { echo "[$NOW] $*"; }

check_service() {
  local name="$1" check_cmd="$2" start_cmd="$3"

  if eval "$check_cmd" >/dev/null 2>&1; then
    log "OK   $name"
  else
    log "DOWN $name"
    ((ISSUES++))
    if [ "$CHECK_ONLY" = false ]; then
      log "     Restarting $name ..."
      if eval "$start_cmd" 2>/dev/null; then
        sleep 2
        if eval "$check_cmd" >/dev/null 2>&1; then
          log "     $name recovered"
        else
          log "     $name STILL DOWN after restart"
        fi
      else
        log "     $name restart command failed"
      fi
    fi
  fi
}

log "=== Watchdog check ==="

# --- sshd ---
check_service "sshd" \
  "pgrep -x sshd" \
  "sshd"

# --- crond ---
if command -v crond >/dev/null 2>&1; then
  check_service "crond" \
    "pgrep -x crond" \
    "crond -b"
fi

# --- Ollama ---
if command -v ollama >/dev/null 2>&1; then
  check_service "ollama" \
    "curl -sf --max-time 5 http://127.0.0.1:11434/api/tags" \
    "nohup ollama serve >> ${LOG_DIR}/ollama.log 2>&1 &"
fi

# --- Disk space warning ---
FREE_KB=$(df /data 2>/dev/null | tail -1 | awk '{print $4}')
FREE_GB=$(( ${FREE_KB:-0} / 1048576 ))
if [ "$FREE_GB" -lt 2 ]; then
  log "WARN Disk space critically low: ${FREE_GB}GB free"
  ((ISSUES++))
  # Notify via Termux:API if available
  if command -v termux-notification >/dev/null 2>&1; then
    termux-notification --id edge-disk \
      --title "Edge Node: Low Disk" \
      --content "Only ${FREE_GB}GB free on /data" 2>/dev/null || true
  fi
else
  log "OK   Disk: ${FREE_GB}GB free"
fi

# --- Battery check (Termux:API) ---
if command -v termux-battery-status >/dev/null 2>&1; then
  BATTERY_JSON=$(termux-battery-status 2>/dev/null || echo '{}')
  BATTERY_PCT=$(echo "$BATTERY_JSON" | jq -r '.percentage // "unknown"' 2>/dev/null || echo "unknown")
  BATTERY_STATUS=$(echo "$BATTERY_JSON" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")

  if [ "$BATTERY_PCT" != "unknown" ] && [ "$BATTERY_PCT" -lt 15 ] 2>/dev/null; then
    log "WARN Battery low: ${BATTERY_PCT}% (${BATTERY_STATUS})"
    ((ISSUES++))
  else
    log "OK   Battery: ${BATTERY_PCT}% (${BATTERY_STATUS})"
  fi
fi

# --- Summary ---
if [ "$ISSUES" -eq 0 ]; then
  log "=== All checks passed ==="
else
  log "=== ${ISSUES} issue(s) detected ==="
fi

exit "$ISSUES"
