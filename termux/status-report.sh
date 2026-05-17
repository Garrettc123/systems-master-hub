#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# Pixel 10 Edge Node — Status Report
#
# Produces a human-readable and machine-parseable status snapshot.
# Output is plain text suitable for SSH capture by CI workflows.
#
# Usage:  bash status-report.sh            # text report to stdout
#         bash status-report.sh --json     # JSON to stdout
#         bash status-report.sh --slack    # Slack-formatted message to stdout
###############################################################################
set -uo pipefail

OUTPUT_MODE="text"
case "${1:-}" in
  --json)  OUTPUT_MODE="json" ;;
  --slack) OUTPUT_MODE="slack" ;;
esac

EDGE_HOME="${HOME}/edge-node"

# --- Gather data ---
NOW=$(date -Iseconds 2>/dev/null || date)
HOSTNAME=$(hostname 2>/dev/null || echo "pixel10")
USER=$(whoami)
ARCH=$(uname -m)
UPTIME=$(uptime 2>/dev/null | sed 's/^.*up /up /' || echo "unknown")

# IP
IP=$(ip -4 route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\d+(\.\d+){3}' || echo "unknown")

# Disk
FREE_KB=$(df /data 2>/dev/null | tail -1 | awk '{print $4}')
TOTAL_KB=$(df /data 2>/dev/null | tail -1 | awk '{print $2}')
FREE_GB=$(( ${FREE_KB:-0} / 1048576 ))
TOTAL_GB=$(( ${TOTAL_KB:-0} / 1048576 ))

# Services
SSHD_STATUS=$(pgrep -x sshd >/dev/null 2>&1 && echo "running" || echo "stopped")
CROND_STATUS="n/a"
if command -v crond >/dev/null 2>&1; then
  CROND_STATUS=$(pgrep -x crond >/dev/null 2>&1 && echo "running" || echo "stopped")
fi

OLLAMA_STATUS="not installed"
OLLAMA_MODELS=""
if command -v ollama >/dev/null 2>&1; then
  if curl -sf --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    OLLAMA_STATUS="running"
    OLLAMA_MODELS=$(curl -sf --max-time 3 http://127.0.0.1:11434/api/tags 2>/dev/null \
      | jq -r '.models[]?.name // empty' 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
  else
    OLLAMA_STATUS="installed but not responding"
  fi
fi

# Battery
BATTERY_PCT="n/a"
BATTERY_CHARGING="n/a"
if command -v termux-battery-status >/dev/null 2>&1; then
  BATT=$(termux-battery-status 2>/dev/null || echo '{}')
  BATTERY_PCT=$(echo "$BATT" | jq -r '.percentage // "n/a"' 2>/dev/null || echo "n/a")
  BATTERY_CHARGING=$(echo "$BATT" | jq -r '.status // "n/a"' 2>/dev/null || echo "n/a")
fi

# Telemetry (if collector available)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TELEMETRY_JSON='null'
if [ -f "$SCRIPT_DIR/telemetry-collect.sh" ]; then
  TELEMETRY_JSON=$(bash "$SCRIPT_DIR/telemetry-collect.sh" 2>/dev/null || echo 'null')
fi

# --- Output ---
case "$OUTPUT_MODE" in
  json)
    cat <<ENDJSON
{
  "timestamp": "$NOW",
  "hostname": "$HOSTNAME",
  "user": "$USER",
  "arch": "$ARCH",
  "ip": "$IP",
  "uptime": "$UPTIME",
  "disk_free_gb": $FREE_GB,
  "disk_total_gb": $TOTAL_GB,
  "battery_pct": "$BATTERY_PCT",
  "battery_status": "$BATTERY_CHARGING",
  "services": {
    "sshd": "$SSHD_STATUS",
    "crond": "$CROND_STATUS",
    "ollama": "$OLLAMA_STATUS"
  },
  "ollama_models": "$OLLAMA_MODELS",
  "telemetry": $TELEMETRY_JSON
}
ENDJSON
    ;;

  slack)
    # Slack mrkdwn formatted message template
    SSHD_ICON=$( [ "$SSHD_STATUS" = "running" ] && echo ":white_check_mark:" || echo ":x:" )
    CROND_ICON=$( [ "$CROND_STATUS" = "running" ] && echo ":white_check_mark:" || echo ":x:" )
    OLLAMA_ICON=$( [ "$OLLAMA_STATUS" = "running" ] && echo ":white_check_mark:" || echo ":x:" )

    BATT_ICON=":battery:"
    if [ "$BATTERY_PCT" != "n/a" ] && [ "$BATTERY_PCT" -lt 20 ] 2>/dev/null; then
      BATT_ICON=":low_battery:"
    fi

    # Extract WiFi info from telemetry if available
    WIFI_LINE=""
    if echo "$TELEMETRY_JSON" | jq -e '.wifi.ssid' >/dev/null 2>&1; then
      WIFI_SSID=$(echo "$TELEMETRY_JSON" | jq -r '.wifi.ssid // "n/a"')
      WIFI_RSSI=$(echo "$TELEMETRY_JSON" | jq -r '.wifi.rssi // "?"')
      WIFI_LINE="WiFi: ${WIFI_SSID} (${WIFI_RSSI}dBm)"
    fi
    NET_LINE=""
    if echo "$TELEMETRY_JSON" | jq -e '.telephony.network_type' >/dev/null 2>&1; then
      NET_TYPE=$(echo "$TELEMETRY_JSON" | jq -r '.telephony.network_type // "n/a"')
      NET_LINE="Cell: ${NET_TYPE}"
    fi

    cat <<ENDSLACK
