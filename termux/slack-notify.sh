#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# Pixel 10 Edge Node — Slack Notification Helper
#
# Sends messages to Slack via Incoming Webhook or Bot Token API.
# Default target: self-DM (the current logged-in user's conversation).
#
# Auth methods (checked in order):
#   1. SLACK_WEBHOOK_URL env var  — Incoming Webhook (simplest)
#   2. SLACK_BOT_TOKEN env var    — Bot Token + chat.postMessage API
#   3. File at SLACK_TOKEN_FILE   — reads token from file (secure storage)
#
# Configuration env vars:
#   SLACK_CHANNEL_ID   — Target channel/user ID (default: U0A6G6YLRDK self-DM)
#   SLACK_WEBHOOK_URL  — Incoming Webhook URL
#   SLACK_BOT_TOKEN    — xoxb-... Bot OAuth token
#   SLACK_TOKEN_FILE   — Path to file containing bot token
#   SLACK_DRY_RUN      — Set to "true" to print payload without sending
#
# Usage:
#   bash slack-notify.sh "message text"
#   bash slack-notify.sh --json '{"blocks":[...]}'
#   echo "piped message" | bash slack-notify.sh -
#   bash slack-notify.sh --status-report    # reads from status-report.sh
###############################################################################
set -uo pipefail

# --- Defaults ---
CHANNEL_ID="${SLACK_CHANNEL_ID:-U0A6G6YLRDK}"
DRY_RUN="${SLACK_DRY_RUN:-false}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

###############################################################################
# Parse arguments
###############################################################################
MODE="text"
MESSAGE=""

case "${1:-}" in
  --json)
    MODE="json"
    MESSAGE="${2:-}"
    ;;
  --status-report)
    MODE="status-report"
    ;;
  -)
    MESSAGE=$(cat)
    ;;
  "")
    echo "Usage: slack-notify.sh [--json JSON | --status-report | - | MESSAGE]" >&2
    exit 1
    ;;
  *)
    MESSAGE="$1"
    ;;
esac

###############################################################################
# Resolve auth
###############################################################################
AUTH_METHOD=""
AUTH_VALUE=""

if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
  AUTH_METHOD="webhook"
  AUTH_VALUE="$SLACK_WEBHOOK_URL"
elif [ -n "${SLACK_BOT_TOKEN:-}" ]; then
  AUTH_METHOD="bot_token"
  AUTH_VALUE="$SLACK_BOT_TOKEN"
elif [ -n "${SLACK_TOKEN_FILE:-}" ] && [ -f "${SLACK_TOKEN_FILE:-}" ]; then
  AUTH_METHOD="bot_token"
  AUTH_VALUE=$(cat "$SLACK_TOKEN_FILE" 2>/dev/null | tr -d '[:space:]')
fi

if [ -z "$AUTH_METHOD" ] && [ "$DRY_RUN" != "true" ]; then
  echo "ERROR: No Slack credentials found." >&2
  echo "Set one of: SLACK_WEBHOOK_URL, SLACK_BOT_TOKEN, or SLACK_TOKEN_FILE" >&2
  exit 2
fi

