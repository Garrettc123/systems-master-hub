#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# Pixel 10 Source Gateway — Outbound Event Dispatcher
#
# Reads queued events from pending/ and pushes them to the cloud relay.
# Successful events move to sent/, failures move to failed/ for retry.
#
# Usage:  bash dispatch-outbound.sh                # send all pending
#         bash dispatch-outbound.sh --dry-run      # show what would be sent
#         bash dispatch-outbound.sh --retry         # re-queue failed events
#         bash dispatch-outbound.sh --max 10       # send at most 10 events
###############################################################################
set -uo pipefail

EDGE_HOME="${HOME}/edge-node"
GATEWAY_DIR="${EDGE_HOME}/gateway"
QUEUE_PENDING="${GATEWAY_DIR}/queue/pending"
QUEUE_SENT="${GATEWAY_DIR}/queue/sent"
QUEUE_FAILED="${GATEWAY_DIR}/queue/failed"
RELAY_CONFIG="${EDGE_HOME}/config/relay.env"

# Defaults
DRY_RUN=false
RETRY_MODE=false
MAX_EVENTS=0  # 0 = unlimited

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --retry)   RETRY_MODE=true; shift ;;
    --max)     MAX_EVENTS="$2"; shift 2 ;;
    *)         shift ;;
  esac
done

# Ensure directories exist
mkdir -p "$QUEUE_PENDING" "$QUEUE_SENT" "$QUEUE_FAILED"

###############################################################################
# Load relay configuration
###############################################################################
CLOUD_RELAY_URL=""
RELAY_HMAC_KEY=""

if [ -f "$RELAY_CONFIG" ]; then
  # shellcheck source=/dev/null
  source "$RELAY_CONFIG"
fi

# Allow environment override
CLOUD_RELAY_URL="${CLOUD_RELAY_URL:-${DISPATCH_RELAY_URL:-}}"
RELAY_HMAC_KEY="${RELAY_HMAC_KEY:-${DISPATCH_HMAC_KEY:-}}"

###############################################################################
# Re-queue failed events if --retry
###############################################################################
if [ "$RETRY_MODE" = true ]; then
  failed_count=$(ls -1 "$QUEUE_FAILED" 2>/dev/null | wc -l)
  if [ "$failed_count" -gt 0 ]; then
    echo "[RETRY] Moving $failed_count failed events back to pending..."
    for f in "$QUEUE_FAILED"/*.json; do
      [ -f "$f" ] || continue
      # Increment retry_count in metadata
      if command -v jq >/dev/null 2>&1; then
        jq '.metadata.retry_count = ((.metadata.retry_count // 0) + 1)' "$f" > "$f.tmp" \
          && mv "$f.tmp" "$f"
      fi
      mv "$f" "$QUEUE_PENDING/"
    done
    echo "[RETRY] Done."
  else
    echo "[RETRY] No failed events to retry."
  fi
fi

###############################################################################
# Dispatch pending events
###############################################################################
echo "=== Pixel 10 Source Gateway — Outbound Dispatch ==="
echo "    $(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date)"
echo ""

pending_files=$(ls -1t "$QUEUE_PENDING"/*.json 2>/dev/null || true)
pending_count=$(echo "$pending_files" | grep -c '\.json$' 2>/dev/null || echo 0)

if [ "$pending_count" -eq 0 ]; then
  echo "No pending events to dispatch."
  exit 0
fi

echo "Pending events: $pending_count"

if [ -z "$CLOUD_RELAY_URL" ] && [ "$DRY_RUN" = false ]; then
  echo ""
  echo "[WARN] CLOUD_RELAY_URL not configured."
  echo "       Set it in $RELAY_CONFIG or export DISPATCH_RELAY_URL."
  echo "       Running in dry-run mode instead."
  echo ""
  DRY_RUN=true
fi

sent=0
failed=0

for event_file in $pending_files; do
  [ -f "$event_file" ] || continue

  # Respect --max limit
  if [ "$MAX_EVENTS" -gt 0 ] && [ $((sent + failed)) -ge "$MAX_EVENTS" ]; then
    echo "[MAX] Reached limit of $MAX_EVENTS events."
    break
  fi

  filename=$(basename "$event_file")
  source_name=$(echo "$filename" | cut -d'_' -f1)
  event_id=$(jq -r '.event_id // "unknown"' "$event_file" 2>/dev/null || echo "unknown")

  if [ "$DRY_RUN" = true ]; then
    echo "[DRY] Would send: $filename (source=$source_name, id=$event_id)"
    continue
  fi

  # Compute HMAC signature if key is available
  sig_header=""
  if [ -n "$RELAY_HMAC_KEY" ]; then
    sig=$(echo -n "$(cat "$event_file")" | openssl dgst -sha256 -hmac "$RELAY_HMAC_KEY" -hex 2>/dev/null | awk '{print $NF}')
    sig_header="-H X-Gateway-Signature:sha256=${sig}"
  fi

  # POST to cloud relay
  http_code=$(curl -sf -o /dev/null -w "%{http_code}" \
    --max-time 15 \
    -X POST \
    -H "Content-Type: application/json" \
    -H "X-Node-Id: pixel10-edge" \
    -H "X-Source: ${source_name}" \
    $sig_header \
    -d @"$event_file" \
    "$CLOUD_RELAY_URL" 2>/dev/null || echo "000")

  if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
    mv "$event_file" "$QUEUE_SENT/"
    echo "[OK]   Sent: $filename (HTTP $http_code)"
    ((sent++))
  else
    mv "$event_file" "$QUEUE_FAILED/"
    echo "[FAIL] $filename (HTTP $http_code)"
    ((failed++))
  fi
done

echo ""
echo "Summary: sent=$sent  failed=$failed  remaining=$(ls -1 "$QUEUE_PENDING"/*.json 2>/dev/null | wc -l)"
