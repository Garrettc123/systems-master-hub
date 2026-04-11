#!/usr/bin/env bash
# notify-notion-deploy.sh — Upsert a Pixel 10 deployment run into a Notion database.
#
# Called as the final (always-run) step of Pixel 10 deploy workflows.
# Creates a new page if no existing page matches the Run URL; otherwise updates it.
#
# Required environment variables:
#   NOTION_API_KEY          — Notion internal integration token (secret_…)
#   NOTION_DATABASE_ID      — Target database ID (no dashes; the script normalises)
#
# Optional environment variables (workflow context):
#   RUN_NAME                — Human-readable run name (default: workflow name + run number)
#   RUN_URL                 — Full Actions run URL
#   RUN_STATUS              — Overall workflow conclusion (success/failure/cancelled)
#   RUN_STARTED             — ISO 8601 start timestamp
#   STEP_SSH                — SSH step outcome (success/failure/skipped)
#   STEP_PREFLIGHT          — Pre-flight outcome
#   STEP_BOOTSTRAP          — Bootstrap outcome
#   STEP_WATCHDOG           — Watchdog / boot-persistence outcome
#   STEP_BOOT_PERSISTENCE   — Boot persistence outcome
#   STEP_OLLAMA             — Ollama outcome
#   STEP_RHNS               — RHNS integration outcome
#   STEP_HEALTH_CHECK       — Health-check outcome
#   NODE_IP                 — Device IP used in this run
#   DEPLOY_SUMMARY          — Free-text summary
#
set -euo pipefail

###############################################################################
# Validate
###############################################################################
if [ -z "${NOTION_API_KEY:-}" ]; then
  echo "::error::NOTION_API_KEY is not set — skipping Notion sync"
  exit 0          # Non-fatal: don't break the workflow if secret is missing
fi
if [ -z "${NOTION_DATABASE_ID:-}" ]; then
  echo "::error::NOTION_DATABASE_ID is not set — skipping Notion sync"
  exit 0
fi

# Normalise database ID to 32-char no-dash format accepted by the Notion API
DB_ID="${NOTION_DATABASE_ID//-/}"

###############################################################################
# Helpers
###############################################################################
notion_api() {
  local method="$1" endpoint="$2" body="${3:-}"
  local url="https://api.notion.com/v1${endpoint}"
  local args=(
    -sS --fail-with-body
    -X "$method"
    -H "Authorization: Bearer ${NOTION_API_KEY}"
    -H "Notion-Version: 2022-06-28"
    -H "Content-Type: application/json"
  )
  if [ -n "$body" ]; then
    args+=(-d "$body")
  fi
  curl "${args[@]}" "$url"
}

# Map a step outcome string to a Notion-friendly status emoji + label
step_status() {
  local val="${1:-skipped}"
  case "$val" in
    success)   echo "Pass" ;;
    failure)   echo "Fail" ;;
    cancelled) echo "Skipped" ;;
    skipped)   echo "Skipped" ;;
    *)         echo "Unknown" ;;
  esac
}

# Build a Notion select property JSON fragment
select_prop() {
  local name="$1" value="$2"
  printf '"%s": {"select": {"name": "%s"}}' "$name" "$value"
}

# Build a Notion rich_text property JSON fragment
text_prop() {
  local name="$1" value="$2"
  # Escape double-quotes and backslashes in value for JSON safety
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  printf '"%s": {"rich_text": [{"text": {"content": "%s"}}]}' "$name" "$value"
}

# Build a Notion url property JSON fragment
url_prop() {
  local name="$1" value="$2"
  printf '"%s": {"url": "%s"}' "$name" "$value"
}

# Build a Notion date property JSON fragment
date_prop() {
  local name="$1" value="$2"
  printf '"%s": {"date": {"start": "%s"}}' "$name" "$value"
}

# Build a Notion title property JSON fragment
title_prop() {
  local name="$1" value="$2"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  printf '"%s": {"title": [{"text": {"content": "%s"}}]}' "$name" "$value"
}

###############################################################################
# Resolve values with sane defaults
###############################################################################
RUN_NAME="${RUN_NAME:-Pixel 10 Deploy #${GITHUB_RUN_NUMBER:-0}}"
RUN_URL="${RUN_URL:-${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY:-unknown}/actions/runs/${GITHUB_RUN_ID:-0}}"
RUN_STATUS="${RUN_STATUS:-unknown}"
RUN_STARTED="${RUN_STARTED:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
NODE_IP="${NODE_IP:-unknown}"
DEPLOY_SUMMARY="${DEPLOY_SUMMARY:-Automated deploy run}"

###############################################################################
# Build properties JSON
###############################################################################
PROPERTIES="$(cat <<EOF
{
  $(title_prop "Run Name" "$RUN_NAME"),
  $(url_prop   "Run URL"  "$RUN_URL"),
  $(select_prop "Run Status" "$(step_status "$RUN_STATUS")"),
  $(date_prop  "Run Started" "$RUN_STARTED"),
  $(select_prop "SSH"              "$(step_status "${STEP_SSH:-skipped}")"),
  $(select_prop "Pre-flight"       "$(step_status "${STEP_PREFLIGHT:-skipped}")"),
  $(select_prop "Bootstrap"        "$(step_status "${STEP_BOOTSTRAP:-skipped}")"),
  $(select_prop "Watchdog"         "$(step_status "${STEP_WATCHDOG:-skipped}")"),
  $(select_prop "Boot Persistence" "$(step_status "${STEP_BOOT_PERSISTENCE:-skipped}")"),
  $(select_prop "Ollama"           "$(step_status "${STEP_OLLAMA:-skipped}")"),
  $(select_prop "RHNS Integration" "$(step_status "${STEP_RHNS:-skipped}")"),
  $(select_prop "Health Check"     "$(step_status "${STEP_HEALTH_CHECK:-skipped}")"),
  $(text_prop   "Node IP"  "$NODE_IP"),
  $(text_prop   "Summary"  "$DEPLOY_SUMMARY")
}
EOF
)"

###############################################################################
# Check for existing page by Run URL (upsert semantics)
###############################################################################
echo "Querying Notion for existing run record..."
QUERY_BODY="$(cat <<EOF
{
  "filter": {
    "property": "Run URL",
    "url": {
      "equals": "${RUN_URL}"
    }
  },
  "page_size": 1
}
EOF
)"

EXISTING="$(notion_api POST "/databases/${DB_ID}/query" "$QUERY_BODY" 2>&1)" || {
  echo "::warning::Notion query failed — will attempt to create a new page"
  EXISTING='{"results":[]}'
}

PAGE_ID="$(echo "$EXISTING" | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('results', [])
print(results[0]['id'] if results else '')
" 2>/dev/null || echo "")"

###############################################################################
# Create or update
###############################################################################
if [ -n "$PAGE_ID" ]; then
  echo "Updating existing Notion page ${PAGE_ID}..."
  UPDATE_BODY="{\"properties\": ${PROPERTIES}}"
  notion_api PATCH "/pages/${PAGE_ID}" "$UPDATE_BODY" > /dev/null
  echo "Notion page updated: ${PAGE_ID}"
else
  echo "Creating new Notion page in database ${DB_ID}..."
  CREATE_BODY="{\"parent\": {\"database_id\": \"${DB_ID}\"}, \"properties\": ${PROPERTIES}}"
  RESULT="$(notion_api POST "/pages" "$CREATE_BODY")"
  NEW_ID="$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "unknown")"
  echo "Notion page created: ${NEW_ID}"
fi

echo "Notion deployment sync complete."
