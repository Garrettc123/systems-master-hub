#!/usr/bin/env bash
# AutoKey bulk sync helper.
# Discovers repositories in an owner account and propagates all VAL_* secrets.
# Usage:
#   GITHUB_OWNER=Garrettc123 GH_TOKEN=... bash .github/scripts/autokey-sync-all.sh
#   TARGET_REPO=garcar-payments DRY_RUN=true bash .github/scripts/autokey-sync-all.sh

set -euo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
PUSH_SCRIPT="$SCRIPT_DIR/autokey-push.sh"

if [ ! -x "$PUSH_SCRIPT" ]; then
  echo "ERROR: Missing executable helper: $PUSH_SCRIPT"
  exit 1
fi

if [ -z "${GH_TOKEN:-}" ]; then
  echo "ERROR: GH_TOKEN not set. Add GHPAT or PAT_TOKEN to systems-master-hub secrets."
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI not found."
  exit 1
fi

GITHUB_OWNER="${GITHUB_OWNER:-Garrettc123}"
TARGET_REPO="${TARGET_REPO:-}"
INCLUDE_ARCHIVED="${INCLUDE_ARCHIVED:-false}"
INCLUDE_FORKS="${INCLUDE_FORKS:-false}"
TARGET_SCOPE="${TARGET_SCOPE:-owner}"
TARGET_TIER="${TARGET_TIER:-all}"
REGISTRY_FILE="${REGISTRY_FILE:-registry/repos.json}"

list_repos() {
  gh repo list "$GITHUB_OWNER" \
    --limit 1000 \
    --json name,isArchived,isFork \
    --jq '.[] | .name + "\t" + (.isArchived|tostring) + "\t" + (.isFork|tostring)'
}

list_registry_repos() {
  local repo_root
  repo_root="$(dirname "$SCRIPT_DIR")/.."
  local registry_path="$repo_root/$REGISTRY_FILE"

  if [ ! -f "$registry_path" ]; then
    echo "ERROR: Registry file not found: $registry_path"
    exit 1
  fi
  if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: jq not found. Required for registry-based sync."
    exit 1
  fi

  case "$TARGET_TIER" in
    all)
      jq -r '
        [
          (.tier1.repos // {}),
          (.tier2.repos // {}),
          (.tier3.repos // {})
        ]
        | map(to_entries[])
        | flatten
        | .[].key
      ' "$registry_path"
      ;;
    tier1|tier2|tier3)
      jq -r --arg tier "$TARGET_TIER" '
        .[$tier].repos // {} | keys[]
      ' "$registry_path"
      ;;
    *)
      echo "ERROR: TARGET_TIER must be one of: all, tier1, tier2, tier3"
      exit 1
      ;;
  esac
}

echo "========================================"
echo " AutoKey Sweep Owner: $GITHUB_OWNER"
echo "========================================"
echo " Scope: $TARGET_SCOPE | Tier: $TARGET_TIER"

SUCCESS=0
FAILED=0

if [ -n "$TARGET_REPO" ]; then
  REPOS="$TARGET_REPO"
else
  case "$TARGET_SCOPE" in
    registry)
      REPOS="$(list_registry_repos | sort -u)"
      ;;
    owner)
      REPOS="$(list_repos | while IFS=$'\t' read -r repo archived fork; do
        if [ "$INCLUDE_ARCHIVED" != "true" ] && [ "$archived" = "true" ]; then
          continue
        fi
        if [ "$INCLUDE_FORKS" != "true" ] && [ "$fork" = "true" ]; then
          continue
        fi
        printf '%s\n' "$repo"
      done)"
      ;;
    *)
      echo "ERROR: TARGET_SCOPE must be either 'owner' or 'registry'."
      exit 1
      ;;
  esac
fi

if [ -z "${REPOS:-}" ]; then
  echo "ERROR: No repositories selected for sync."
  exit 1
fi

while IFS= read -r repo; do
  [ -z "$repo" ] && continue

  target="$GITHUB_OWNER/$repo"
  echo ""
  echo "━━ SYNC $target ━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  if "$PUSH_SCRIPT" "$target"; then
    SUCCESS=$((SUCCESS + 1))
  else
    FAILED=$((FAILED + 1))
  fi
done <<EOF
$REPOS
EOF

echo ""
echo "========================================"
echo " Sweep complete: $SUCCESS succeeded | $FAILED failed"
echo "========================================"

[ "$FAILED" -eq 0 ]
