#!/usr/bin/env bash
# ===========================================================================
# GARCAR AUTOKEY — bootstrap.sh
# All-in-one: clone repo, install deps, fill vault, load secrets, validate.
#
# Run this from ANYWHERE on your machine:
#   curl -fsSL https://raw.githubusercontent.com/Garrettc123/systems-master-hub/main/bootstrap.sh | bash
#
# OR if you already have the repo:
#   bash bootstrap.sh
# ===========================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
GITHUB_ORG="Garrettc123"
REPO_NAME="systems-master-hub"
REPO_URL="https://github.com/$GITHUB_ORG/$REPO_NAME.git"
CLONE_DIR="$HOME/$REPO_NAME"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[AUTOKEY]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓ AUTOKEY]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[⚠ AUTOKEY]${NC} $1"; }
log_error()   { echo -e "${RED}[✗ AUTOKEY]${NC} $1"; }
log_step()    { echo -e "\n${BOLD}${BLUE}━━━ $1 ━━━${NC}"; }

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║     GARCAR AUTOKEY — Bootstrap & Vault Setup     ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ---------------------------------------------------------------------------
# STEP 1: Detect OS / package manager
# ---------------------------------------------------------------------------
log_step "STEP 1: Detecting environment"

OS="unknown"
PKG_MANAGER=""

if [[ "$OSTYPE" == "darwin"* ]]; then
  OS="mac"
  PKG_MANAGER="brew"
  log_info "Detected: macOS"
elif [[ -f /etc/termux-login.sh ]] || [[ -n "${TERMUX_VERSION:-}" ]]; then
  OS="termux"
  PKG_MANAGER="pkg"
  log_info "Detected: Termux (Android)"
elif [[ -f /etc/debian_version ]]; then
  OS="debian"
  PKG_MANAGER="apt"
  log_info "Detected: Debian/Ubuntu Linux"
elif [[ -f /etc/redhat-release ]]; then
  OS="redhat"
  PKG_MANAGER="yum"
  log_info "Detected: RedHat/CentOS/Fedora Linux"
else
  OS="linux"
  PKG_MANAGER="apt"
  log_warn "Unknown OS — assuming apt. Adjust manually if needed."
fi

# ---------------------------------------------------------------------------
# STEP 2: Install gh CLI if missing
# ---------------------------------------------------------------------------
log_step "STEP 2: Checking GitHub CLI (gh)"

if command -v gh &>/dev/null; then
  GH_VERSION=$(gh --version | head -1)
  log_success "gh already installed: $GH_VERSION"
else
  log_info "gh not found — installing..."
  case "$OS" in
    mac)
      brew install gh
      ;;
    termux)
      pkg install gh -y
      ;;
    debian|linux)
      type -p curl >/dev/null || (sudo apt update && sudo apt install curl -y)
      curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | \
        sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
      sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | \
        sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
      sudo apt update && sudo apt install gh -y
      ;;
    redhat)
      sudo dnf install 'dnf-command(config-manager)' -y
      sudo dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo
      sudo dnf install gh -y
      ;;
  esac
  log_success "gh installed: $(gh --version | head -1)"
fi

# ---------------------------------------------------------------------------
# STEP 3: Install jq if missing
# ---------------------------------------------------------------------------
log_step "STEP 3: Checking jq"

if command -v jq &>/dev/null; then
  log_success "jq already installed: $(jq --version)"
else
  log_info "jq not found — installing..."
  case "$OS" in
    mac)     brew install jq ;;
    termux)  pkg install jq -y ;;
    debian|linux) sudo apt install jq -y ;;
    redhat)  sudo yum install jq -y ;;
  esac
  log_success "jq installed: $(jq --version)"
fi

# ---------------------------------------------------------------------------
# STEP 4: Authenticate gh (if not already)
# ---------------------------------------------------------------------------
log_step "STEP 4: GitHub CLI authentication"

if gh auth status &>/dev/null; then
  GH_USER=$(gh api user -q .login 2>/dev/null || echo "authenticated")
  log_success "gh authenticated as: $GH_USER"
else
  log_warn "gh not authenticated. Launching login..."
  gh auth login
  log_success "gh authenticated."
fi

# ---------------------------------------------------------------------------
# STEP 5: Clone or update systems-master-hub
# ---------------------------------------------------------------------------
log_step "STEP 5: Clone / update systems-master-hub"

