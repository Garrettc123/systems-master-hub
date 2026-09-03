#!/usr/bin/env bash
# AutoKey push helper — called by every sync job in autokey-sweep-all.yml
# Usage: autokey-push.sh <owner/repo>
# Reads all VAL_* env vars and pushes each as a secret to the target repo.
# Requires GH_TOKEN (classic PAT, repo + admin:repo_hook scopes).

set -euo pipefail

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  echo "ERROR: No target repo provided"
  exit 1
fi

if [ -z "${GH_TOKEN:-}" ]; then
  echo "ERROR: GH_TOKEN not set. Add GITHUB_PAT to systems-master-hub secrets."
  echo "Required scopes: repo, admin:repo_hook"
  exit 1
fi

DRY_RUN="${DRY_RUN:-false}"
OK=0; FAIL=0; SKIP=0

push_secret() {
  local name="$1"
  local value="$2"
  if [ -n "$value" ]; then
    if [ "$DRY_RUN" = "true" ]; then
      echo "  [DRY]  $name"
      OK=$((OK+1))
    else
      if printf '%s' "$value" | gh secret set "$name" --repo "$TARGET" --body - 2>&1; then
        echo "  [OK]   $name"
        OK=$((OK+1))
      else
        echo "  [FAIL] $name"
        FAIL=$((FAIL+1))
      fi
    fi
  else
    echo "  [SKIP] $name (not set in source)"
    SKIP=$((SKIP+1))
  fi
}

echo "========================================"
echo " AutoKey → $TARGET"
echo "========================================"
[ "$DRY_RUN" = "true" ] && echo " DRY RUN ENABLED (no writes)"

# Iterate every VAL_* env var and push it as the secret name without the VAL_ prefix
while IFS='=' read -r key value; do
  secret_name="${key#VAL_}"
  push_secret "$secret_name" "$value"
done < <(env | grep '^VAL_' | sort)

echo ""
echo "======================================"
echo " Result: $OK pushed | $FAIL failed | $SKIP skipped"
echo "======================================"

if [ $SKIP -gt 0 ]; then
  echo ""
  echo "Skipped secrets are not set in systems-master-hub."
  echo "Add them at: https://github.com/Garrettc123/systems-master-hub/settings/secrets/actions"
fi

[ $FAIL -eq 0 ]
