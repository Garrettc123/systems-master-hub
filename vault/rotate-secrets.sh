#!/usr/bin/env bash
# ===========================================================================
# GARCAR AUTOKEY — rotate-secrets.sh
# Rotates auto-generatable internal secrets:
#   - JWT_SECRET
#   - API signing keys
#   - Encryption keys
#   - Session secrets
#
# Stripe/Supabase/Railway secrets must be rotated via their dashboards
# then updated in .vault.env and re-run vault-setup.sh.
#
# Usage:
#   bash vault/rotate-secrets.sh [--repo <repo>] [--secret <name>] [--dry-run]
#
# Full rotation (all internal secrets, all repos):
#   bash vault/rotate-secrets.sh
# ===========================================================================
set -euo pipefail

VAULT_DIR="$(dirname "$0")"
VAULT_FILE="$VAULT_DIR/.vault.env"
DRY_RUN=false
TARGET_REPO=""
TARGET_SECRET=""
GITHUB_ORG="Garrettc123"
ROTATION_LOG="$VAULT_DIR/rotation-log.txt"

for arg in "$@"; do
  case $arg in
    --dry-run)  DRY_RUN=true ;;
    --repo)     TARGET_REPO="$2"; shift ;;
    --secret)   TARGET_SECRET="$2"; shift ;;
  esac
done

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[AUTOKEY-ROTATE]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error()   { echo -e "${RED}[✗]${NC} $1"; }

generate_secret() {
  local length=${1:-64}
  # Use openssl if available, else urandom fallback
  if command -v openssl &>/dev/null; then
    openssl rand -hex "$length"
  else
    cat /dev/urandom | tr -dc 'a-f0-9' | head -c $((length * 2))
  fi
}

generate_base64_secret() {
  local length=${1:-32}
  if command -v openssl &>/dev/null; then
    openssl rand -base64 "$length" | tr -d '\n'
  else
    cat /dev/urandom | base64 | head -c $((length * 2))
  fi
}

rotate_secret_in_repo() {
  local secret_name="$1"
  local secret_value="$2"
  local repo="$3"
  local full_repo="$GITHUB_ORG/$repo"

  if [ "$DRY_RUN" = true ]; then
    log_info "[DRY-RUN] Would rotate $secret_name in $repo"
    return 0
  fi

  if echo "$secret_value" | gh secret set "$secret_name" --repo "$full_repo" 2>/dev/null; then
    log_success "Rotated $secret_name → $repo"
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") ROTATED $secret_name in $repo" >> "$ROTATION_LOG"
    return 0
  else
    log_error "Failed to rotate $secret_name in $repo"
    return 1
  fi
}

# ===========================================================================
# INTERNAL SECRETS (auto-generatable — safe to rotate automatically)
# ===========================================================================

declare -A INTERNAL_SECRETS

INTERNAL_SECRETS["JWT_SECRET"]="hex:64"       # 128-char hex
INTERNAL_SECRETS["API_SIGNING_KEY"]="hex:32"   # 64-char hex
INTERNAL_SECRETS["ENCRYPTION_KEY"]="base64:32" # 32-byte base64
INTERNAL_SECRETS["SESSION_SECRET"]="hex:48"    # 96-char hex

# Repos that use internal secrets
declare -A INTERNAL_REPO_MAP
INTERNAL_REPO_MAP["JWT_SECRET"]="garcar-payments mars-api"
INTERNAL_REPO_MAP["API_SIGNING_KEY"]="garcar-payments mars-api TITAN-Autonomous-Business-Empire"
INTERNAL_REPO_MAP["ENCRYPTION_KEY"]="garcar-payments garcar-payment-loop"
INTERNAL_REPO_MAP["SESSION_SECRET"]="garcar-payments"

log_info "=========================================="
log_info "GARCAR AUTOKEY — Secret Rotation"
log_info "Time: $(date -u)"
[ "$DRY_RUN" = true ] && log_warn "DRY RUN — no secrets will be written"
log_info "=========================================="

ROTATED=0
FAILED=0

for secret_name in "${!INTERNAL_SECRETS[@]}"; do
  if [ -n "$TARGET_SECRET" ] && [ "$secret_name" != "$TARGET_SECRET" ]; then
    continue
  fi

  spec="${INTERNAL_SECRETS[$secret_name]}"
  type="${spec%%:*}"
  length="${spec##*:}"

  log_info "Generating new $secret_name (type: $type, length: $length)..."
  if [ "$type" = "hex" ]; then
    new_value=$(generate_secret "$length")
  else
    new_value=$(generate_base64_secret "$length")
  fi

  repos_str="${INTERNAL_REPO_MAP[$secret_name]:-}"
  if [ -z "$repos_str" ]; then
    log_warn "No repos mapped for $secret_name — skipping"
    continue
  fi

  read -ra repos <<< "$repos_str"

  if [ -n "$TARGET_REPO" ]; then
    repos=("$TARGET_REPO")
  fi

  for repo in "${repos[@]}"; do
    if rotate_secret_in_repo "$secret_name" "$new_value" "$repo"; then
      ROTATED=$((ROTATED + 1))
    else
      FAILED=$((FAILED + 1))
    fi
  done
done

echo ""
log_info "=========================================="
log_info "ROTATION COMPLETE"
log_success "Secrets rotated: $ROTATED"
[ $FAILED -gt 0 ] && log_error "Secrets failed: $FAILED"
log_info "=========================================="
log_info ""
log_warn "EXTERNAL SECRETS (Stripe, Supabase, Railway) must be rotated via their dashboards."
log_warn "See: docs/SECRETSAPI.md → Rotation Protocol"

[ $FAILED -gt 0 ] && exit 1
exit 0
