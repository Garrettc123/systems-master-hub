#!/usr/bin/env bash
# ===========================================================================
# GARCAR AUTOKEY — validate-secrets.sh
# Validates that all required GitHub Secrets exist for all repos in registry/repos.json.
# Does NOT read secret values (GitHub never returns them) — only checks
# presence.
#
# Usage: bash vault/validate-secrets.sh [--repo <repo>]
# ===========================================================================
set -euo pipefail

GITHUB_ORG="Garrettc123"
TARGET_REPO=""
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REGISTRY_FILE="${REGISTRY_FILE:-$ROOT_DIR/registry/repos.json}"

while [ $# -gt 0 ]; do
  case "$1" in
    --repo)
      [ $# -lt 2 ] && { echo "ERROR: Missing value for --repo" >&2; exit 1; }
      TARGET_REPO="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[AUTOKEY-VALIDATE]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error()   { echo -e "${RED}[✗]${NC} $1"; }

if ! command -v gh &>/dev/null; then
  log_error "GitHub CLI (gh) not found."
  exit 1
fi

declare -A REQUIRED
if [ ! -f "$REGISTRY_FILE" ]; then
  log_error "Registry file not found: $REGISTRY_FILE"
  exit 1
fi
if ! command -v jq &>/dev/null; then
  log_error "jq not found."
  exit 1
fi

while IFS='|' read -r repo required; do
  [ -z "${repo:-}" ] && continue
  REQUIRED["$repo"]="$required"
done < <(
  jq -r '
    [
      (.tier1.repos // {}),
      (.tier2.repos // {}),
      (.tier3.repos // {})
    ]
    | map(to_entries[])
    | flatten
    | .[]
    | .key + "|" + ((.value.requiredSecrets // []) | join(" "))
  ' "$REGISTRY_FILE"
)

if [ "${#REQUIRED[@]}" -eq 0 ]; then
  log_error "No repository mappings found in registry."
  exit 1
fi

if [ -n "$TARGET_REPO" ]; then
  REPOS=("$TARGET_REPO")
else
  mapfile -t REPOS < <(printf "%s\n" "${!REQUIRED[@]}" | sort)
fi

PASS=0
FAIL=0
TOTAL_SECRETS=0

log_info "=========================================="
log_info "GARCAR AUTOKEY — Secret Validation"
log_info "Time: $(date -u)"
log_info "=========================================="

for repo in "${REPOS[@]}"; do
  full_repo="$GITHUB_ORG/$repo"
  log_info "Checking: $full_repo"

  # Get list of existing secrets
  existing_secrets=$(gh secret list --repo "$full_repo" --json name -q '.[].name' 2>/dev/null || echo "")

  required_list="${REQUIRED[$repo]:-}"
  if [ -z "$required_list" ]; then
    log_warn "No requirements defined for $repo — skipping"
    continue
  fi

  read -ra required_arr <<< "$required_list"

  for secret in "${required_arr[@]}"; do
    TOTAL_SECRETS=$((TOTAL_SECRETS + 1))
    if echo "$existing_secrets" | grep -q "^${secret}$"; then
      log_success "  $secret ✓"
      PASS=$((PASS + 1))
    else
      log_error "  $secret ✗ MISSING"
      FAIL=$((FAIL + 1))
    fi
  done
done

echo ""
log_info "=========================================="
log_info "VALIDATION SUMMARY"
log_info "Total checked: $TOTAL_SECRETS"
log_success "Present: $PASS"
[ $FAIL -gt 0 ] && log_error "Missing: $FAIL"
log_info "=========================================="

if [ $FAIL -gt 0 ]; then
  log_error "$FAIL secrets are missing. Run: bash vault/vault-setup.sh"
  exit 1
fi

log_success "All required secrets are present across all repos."
exit 0
