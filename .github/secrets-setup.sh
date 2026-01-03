#!/bin/bash
# Automated GitHub Secrets Setup for Pixel 10 Deployment

set -e

echo "========================================"
echo "GitHub Secrets Setup"
echo "========================================"
echo ""

GITHUB_USER="garrettc123"
GITHUB_REPO="systems-master-hub"
DEVICE_IP="100.71.218.79"
SSH_PORT="8022"

SSH_KEY="-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gt
ZWQyNTUxOQAAACD3PChxmOnIj9BD7Qtkw6yyCIo/uo3DdtnPtxA2dmwuBwAAAJjL0ued
y9LngwAAAAtzc2gtZWQyNTUxOQAAACD3PChxmOnIj9BD7Qtkw6yyCIo/uo3DdtnPtxA2
dmwuBwAAAEBoKWAC7nWjmfz4yGgUTX6XL5F7LAx3qZKnQktWXZ/ZYfc8KHGY6ciP0EPt
C2TDrLIIij+6jcN22c+3EDZ2bC4HAAAAEXUwX2EzMjVAbG9jYWxob3N0AQIDBA==
-----END OPENSSH PRIVATE KEY-----"

# Check if gh CLI is installed
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

# Authenticate
echo "Authenticating with GitHub..."
gh auth login

# Create secrets
echo ""
echo "Creating GitHub Secrets..."
echo ""

echo "[1/3] PIXEL10_SSH_KEY"
echo "$SSH_KEY" | gh secret set PIXEL10_SSH_KEY -R "$GITHUB_USER/$GITHUB_REPO"

echo "[2/3] PIXEL10_IP"
echo "$DEVICE_IP" | gh secret set PIXEL10_IP -R "$GITHUB_USER/$GITHUB_REPO"

echo "[3/3] PIXEL10_SSH_PORT"
echo "$SSH_PORT" | gh secret set PIXEL10_SSH_PORT -R "$GITHUB_USER/$GITHUB_REPO"

echo ""
echo "========================================"
echo "✓ Secrets Created Successfully"
echo "========================================"
echo ""
echo "Ready to deploy! Go to:"
echo "https://github.com/$GITHUB_USER/$GITHUB_REPO/actions"
echo ""
