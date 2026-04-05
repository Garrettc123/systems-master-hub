#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# Pixel 10 Source Gateway — Local Telemetry Ingestion
#
# Collects on-device telemetry (battery, storage, network, Ollama, sensors)
# and writes normalized Source Event Envelopes to the local queue.
#
# Usage:  bash ingest-local.sh                 # all local sources
#         bash ingest-local.sh --source device_telemetry
#         bash ingest-local.sh --source ollama_status
#         bash ingest-local.sh --dry-run       # print to stdout, don't queue
###############################################################################
set -uo pipefail

EDGE_HOME="${HOME}/edge-node"
GATEWAY_DIR="${EDGE_HOME}/gateway"
QUEUE_DIR="${GATEWAY_DIR}/queue/pending"
REPORTS_DIR="${EDGE_HOME}/reports"
SOURCES_CONFIG="${EDGE_HOME}/config/sources.json"
NODE_ID="pixel10-edge"
SCHEMA_VERSION="1.0"

# Parse args
SOURCE_FILTER=""
DRY_RUN=false
while [ $# -gt 0 ]; do
  case "$1" in
    --source)  SOURCE_FILTER="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *)         shift ;;
  esac
done

# Ensure directories exist
mkdir -p "$QUEUE_DIR" "$REPORTS_DIR"

# --- Helpers ---
generate_uuid() {
  # Termux-compatible UUID v4 generation
  if command -v uuidgen >/dev/null 2>&1; then
    uuidgen
  elif [ -f /proc/sys/kernel/random/uuid ]; then
    cat /proc/sys/kernel/random/uuid
  else
    # Fallback: construct from /dev/urandom
    od -x /dev/urandom | head -1 | awk '{print $2$3"-"$4"-4"substr($5,2)"-"substr($6,1,1)"a"substr($6,2)"-"$7$8$9}' | head -c 36
  fi
}

timestamp_iso() {
  date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -Iseconds
}

write_event() {
  local source="$1"
  local category="$2"
  local event_type="$3"
  local data_json="$4"

  local event_id
  event_id=$(generate_uuid)
  local ts
  ts=$(timestamp_iso)

  local envelope
  envelope=$(cat <<ENVELOPE
{
  "schema_version": "${SCHEMA_VERSION}",
  "event_id": "${event_id}",
  "source": "${source}",
  "category": "${category}",
  "timestamp": "${ts}",
  "node_id": "${NODE_ID}",
  "payload": {
    "type": "${event_type}",
    "data": ${data_json}
  },
  "metadata": {
    "adapter_version": "1.0.0",
    "polling_mode": "local",
    "ttl_seconds": 86400
  }
}
ENVELOPE
)

  if [ "$DRY_RUN" = true ]; then
    echo "$envelope" | jq . 2>/dev/null || echo "$envelope"
  else
    local filename="${source}_${ts//[:.]/-}_${event_id:0:8}.json"
    echo "$envelope" > "${QUEUE_DIR}/${filename}"
    echo "[OK] Queued: ${filename}"
  fi
}

###############################################################################
# Collector: device_telemetry
###############################################################################
collect_device_telemetry() {
  local battery_pct="null"
  local battery_status="unknown"
  local free_kb=0
  local total_kb=0

  # Battery
  if command -v termux-battery-status >/dev/null 2>&1; then
    local batt
    batt=$(termux-battery-status 2>/dev/null || echo '{}')
    battery_pct=$(echo "$batt" | jq -r '.percentage // "null"' 2>/dev/null || echo "null")
    battery_status=$(echo "$batt" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
  fi

  # Disk
  free_kb=$(df /data 2>/dev/null | tail -1 | awk '{print $4}')
  total_kb=$(df /data 2>/dev/null | tail -1 | awk '{print $2}')
  local free_gb=$(( ${free_kb:-0} / 1048576 ))
  local total_gb=$(( ${total_kb:-0} / 1048576 ))

  # Network
  local ip
  ip=$(ip -4 route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\d+(\.\d+){3}' || echo "unknown")

  # Services
  local sshd_up=$(pgrep -x sshd >/dev/null 2>&1 && echo true || echo false)
  local crond_up=$(pgrep -x crond >/dev/null 2>&1 && echo true || echo false)

  # Uptime
  local uptime_str
  uptime_str=$(uptime 2>/dev/null | sed 's/^.*up //' | sed 's/,.*//' || echo "unknown")

  local data
  data=$(cat <<DATA
{
    "battery_pct": ${battery_pct},
    "battery_status": "${battery_status}",
    "disk_free_gb": ${free_gb},
    "disk_total_gb": ${total_gb},
    "ip": "${ip}",
    "uptime": "${uptime_str}",
    "services": {
      "sshd": ${sshd_up},
      "crond": ${crond_up}
    }
  }
DATA
)

  write_event "device_telemetry" "edge" "system_snapshot" "$data"
}

###############################################################################
# Collector: ollama_status
###############################################################################
collect_ollama_status() {
  local ollama_running=false
  local models="[]"
  local server_version="unknown"

  if command -v ollama >/dev/null 2>&1; then
    if curl -sf --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
      ollama_running=true
      local tags_response
      tags_response=$(curl -sf --max-time 3 http://127.0.0.1:11434/api/tags 2>/dev/null || echo '{}')
      models=$(echo "$tags_response" | jq '[.models[]?.name // empty]' 2>/dev/null || echo '[]')
      server_version=$(curl -sf --max-time 3 http://127.0.0.1:11434/api/version 2>/dev/null \
        | jq -r '.version // "unknown"' 2>/dev/null || echo "unknown")
    fi
  fi

  local data
  data=$(cat <<DATA
{
    "running": ${ollama_running},
    "server_version": "${server_version}",
    "models": ${models}
  }
DATA
)

  write_event "ollama_status" "edge" "llm_status" "$data"
}

###############################################################################
# Main
###############################################################################
echo "=== Pixel 10 Source Gateway — Local Ingestion ==="
echo "    $(timestamp_iso)"
echo ""

if [ -z "$SOURCE_FILTER" ] || [ "$SOURCE_FILTER" = "device_telemetry" ]; then
  collect_device_telemetry
fi

if [ -z "$SOURCE_FILTER" ] || [ "$SOURCE_FILTER" = "ollama_status" ]; then
  collect_ollama_status
fi

# Write a combined report for convenience
if [ "$DRY_RUN" = false ]; then
  REPORT_FILE="${REPORTS_DIR}/local-telemetry-$(date -u +%Y%m%d-%H%M%S).json"
  cat "${QUEUE_DIR}"/device_telemetry_*.json "${QUEUE_DIR}"/ollama_status_*.json 2>/dev/null \
    | jq -s '.' > "$REPORT_FILE" 2>/dev/null || true
  echo ""
  echo "Report written: $REPORT_FILE"
fi

echo ""
echo "Pending events: $(ls -1 "$QUEUE_DIR" 2>/dev/null | wc -l)"
