#!/usr/bin/env bash
# AutoKey bulk sync helper.
# Discovers repositories in an owner account and propagates all VAL_* secrets.
# Usage:
#   GITHUB_OWNER=Garrettc123 GH_TOKEN=... bash .github/scripts/autokey-sync-all.sh
#   TARGET_REPO=garcar-payments DRY_RUN=true bash .github/scripts/autokey-sync-all.sh

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
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

list_repos() {
  gh repo list "$GITHUB_OWNER" \
    --limit 1000 \
    --json name,isArchived,isFork \
    --jq '.[] | .name + "\t" + (.isArchived|tostring) + "\t" + (.isFork|tostring)'
}

echo "========================================"
echo " AutoKey Sweep Owner: $GITHUB_OWNER"
echo "========================================"

SUCCESS=0
FAILED=0

if [ -n "$TARGET_REPO" ]; then
  REPOS="$TARGET_REPO"
else
  REPOS="$(list_repos | while IFS=$'\t' read -r repo archived fork; do
    if [ "$INCLUDE_ARCHIVED" != "true" ] && [ "$archived" = "true" ]; then
      continue
    fi
    if [ "$INCLUDE_FORKS" != "true" ] && [ "$fork" = "true" ]; then
      continue
    fi
    printf '%s\n' "$repo"
  done)"
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
