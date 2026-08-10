#!/usr/bin/env bash
###############################################################################
# Cloud Adapter Template
#
# Copy this file to create a new cloud-side source adapter.
# Each adapter runs OFF-DEVICE (GitHub Actions, VPS, or relay server) and:
#   1. Authenticates with the source API using secrets from the environment
#   2. Fetches new data since the last checkpoint
#   3. Normalizes the response into a Source Event Envelope
#   4. Delivers the envelope to the Pixel via SSH or stores it for sync
#
# Naming convention:  adapters/<source_name>.sh
#                     e.g. adapters/notion_mcp.sh
#
# Environment variables (set in GitHub Secrets or .env):
#   SOURCE_NAME          — must match the key in sources.json
#   PIXEL10_SSH_KEY      — private key for SSH delivery to edge node
#   PIXEL10_IP           — edge node IP address
#   PIXEL10_SSH_PORT     — SSH port (default: 8022)
#   <SOURCE>_API_KEY     — source-specific credential (varies per adapter)
#
# This template is NOT meant to run directly. It documents the contract.
###############################################################################
set -euo pipefail

# --- Configuration (override per adapter) ---
SOURCE_NAME="${SOURCE_NAME:-template}"
ADAPTER_VERSION="1.0.0"
EDGE_QUEUE_PATH="/data/data/com.termux/files/home/edge-node/gateway/queue/pending"

# --- Helpers ---
generate_uuid() {
  python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null \
    || cat /proc/sys/kernel/random/uuid 2>/dev/null \
    || uuidgen
}

timestamp_iso() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Build a Source Event Envelope
# Usage: build_envelope "event_type" '{"key": "value"}'
build_envelope() {
  local event_type="$1"
  local data_json="$2"
  local event_id
  event_id=$(generate_uuid)

  cat <<ENVELOPE
{
  "schema_version": "1.0",
  "event_id": "${event_id}",
  "source": "${SOURCE_NAME}",
  "category": "cloud",
  "timestamp": "$(timestamp_iso)",
  "node_id": "pixel10-edge",
  "payload": {
    "type": "${event_type}",
    "data": ${data_json}
  },
  "metadata": {
    "adapter_version": "${ADAPTER_VERSION}",
    "polling_mode": "scheduled",
    "ttl_seconds": 86400,
    "retry_count": 0
  }
}
ENVELOPE
}

# Deliver an envelope to the edge node via SSH/SCP
# Usage: deliver_to_edge "$envelope_json" "$filename"
deliver_to_edge() {
  local envelope="$1"
  local filename="$2"
  local tmp_file="/tmp/${filename}"

  echo "$envelope" > "$tmp_file"

  scp -i "${PIXEL10_SSH_KEY_PATH:-~/.ssh/pixel10_edge}" \
      -P "${PIXEL10_SSH_PORT:-8022}" \
      -o StrictHostKeyChecking=accept-new \
      -o ConnectTimeout=10 \
      "$tmp_file" \
      "${PIXEL10_USER:-root}@${PIXEL10_IP}:${EDGE_QUEUE_PATH}/${filename}"

  rm -f "$tmp_file"
}

###############################################################################
# ADAPTER IMPLEMENTATION (replace this section)
###############################################################################

fetch_and_normalize() {
  echo "[ERROR] This is a template. Copy and implement fetch_and_normalize()." >&2
  exit 1

  # Example implementation pattern:
  #
  # 1. Authenticate
  #    response=$(curl -sf -H "Authorization: Bearer ${MY_SOURCE_TOKEN}" \
  #               "https://api.example.com/v1/changes?since=${LAST_CHECKPOINT}")
  #
  # 2. Parse response into events
  #    echo "$response" | jq -c '.items[]' | while read -r item; do
  #      event_type=$(echo "$item" | jq -r '.type')
  #      data=$(echo "$item" | jq '{id: .id, title: .title, updated: .updated_at}')
  #      envelope=$(build_envelope "$event_type" "$data")
  #      filename="${SOURCE_NAME}_$(timestamp_iso | tr ':.' '-')_$(generate_uuid | head -c 8).json"
  #      deliver_to_edge "$envelope" "$filename"
  #    done
  #
  # 3. Update checkpoint
  #    echo "$(timestamp_iso)" > "/tmp/${SOURCE_NAME}_checkpoint"
}

# --- Main ---
echo "=== Cloud Adapter: ${SOURCE_NAME} ==="
echo "    $(timestamp_iso)"
fetch_and_normalize
