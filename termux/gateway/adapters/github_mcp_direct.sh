#!/usr/bin/env bash
###############################################################################
# Cloud Adapter: github_mcp_direct
#
# Polls GitHub API for recent events (PRs, issues, workflow runs) across
# configured repositories and delivers normalized envelopes to the edge node.
#
# Runs OFF-DEVICE (GitHub Actions or relay server).
#
# Required secrets:
#   GITHUB_PAT           — Personal access token with repo scope
#   PIXEL10_SSH_KEY_PATH — Path to SSH private key for edge delivery
#   PIXEL10_IP           — Edge node IP
#   PIXEL10_SSH_PORT     — Edge node SSH port (default: 8022)
#
# Optional:
#   GITHUB_REPOS         — Comma-separated list (default: Garrettc123/systems-master-hub)
#   GITHUB_SINCE_MINUTES — Look-back window (default: 20)
###############################################################################
set -euo pipefail

SOURCE_NAME="github_mcp_direct"
ADAPTER_VERSION="1.0.0"
EDGE_QUEUE_PATH="/data/data/com.termux/files/home/edge-node/gateway/queue/pending"

GITHUB_PAT="${GITHUB_PAT:?ERROR: GITHUB_PAT not set}"
REPOS="${GITHUB_REPOS:-Garrettc123/systems-master-hub}"
SINCE_MINUTES="${GITHUB_SINCE_MINUTES:-20}"

# --- Helpers (same as template) ---
generate_uuid() {
  python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null \
    || cat /proc/sys/kernel/random/uuid 2>/dev/null \
    || uuidgen
}

timestamp_iso() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

build_envelope() {
  local event_type="$1" data_json="$2"
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
  "payload": { "type": "${event_type}", "data": ${data_json} },
  "metadata": {
    "adapter_version": "${ADAPTER_VERSION}",
    "polling_mode": "scheduled",
    "ttl_seconds": 86400,
    "retry_count": 0
  }
}
ENVELOPE
}

deliver_to_edge() {
  local envelope="$1" filename="$2"
  local tmp="/tmp/${filename}"
  echo "$envelope" > "$tmp"
  scp -i "${PIXEL10_SSH_KEY_PATH:-~/.ssh/pixel10_edge}" \
      -P "${PIXEL10_SSH_PORT:-8022}" \
      -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 \
      "$tmp" "${PIXEL10_USER:-root}@${PIXEL10_IP}:${EDGE_QUEUE_PATH}/${filename}"
  rm -f "$tmp"
}

# --- Compute since timestamp ---
if date --version >/dev/null 2>&1; then
  SINCE=$(date -u -d "${SINCE_MINUTES} minutes ago" +"%Y-%m-%dT%H:%M:%SZ")
else
  SINCE=$(date -u -v-${SINCE_MINUTES}M +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || timestamp_iso)
fi

# --- Fetch and normalize ---
echo "=== Cloud Adapter: ${SOURCE_NAME} ==="
echo "    Repos: ${REPOS}"
echo "    Since: ${SINCE}"
echo ""

IFS=',' read -ra REPO_LIST <<< "$REPOS"
total_events=0

for repo in "${REPO_LIST[@]}"; do
  repo=$(echo "$repo" | xargs)  # trim whitespace

  # Recent PRs
  prs=$(curl -sf -H "Authorization: token ${GITHUB_PAT}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${repo}/pulls?state=all&sort=updated&direction=desc&per_page=10" \
    2>/dev/null || echo '[]')

  echo "$prs" | jq -c --arg since "$SINCE" '.[] | select(.updated_at >= $since)' 2>/dev/null \
  | while read -r pr; do
    pr_number=$(echo "$pr" | jq -r '.number')
    pr_state=$(echo "$pr" | jq -r '.state')
    merged=$(echo "$pr" | jq -r '.merged_at // empty')

    if [ -n "$merged" ]; then
      event_type="pr_merged"
    elif [ "$pr_state" = "open" ]; then
      event_type="pr_opened"
    else
      event_type="pr_closed"
    fi

    data=$(echo "$pr" | jq '{
      repo: .base.repo.full_name,
      pr_number: .number,
      title: .title,
      author: .user.login,
      state: .state,
      base_branch: .base.ref,
      updated_at: .updated_at
    }')

    envelope=$(build_envelope "$event_type" "$data")
    fname="${SOURCE_NAME}_$(timestamp_iso | tr ':.' '-')_$(generate_uuid | head -c 8).json"

    if [ -n "${PIXEL10_IP:-}" ]; then
      deliver_to_edge "$envelope" "$fname"
      echo "[OK] Delivered: ${repo}#${pr_number} (${event_type})"
    else
      echo "$envelope" | jq . 2>/dev/null || echo "$envelope"
      echo "[DRY] ${repo}#${pr_number} (${event_type}) — PIXEL10_IP not set"
    fi
    ((total_events++)) || true
  done

  # Recent workflow runs
  runs=$(curl -sf -H "Authorization: token ${GITHUB_PAT}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${repo}/actions/runs?per_page=5&created=%3E${SINCE}" \
    2>/dev/null || echo '{"workflow_runs":[]}')

  echo "$runs" | jq -c '.workflow_runs[]?' 2>/dev/null \
  | while read -r run; do
    data=$(echo "$run" | jq '{
      repo: .repository.full_name,
      workflow: .name,
      run_id: .id,
      status: .status,
      conclusion: .conclusion,
      branch: .head_branch,
      triggered_by: .triggering_actor.login
    }')

    envelope=$(build_envelope "workflow_run" "$data")
    fname="${SOURCE_NAME}_$(timestamp_iso | tr ':.' '-')_$(generate_uuid | head -c 8).json"

    if [ -n "${PIXEL10_IP:-}" ]; then
      deliver_to_edge "$envelope" "$fname"
      echo "[OK] Delivered: workflow run"
    else
      echo "[DRY] Workflow run — PIXEL10_IP not set"
    fi
    ((total_events++)) || true
  done
done

echo ""
echo "Done. Events processed: ${total_events}"
