#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# Pixel 10 Edge Node — Boot Init (Termux:Boot)
#
# Place this script (or a symlink) in ~/.termux/boot/ so it runs automatically
# when the device reboots and Termux:Boot is installed.
#
# Termux:Boot convention:
#   - Scripts in ~/.termux/boot/ execute on device boot
#   - They run with the Termux environment (PREFIX, PATH, etc.)
#   - Install Termux:Boot from F-Droid: https://f-droid.org/packages/com.termux.boot/
#
# What this script starts:
#   1. sshd (remote access)
#   2. crond (scheduled tasks)
#   3. Ollama serve (LLM inference, if installed)
#   4. Watchdog in background (periodic health checks)
###############################################################################
set -uo pipefail

LOG_DIR="${HOME}/edge-node/logs"
BOOT_LOG="${LOG_DIR}/boot-init.log"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$BOOT_LOG"; }

log "=== Boot init starting ==="

###############################################################################
# 1. Start sshd
###############################################################################
if ! pgrep -x sshd >/dev/null 2>&1; then
  sshd 2>>"$BOOT_LOG" && log "sshd started" || log "sshd FAILED to start"
else
  log "sshd already running"
fi

###############################################################################
# 2. Start crond (for scheduled watchdog / maintenance)
###############################################################################
if command -v crond >/dev/null 2>&1; then
  if ! pgrep -x crond >/dev/null 2>&1; then
    crond -b 2>>"$BOOT_LOG" && log "crond started" || log "crond FAILED"
  else
    log "crond already running"
  fi

  # Install watchdog cron if not already present
  CRON_ENTRY="*/15 * * * * bash ${HOME}/watchdog.sh >> ${LOG_DIR}/watchdog.log 2>&1"
  if ! crontab -l 2>/dev/null | grep -qF "watchdog.sh"; then
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab - 2>>"$BOOT_LOG"
    log "Watchdog cron installed (every 15 min)"
  fi
fi

###############################################################################
# 3. Start Ollama (if installed)
###############################################################################
if command -v ollama >/dev/null 2>&1; then
  if ! pgrep -f 'ollama serve' >/dev/null 2>&1; then
    nohup ollama serve >> "${LOG_DIR}/ollama.log" 2>&1 &
    sleep 2
    if pgrep -f 'ollama serve' >/dev/null 2>&1; then
      log "Ollama serve started (PID $(pgrep -f 'ollama serve' | head -1))"
    else
      log "Ollama serve FAILED to start"
    fi
  else
    log "Ollama serve already running"
  fi
fi

###############################################################################
# 4. Announce boot via Termux:API notification (if available)
###############################################################################
if command -v termux-notification >/dev/null 2>&1; then
  IP=$(ip -4 route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\d+(\.\d+){3}' || echo "unknown")
  termux-notification \
    --id edge-boot \
    --title "Edge Node Online" \
    --content "SSH: ${IP}:8022 | $(date '+%H:%M')" \
    2>>"$BOOT_LOG" || true
fi

log "=== Boot init complete ==="