:satellite: *Pixel 10 Edge Node — ${HOSTNAME}*
_${NOW}_

*System*
> IP: \`${IP}\` | Uptime: ${UPTIME}
> ${BATT_ICON} Battery: ${BATTERY_PCT}% (${BATTERY_CHARGING})
> :floppy_disk: Disk: ${FREE_GB}GB / ${TOTAL_GB}GB

*Services*
> ${SSHD_ICON} sshd  ${CROND_ICON} crond  ${OLLAMA_ICON} ollama
$([ -n "$OLLAMA_MODELS" ] && echo "> Models: ${OLLAMA_MODELS}")

*Network*
$([ -n "$WIFI_LINE" ] && echo "> ${WIFI_LINE}")
$([ -n "$NET_LINE" ] && echo "> ${NET_LINE}")

_RHNS self-report_
ENDSLACK
    ;;

  *)
    echo "===== Pixel 10 Edge Node Status ====="
    echo ""
    echo "  Timestamp:  $NOW"
    echo "  Host:       $HOSTNAME ($ARCH)"
    echo "  User:       $USER"
    echo "  IP:         $IP"
    echo "  Uptime:     $UPTIME"
    echo ""
    echo "--- Storage ---"
    echo "  Free:       ${FREE_GB}GB / ${TOTAL_GB}GB"
    echo ""
    echo "--- Battery ---"
    echo "  Level:      ${BATTERY_PCT}%"
    echo "  Status:     $BATTERY_CHARGING"
    echo ""
    echo "--- Services ---"
    echo "  sshd:       $SSHD_STATUS"
    echo "  crond:      $CROND_STATUS"
    echo "  ollama:     $OLLAMA_STATUS"
    [ -n "$OLLAMA_MODELS" ] && echo "  models:     $OLLAMA_MODELS"
    echo ""
    echo "--- Telemetry ---"
    if echo "$TELEMETRY_JSON" | jq -e '.wifi.ssid' >/dev/null 2>&1; then
      echo "  WiFi:       $(echo "$TELEMETRY_JSON" | jq -r '.wifi.ssid') ($(echo "$TELEMETRY_JSON" | jq -r '.wifi.rssi')dBm)"
    fi
    if echo "$TELEMETRY_JSON" | jq -e '.telephony.network_type' >/dev/null 2>&1; then
      echo "  Cell:       $(echo "$TELEMETRY_JSON" | jq -r '.telephony.network_type')"
    fi
    echo ""
    echo "====================================="
    ;;
esac
