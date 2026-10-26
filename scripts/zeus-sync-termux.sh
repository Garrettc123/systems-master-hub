#!/data/data/com.termux/files/usr/bin/bash
# ZEUS Termux GitHub sync — safe, non-destructive repository sync.
# Usage:
#   bash scripts/zeus-sync-termux.sh
#   GH_PAT=... bash scripts/zeus-sync-termux.sh
#   GITHUB_TOKEN=... bash scripts/zeus-sync-termux.sh
#
# Clones or fast-forward-pulls repositories owned by Garrettc123.
# It does NOT install dependencies, start services, overwrite local edits,
# delete repositories, or deploy cloud infrastructure.

set -Eeuo pipefail
umask 077

OWNER="Garrettc123"
ROOT="${ZEUS_REPOS_DIR:-$HOME/ZEUS/repos}"
TOKEN="${GH_PAT:-${GITHUB_TOKEN:-}}"
API="https://api.github.com"
PER_PAGE=100
PAGE=1
SYNCED=0
SKIPPED=0
FAILED=0

command -v git >/dev/null 2>&1 || { echo "ERROR: git is required. Install with: pkg install git"; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is required. Install with: pkg install curl"; exit 1; }
command -v python >/dev/null 2>&1 || { echo "ERROR: python is required. Install with: pkg install python"; exit 1; }

mkdir -p "$ROOT"
chmod 700 "$ROOT"

api_page() {
  local page="$1"
  if [[ -n "$TOKEN" ]]; then
    curl --fail --silent --show-error --location \
      -H "Authorization: Bearer $TOKEN" \
      -H "Accept: application/vnd.github+json" \
      "$API/user/repos?per_page=$PER_PAGE&page=$page&sort=full_name&direction=asc"
  else
    # Public repositories only when no token is provided.
    curl --fail --silent --show-error --location \
      -H "Accept: application/vnd.github+json" \
      "$API/users/$OWNER/repos?per_page=$PER_PAGE&page=$page&sort=full_name&direction=asc"
  fi
}

echo "ZEUS GitHub sync"
echo "Owner: $OWNER"
echo "Destination: $ROOT"
if [[ -z "$TOKEN" ]]; then
  echo "Mode: public repositories only (set GH_PAT or GITHUB_TOKEN for authorized private-repo access)"
else
  echo "Mode: authenticated repositories (token value will not be printed)"
fi
echo

while :; do
  JSON="$(api_page "$PAGE")" || { echo "ERROR: GitHub API request failed on page $PAGE"; exit 1; }
  COUNT="$(printf '%s' "$JSON" | python -c 'import json,sys; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else -1)')"
  if [[ "$COUNT" -lt 0 ]]; then
    echo "ERROR: GitHub returned an API error instead of a repository list."
    printf '%s\n' "$JSON" | python -c 'import json,sys; d=json.load(sys.stdin); print(d.get("message","Unknown API error"))' 2>/dev/null || true
    exit 1
  fi
  [[ "$COUNT" -eq 0 ]] && break

  while IFS=$'\t' read -r NAME CLONE_URL ARCHIVED; do
    [[ -z "$NAME" || "$NAME" == "null" ]] && continue
    if [[ "$ARCHIVED" == "true" ]]; then
      echo "SKIP archived: $NAME"
      SKIPPED=$((SKIPPED+1))
      continue
    fi

    DEST="$ROOT/$NAME"
    if [[ -d "$DEST/.git" ]]; then
      if [[ -n "$(git -C "$DEST" status --porcelain 2>/dev/null)" ]]; then
        echo "SKIP local changes (preserved): $NAME"
        SKIPPED=$((SKIPPED+1))
        continue
      fi
      if git -C "$DEST" pull --ff-only --prune; then
        echo "UPDATED: $NAME"
        SYNCED=$((SYNCED+1))
      else
        echo "FAILED update: $NAME"
        FAILED=$((FAILED+1))
      fi
    elif [[ -e "$DEST" ]]; then
      echo "SKIP existing non-git path (preserved): $NAME"
      SKIPPED=$((SKIPPED+1))
    else
      if git clone -- "$CLONE_URL" "$DEST"; then
        echo "CLONED: $NAME"
        SYNCED=$((SYNCED+1))
      else
        echo "FAILED clone: $NAME"
        FAILED=$((FAILED+1))
      fi
    fi
  done < <(printf '%s' "$JSON" | python -c '
import json,sys
d=json.load(sys.stdin)
for r in d:
    if r.get("owner",{}).get("login","").lower() == "garrettc123":
        print("{}\t{}\t{}".format(r.get("name",""),r.get("clone_url",""),str(r.get("archived",False)).lower()))
')

  [[ "$COUNT" -lt "$PER_PAGE" ]] && break
  PAGE=$((PAGE+1))
done

echo
echo "Sync summary: cloned/updated=$SYNCED skipped=$SKIPPED failed=$FAILED"
echo "Repository directory: $ROOT"
echo "No service startup or deployment was attempted."
[[ "$FAILED" -eq 0 ]]
