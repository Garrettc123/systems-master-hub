#!/bin/bash
# Setup GitHub Secrets for Pixel 10 Deployment
# NEVER commit real private keys. Supply via PIXEL10_SSH_KEY env or file path.

set -euo pipefail

echo ""
echo "========================================"
echo "GITHUB SECRETS SETUP"
echo "========================================"
echo ""

GITHUB_USER="${GITHUB_USER:-garrettc123}"
GITHUB_REPO="${GITHUB_REPO:-systems-master-hub}"

if [ -z "${PIXEL10_SSH_KEY:-}" ]; then
  if [ -n "${PIXEL10_SSH_KEY_FILE:-}" ] && [ -f "$PIXEL10_SSH_KEY_FILE" ]; then
    PIXEL10_SSH_KEY="$(cat "$PIXEL10_SSH_KEY_FILE")"
  else
    echo "ERROR: Set PIXEL10_SSH_KEY or PIXEL10_SSH_KEY_FILE before running."
    echo "Example: export PIXEL10_SSH_KEY_FILE=~/.ssh/pixel10_key"
    exit 1
  fi
fi

if ! command -v gh &> /dev/null; then
  echo "GitHub CLI not found. Install from: https://cli.github.com"
  exit 1
fi

echo "Creating secrets for $GITHUB_USER/$GITHUB_REPO..."
echo ""

echo "[1/3] Setting PIXEL10_SSH_KEY"
echo "$PIXEL10_SSH_KEY" | gh secret set PIXEL10_SSH_KEY -R "$GITHUB_USER/$GITHUB_REPO"
echo "Done"

echo ""
echo "[2/3] Setting PIXEL10_IP"
echo "${PIXEL10_IP:-100.71.218.79}" | gh secret set PIXEL10_IP -R "$GITHUB_USER/$GITHUB_REPO"
echo "Done"

echo ""
echo "[3/3] Setting PIXEL10_SSH_PORT"
echo "${PIXEL10_SSH_PORT:-8022}" | gh secret set PIXEL10_SSH_PORT -R "$GITHUB_USER/$GITHUB_REPO"
echo "Done"

echo ""
echo "========================================"
echo "SECRETS CONFIGURED"
echo "========================================"
echo "Next: https://github.com/$GITHUB_USER/$GITHUB_REPO/actions"
echo ""
