#!/usr/bin/env bash
# ===========================================================================
# GARCAR AUTOKEY — vault-setup.sh
# Loads all secrets from .vault.env into GitHub Repo Secrets
# for all Tier-1 repos in the Garcar empire.
#
# Usage: bash vault/vault-setup.sh [--dry-run] [--repo <repo-name>]
# ===========================================================================
set -euo pipefail

VAULT_FILE="$(dirname "$0")/.vault.env"
DRY_RUN=false
TARGET_REPO=""
GITHUB_ORG="Garrettc123"

# Parse args
for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=true ;;
    --repo) TARGET_REPO="$2"; shift ;;
  esac
done

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log_info()    { echo -e "${BLUE}[AUTOKEY]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓ AUTOKEY]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[⚠ AUTOKEY]${NC} $1"; }
log_error()   { echo -e "${RED}[✗ AUTOKEY]${NC} $1"; }

# Check dependencies
if ! command -v gh &>/dev/null; then
  log_error "GitHub CLI (gh) not found. Install: https://cli.github.com"
  exit 1
fi

if ! command -v jq &>/dev/null; then
  log_error "jq not found. Install: brew install jq (mac) or apt install jq (linux)"
  exit 1
fi

# Check vault file
if [ ! -f "$VAULT_FILE" ]; then
  log_error "Vault file not found: $VAULT_FILE"
  log_info "Run: cp vault/.vault.env.template vault/.vault.env"
  log_info "Then fill in all values and retry."
  exit 1
fi

# Validate no empty required secrets
REQUIRED_SECRETS=("GITHUB_TOKEN" "LINEAR_API_KEY" "SLACK_WEBHOOK_URL" "STRIPE_SECRET_KEY" "STRIPE_WEBHOOK_SECRET" "SUPABASE_URL" "SUPABASE_SERVICE_KEY" "APP_URL" "RAILWAY_TOKEN")
EMPTY_COUNT=0
for secret in "${REQUIRED_SECRETS[@]}"; do
  val=$(grep "^${secret}=" "$VAULT_FILE" | cut -d= -f2-)
  if [ -z "$val" ]; then
    log_warn "Required secret is empty: $secret"
    EMPTY_COUNT=$((EMPTY_COUNT + 1))
  fi
done

if [ $EMPTY_COUNT -gt 0 ]; then
  log_error "$EMPTY_COUNT required secrets are empty. Fill them in vault/.vault.env before proceeding."
  exit 1
fi

# Load secrets from vault
declare -A SECRET_MAP
while IFS='=' read -r key value; do
  [[ "$key" =~ ^#.*$ ]] && continue
  [[ -z "$key" ]] && continue
  [[ "$key" =~ ^AUTOKEY_ ]] && continue
  SECRET_MAP["$key"]="$value"
done < "$VAULT_FILE"

# Define which repos get which secrets (per SECRETSAPI.md)
declare -A REPO_SECRET_MAP
REPO_SECRET_MAP["systems-master-hub"]="GITHUB_TOKEN LINEAR_API_KEY SLACK_WEBHOOK_URL RAILWAY_TOKEN"
REPO_SECRET_MAP["garcar-payments"]="STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET STRIPE_PUBLISHABLE_KEY SUPABASE_URL SUPABASE_SERVICE_KEY APP_URL RAILWAY_TOKEN SLACK_WEBHOOK_URL LINEAR_API_KEY"
REPO_SECRET_MAP["garcar-payment-loop"]="STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET SUPABASE_URL SUPABASE_SERVICE_KEY RAILWAY_TOKEN SLACK_WEBHOOK_URL LINEAR_API_KEY"
REPO_SECRET_MAP["mars-api"]="SUPABASE_URL SUPABASE_SERVICE_KEY APP_URL RAILWAY_TOKEN SLACK_WEBHOOK_URL LINEAR_API_KEY"
REPO_SECRET_MAP["enterprise-mlops-platform"]="SUPABASE_URL SUPABASE_SERVICE_KEY RAILWAY_TOKEN SLACK_WEBHOOK_URL"
REPO_SECRET_MAP["TITAN-Autonomous-Business-Empire"]="STRIPE_SECRET_KEY SUPABASE_URL SUPABASE_SERVICE_KEY RAILWAY_TOKEN LINEAR_API_KEY SLACK_WEBHOOK_URL"
REPO_SECRET_MAP["atlas-dashboard"]="SUPABASE_URL SUPABASE_SERVICE_KEY VERCEL_TOKEN SLACK_WEBHOOK_URL"
REPO_SECRET_MAP["zeus-dashboard"]="SUPABASE_URL SUPABASE_SERVICE_KEY LINEAR_API_KEY VERCEL_TOKEN SLACK_WEBHOOK_URL"
REPO_SECRET_MAP["neural-mesh"]="GITHUB_TOKEN SLACK_WEBHOOK_URL"

# Determine target repos
if [ -n "$TARGET_REPO" ]; then
  REPOS=("$TARGET_REPO")
else
  REPOS=("systems-master-hub" "garcar-payments" "garcar-payment-loop" "mars-api" "enterprise-mlops-platform" "TITAN-Autonomous-Business-Empire" "atlas-dashboard" "zeus-dashboard" "neural-mesh")
fi

log_info "=========================================="
log_info "GARCAR AUTOKEY — Secret Setup"
log_info "Org: $GITHUB_ORG | Repos: ${#REPOS[@]}"
[ "$DRY_RUN" = true ] && log_warn "DRY RUN — no secrets will be written"
log_info "=========================================="

TOTAL_SET=0
TOTAL_SKIP=0
TOTAL_ERR=0

for repo in "${REPOS[@]}"; do
  full_repo="$GITHUB_ORG/$repo"
  log_info "Processing: $full_repo"

  if [ -z "${REPO_SECRET_MAP[$repo]+x}" ]; then
    log_warn "No secret mapping found for $repo — skipping"
    continue
  fi

  read -ra secrets_for_repo <<< "${REPO_SECRET_MAP[$repo]}"

  for secret_name in "${secrets_for_repo[@]}"; do
    secret_value="${SECRET_MAP[$secret_name]:-}"

    if [ -z "$secret_value" ]; then
      log_warn "Skipping $secret_name for $repo (value not set in vault)"
      TOTAL_SKIP=$((TOTAL_SKIP + 1))
      continue
    fi

    if [ "$DRY_RUN" = true ]; then
      log_info "  [DRY-RUN] Would set: $secret_name → $full_repo"
      TOTAL_SET=$((TOTAL_SET + 1))
    else
      if echo "$secret_value" | gh secret set "$secret_name" --repo "$full_repo" 2>/dev/null; then
        log_success "  Set: $secret_name → $repo"
        TOTAL_SET=$((TOTAL_SET + 1))
      else
        log_error "  Failed to set: $secret_name → $repo"
        TOTAL_ERR=$((TOTAL_ERR + 1))
      fi
    fi
  done
done

echo ""
log_info "=========================================="
log_info "AUTOKEY SETUP COMPLETE"
log_success "Secrets set: $TOTAL_SET"
[ $TOTAL_SKIP -gt 0 ] && log_warn "Secrets skipped (empty): $TOTAL_SKIP"
[ $TOTAL_ERR -gt 0 ] && log_error "Secrets failed: $TOTAL_ERR"
log_info "=========================================="

if [ $TOTAL_ERR -gt 0 ]; then
  log_error "Some secrets failed. Check gh auth status and repo permissions."
  exit 1
fi

log_success "All secrets loaded. Run: bash vault/validate-secrets.sh to verify."
