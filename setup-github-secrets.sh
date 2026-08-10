#!/bin/bash
# Setup GitHub Secrets for Pixel 10 Deployment

set -e

echo ""
echo "========================================"
echo "GITHUB SECRETS SETUP"
echo "========================================"
echo ""

GITHUB_USER="${GITHUB_USER:-garrettc123}"
GITHUB_REPO="${GITHUB_REPO:-systems-master-hub}"

# The SSH private key is NEVER stored in this repository. Point PIXEL10_SSH_KEY_FILE
# at a private key on disk (default: ~/.ssh/pixel10_ed25519) or export PIXEL10_SSH_KEY.
SSH_KEY_FILE="${PIXEL10_SSH_KEY_FILE:-$HOME/.ssh/pixel10_ed25519}"

if [ -z "${PIXEL10_SSH_KEY:-}" ]; then
    if [ ! -f "$SSH_KEY_FILE" ]; then
        echo "ERROR: no private key available."
        echo "  Provide one of:"
        echo "    export PIXEL10_SSH_KEY=\"\$(cat /path/to/key)\""
        echo "    export PIXEL10_SSH_KEY_FILE=/path/to/key"
        echo "  Generate a fresh key with: ssh-keygen -t ed25519 -f \"$SSH_KEY_FILE\" -N ''"
        exit 1
    fi
    PIXEL10_SSH_KEY="$(cat "$SSH_KEY_FILE")"
fi

DEVICE_IP="${PIXEL10_IP:?PIXEL10_IP must be set (device address)}"
SSH_PORT="${PIXEL10_SSH_PORT:-8022}"

echo "Installing GitHub CLI if needed..."
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI not found. Please install from: https://cli.github.com"
    exit 1
fi

echo "Authenticating with GitHub..."
gh auth login

echo ""
echo "Creating secrets..."
echo ""

echo "[1/3] Setting PIXEL10_SSH_KEY"
printf '%s\n' "$PIXEL10_SSH_KEY" | gh secret set PIXEL10_SSH_KEY -R "$GITHUB_USER/$GITHUB_REPO"
echo "✓ Done"

echo ""
echo "[2/3] Setting PIXEL10_IP"
printf '%s\n' "$DEVICE_IP" | gh secret set PIXEL10_IP -R "$GITHUB_USER/$GITHUB_REPO"
echo "✓ Done"

echo ""
echo "[3/3] Setting PIXEL10_SSH_PORT"
printf '%s\n' "$SSH_PORT" | gh secret set PIXEL10_SSH_PORT -R "$GITHUB_USER/$GITHUB_REPO"
echo "✓ Done"

echo ""
echo "========================================"
echo "SECRETS CONFIGURED"
echo "========================================"
echo ""
echo "Next step: Go to GitHub Actions and run the workflow"
echo "URL: https://github.com/$GITHUB_USER/$GITHUB_REPO/actions"
echo ""