###############################################################################
# Build status report payload (Slack Block Kit)
###############################################################################
build_status_payload() {
  local report_json
  report_json=$(bash "$SCRIPT_DIR/status-report.sh" --json 2>/dev/null || echo '{}')

  local telemetry_json='{}'
  if [ -f "$SCRIPT_DIR/telemetry-collect.sh" ]; then
    telemetry_json=$(bash "$SCRIPT_DIR/telemetry-collect.sh" 2>/dev/null || echo '{}')
  fi

  local hostname battery_pct battery_status disk_free disk_total ip
  local sshd crond ollama uptime_str
  hostname=$(echo "$report_json" | jq -r '.hostname // "pixel10"')
  battery_pct=$(echo "$report_json" | jq -r '.battery_pct // "n/a"')
  battery_status=$(echo "$report_json" | jq -r '.battery_status // "n/a"')
  disk_free=$(echo "$report_json" | jq -r '.disk_free_gb // "?"')
  disk_total=$(echo "$report_json" | jq -r '.disk_total_gb // "?"')
  ip=$(echo "$report_json" | jq -r '.ip // "unknown"')
  sshd=$(echo "$report_json" | jq -r '.services.sshd // "?"')
  crond=$(echo "$report_json" | jq -r '.services.crond // "?"')
  ollama=$(echo "$report_json" | jq -r '.services.ollama // "?"')
  uptime_str=$(echo "$report_json" | jq -r '.uptime // "unknown"')

  # Telemetry extras
  local wifi_ssid wifi_rssi net_type
  wifi_ssid=$(echo "$telemetry_json" | jq -r '.wifi.ssid // "n/a"')
  wifi_rssi=$(echo "$telemetry_json" | jq -r '.wifi.rssi // "n/a"')
  net_type=$(echo "$telemetry_json" | jq -r '.telephony.network_type // "n/a"')

  # Service status emoji
  local sshd_icon crond_icon ollama_icon
  sshd_icon=$( [ "$sshd" = "running" ] && echo ":white_check_mark:" || echo ":x:" )
  crond_icon=$( [ "$crond" = "running" ] && echo ":white_check_mark:" || echo ":x:" )
  ollama_icon=$( [ "$ollama" = "running" ] && echo ":white_check_mark:" || echo ":x:" )

  # Battery icon
  local batt_icon=":battery:"
  if [ "$battery_pct" != "n/a" ] && [ "$battery_pct" -lt 20 ] 2>/dev/null; then
    batt_icon=":low_battery:"
  fi

  local ts
  ts=$(echo "$report_json" | jq -r '.timestamp // ""' | head -c 19)

  cat <<PAYLOAD
{
  "channel": "$CHANNEL_ID",
  "text": "Pixel 10 Edge Node Status — $hostname",
  "blocks": [
    {
      "type": "header",
      "text": {"type": "plain_text", "text": ":satellite: Pixel 10 Edge Node — $hostname"}
    },
    {
      "type": "section",
      "fields": [
        {"type": "mrkdwn", "text": "*IP:* \`$ip\`"},
        {"type": "mrkdwn", "text": "*Uptime:* $uptime_str"},
        {"type": "mrkdwn", "text": "*$batt_icon Battery:* ${battery_pct}% ($battery_status)"},
        {"type": "mrkdwn", "text": "*:floppy_disk: Disk:* ${disk_free}GB / ${disk_total}GB"}
      ]
    },
    {
      "type": "section",
      "fields": [
        {"type": "mrkdwn", "text": "*Services:*\n$sshd_icon sshd  $crond_icon crond  $ollama_icon ollama"},
        {"type": "mrkdwn", "text": "*:signal_strength: Network:*\nWiFi: $wifi_ssid (${wifi_rssi}dBm)\nCell: $net_type"}
      ]
    },
    {
      "type": "context",
      "elements": [
        {"type": "mrkdwn", "text": "RHNS self-report | $ts"}
      ]
    }
  ]
}
PAYLOAD
}

###############################################################################
# Build payload
###############################################################################
PAYLOAD=""

case "$MODE" in
  text)
    PAYLOAD=$(jq -nc --arg ch "$CHANNEL_ID" --arg txt "$MESSAGE" \
      '{channel: $ch, text: $txt}')
    ;;
  json)
    PAYLOAD="$MESSAGE"
    ;;
  status-report)
    PAYLOAD=$(build_status_payload)
    ;;
esac

###############################################################################
# Send
###############################################################################
if [ "$DRY_RUN" = "true" ]; then
  echo "[DRY RUN] Would send to Slack ($AUTH_METHOD -> $CHANNEL_ID):"
  echo "$PAYLOAD" | jq '.' 2>/dev/null || echo "$PAYLOAD"
  exit 0
fi

RESPONSE=""
HTTP_CODE=""

case "$AUTH_METHOD" in
  webhook)
    RESPONSE=$(curl -sf --max-time 10 \
      -X POST \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" \
      -w "\n%{http_code}" \
      "$AUTH_VALUE" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    ;;
  bot_token)
    RESPONSE=$(curl -sf --max-time 10 \
      -X POST \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $AUTH_VALUE" \
      -d "$PAYLOAD" \
      -w "\n%{http_code}" \
      "https://slack.com/api/chat.postMessage" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    ;;
esac

# Check result
if [ "${HTTP_CODE:-0}" -ge 200 ] && [ "${HTTP_CODE:-0}" -lt 300 ]; then
  echo "OK: Slack message sent ($AUTH_METHOD -> $CHANNEL_ID)"
  exit 0
else
  echo "ERROR: Slack send failed (HTTP $HTTP_CODE)" >&2
  echo "$RESPONSE" | head -5 >&2
  exit 1
fi