if [ -d "$CLONE_DIR/.git" ]; then
  log_info "Repo already cloned at $CLONE_DIR — pulling latest..."
  git -C "$CLONE_DIR" pull --rebase --autostash
  log_success "Repo updated."
else
  log_info "Cloning $REPO_URL → $CLONE_DIR..."
  git clone "$REPO_URL" "$CLONE_DIR"
  log_success "Repo cloned."
fi

cd "$CLONE_DIR"
log_info "Working directory: $(pwd)"

# ---------------------------------------------------------------------------
# STEP 6: Set up vault
# ---------------------------------------------------------------------------
log_step "STEP 6: Vault setup"

VAULT_FILE="vault/.vault.env"
TEMPLATE_FILE="vault/.vault.env.template"

if [ ! -f "$TEMPLATE_FILE" ]; then
  log_error "Template not found at $TEMPLATE_FILE — repo may not be fully initialized."
  exit 1
fi

if [ -f "$VAULT_FILE" ]; then
  log_warn "$VAULT_FILE already exists."
  read -rp "$(echo -e "${YELLOW}Overwrite existing vault? (y/N):${NC} ")" OVERWRITE
  if [[ "$OVERWRITE" =~ ^[Yy]$ ]]; then
    cp "$TEMPLATE_FILE" "$VAULT_FILE"
    log_info "Vault reset from template."
  else
    log_info "Keeping existing vault file."
  fi
else
  cp "$TEMPLATE_FILE" "$VAULT_FILE"
  log_success "Vault file created from template."
fi

# ---------------------------------------------------------------------------
# STEP 7: Open vault for editing
# ---------------------------------------------------------------------------
log_step "STEP 7: Fill in your credentials"

log_warn "Opening vault/$VAULT_FILE in your editor..."
log_warn "Fill in ALL values. Save and close when done."
echo ""
echo -e "  ${BOLD}Quick reference:${NC}"
echo -e "  STRIPE_SECRET_KEY      → https://dashboard.stripe.com/apikeys"
echo -e "  STRIPE_WEBHOOK_SECRET  → https://dashboard.stripe.com/webhooks"
echo -e "  SUPABASE_URL           → Supabase Dashboard → Settings → API"
echo -e "  SUPABASE_SERVICE_KEY   → Supabase Dashboard → Settings → API"
echo -e "  RAILWAY_TOKEN          → https://railway.app/account/tokens"
echo -e "  LINEAR_API_KEY         → https://linear.app/settings/api"
echo -e "  SLACK_WEBHOOK_URL      → https://api.slack.com/apps → Incoming Webhooks"
echo -e "  GITHUB_TOKEN           → https://github.com/settings/tokens"
echo ""
read -rp "$(echo -e "${BLUE}Press ENTER to open editor (or Ctrl+C to abort and edit manually)...${NC}")" _

# Pick best available editor
if command -v code &>/dev/null; then
  code --wait "$VAULT_FILE"
elif [ -n "${EDITOR:-}" ]; then
  $EDITOR "$VAULT_FILE"
elif command -v nano &>/dev/null; then
  nano "$VAULT_FILE"
elif command -v vim &>/dev/null; then
  vim "$VAULT_FILE"
else
  log_warn "No editor found. Edit manually: $CLONE_DIR/$VAULT_FILE"
  read -rp "Press ENTER when done editing..."
fi

# ---------------------------------------------------------------------------
# STEP 8: Run vault-setup.sh — load all secrets into GitHub
# ---------------------------------------------------------------------------
log_step "STEP 8: Loading secrets into GitHub (all 9 repos)"

chmod +x vault/vault-setup.sh
bash vault/vault-setup.sh

# ---------------------------------------------------------------------------
# STEP 9: Validate all secrets are present
# ---------------------------------------------------------------------------
log_step "STEP 9: Validating secret presence across all repos"

chmod +x vault/validate-secrets.sh
bash vault/validate-secrets.sh

# ---------------------------------------------------------------------------
# DONE
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  ✓ AUTOKEY BOOTSTRAP COMPLETE — Garcar Empire is armed.     ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
log_success "Repo:       $CLONE_DIR"
log_success "Secrets:    Loaded across all 9 Garcar repos"
log_success "Rotation:   Automated via GitHub Actions (quarterly + daily validation)"
log_success "Next step:  Trigger sweep — bash orchestrate/garcar-sweep.sh full"
echo ""
