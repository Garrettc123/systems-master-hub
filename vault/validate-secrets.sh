#!/usr/bin/env bash
# ===========================================================================
# GARCAR AUTOKEY — validate-secrets.sh
# Validates that all required GitHub Secrets exist for all Tier-1 repos.
# Does NOT read secret values (GitHub never returns them) — only checks
# presence.
#
# Usage: bash vault/validate-secrets.sh [--repo <repo>]
# ===========================================================================
set -euo pipefail

GITHUB_ORG="Garrettc123"
TARGET_REPO=""

for arg in "$@"; do
  case $arg in
    --repo) TARGET_REPO="$2"; shift ;;
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

# Required secrets per repo
declare -A REQUIRED
REQUIRED["systems-master-hub"]="GITHUB_TOKEN LINEAR_API_KEY SLACK_WEBHOOK_URL RAILWAY_TOKEN"
REQUIRED["garcar-payments"]="STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET STRIPE_PUBLISHABLE_KEY SUPABASE_URL SUPABASE_SERVICE_KEY APP_URL RAILWAY_TOKEN SLACK_WEBHOOK_URL LINEAR_API_KEY"
REQUIRED["garcar-payment-loop"]="STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET SUPABASE_URL SUPABASE_SERVICE_KEY RAILWAY_TOKEN SLACK_WEBHOOK_URL LINEAR_API_KEY"
REQUIRED["mars-api"]="SUPABASE_URL SUPABASE_SERVICE_KEY APP_URL RAILWAY_TOKEN SLACK_WEBHOOK_URL LINEAR_API_KEY"
REQUIRED["enterprise-mlops-platform"]="SUPABASE_URL SUPABASE_SERVICE_KEY RAILWAY_TOKEN SLACK_WEBHOOK_URL"
REQUIRED["TITAN-Autonomous-Business-Empire"]="STRIPE_SECRET_KEY SUPABASE_URL SUPABASE_SERVICE_KEY RAILWAY_TOKEN LINEAR_API_KEY SLACK_WEBHOOK_URL"
REQUIRED["atlas-dashboard"]="SUPABASE_URL SUPABASE_SERVICE_KEY VERCEL_TOKEN SLACK_WEBHOOK_URL"
REQUIRED["zeus-dashboard"]="SUPABASE_URL SUPABASE_SERVICE_KEY LINEAR_API_KEY VERCEL_TOKEN SLACK_WEBHOOK_URL"
REQUIRED["neural-mesh"]="GITHUB_TOKEN SLACK_WEBHOOK_URL"

if [ -n "$TARGET_REPO" ]; then
  REPOS=("$TARGET_REPO")
else
  REPOS=("systems-master-hub" "garcar-payments" "garcar-payment-loop" "mars-api" "enterprise-mlops-platform" "TITAN-Autonomous-Business-Empire" "atlas-dashboard" "zeus-dashboard" "neural-mesh")
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
