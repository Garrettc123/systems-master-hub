#!/bin/bash
# Automated GitHub Secrets Setup for Pixel 10 Deployment
# NEVER commit real private keys. Supply via PIXEL10_SSH_KEY env or file path.

set -euo pipefail

echo "========================================"
echo "GitHub Secrets Setup"
echo "========================================"
echo ""

GITHUB_USER="${GITHUB_USER:-garrettc123}"
GITHUB_REPO="${GITHUB_REPO:-systems-master-hub}"
DEVICE_IP="${PIXEL10_IP:-100.71.218.79}"
SSH_PORT="${PIXEL10_SSH_PORT:-8022}"

if [ -z "${PIXEL10_SSH_KEY:-}" ]; then
  if [ -n "${PIXEL10_SSH_KEY_FILE:-}" ] && [ -f "$PIXEL10_SSH_KEY_FILE" ]; then
    PIXEL10_SSH_KEY="$(cat "$PIXEL10_SSH_KEY_FILE")"
  else
    echo "ERROR: Set PIXEL10_SSH_KEY or PIXEL10_SSH_KEY_FILE before running."
    exit 1
  fi
fi

if ! command -v gh &> /dev/null; then
  echo "Installing GitHub CLI..."
  if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y gh
  elif command -v brew &> /dev/null; then
    brew install gh
  else
    echo "Please install GitHub CLI from https://cli.github.com"
    exit 1
  fi
fi

echo "Creating GitHub Secrets..."
echo ""

echo "[1/3] PIXEL10_SSH_KEY"
echo "$PIXEL10_SSH_KEY" | gh secret set PIXEL10_SSH_KEY -R "$GITHUB_USER/$GITHUB_REPO"

echo "[2/3] PIXEL10_IP"
echo "$DEVICE_IP" | gh secret set PIXEL10_IP -R "$GITHUB_USER/$GITHUB_REPO"

echo "[3/3] PIXEL10_SSH_PORT"
echo "$SSH_PORT" | gh secret set PIXEL10_SSH_PORT -R "$GITHUB_USER/$GITHUB_REPO"

echo ""
echo "========================================"
echo "Secrets Created Successfully"
echo "========================================"
echo "Ready: https://github.com/$GITHUB_USER/$GITHUB_REPO/actions"
echo ""
