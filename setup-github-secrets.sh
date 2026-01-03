#!/bin/bash
# Setup GitHub Secrets for Pixel 10 Deployment

set -e

echo ""
echo "========================================"
echo "GITHUB SECRETS SETUP"
echo "========================================"
echo ""

GITHUB_USER="garrettc123"
GITHUB_REPO="systems-master-hub"

# The SSH private key (base64 decoded)
SSH_KEY="-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gt
ZWQyNTUxOQAAACD3PChxmOnIj9BD7Qtkw6yyCIo/uo3DdtnPtxA2dmwuBwAAAJjL0ued
y9LngwAAAAtzc2gtZWQyNTUxOQAAACD3PChxmOnIj9BD7Qtkw6yyCIo/uo3DdtnPtxA2
dmwuBwAAAEBoKWAC7nWjmfz4yGgUTX6XL5F7LAx3qZKnQktWXZ/ZYfc8KHGY6ciP0EPt
C2TDrLIIij+6jcN22c+3EDZ2bC4HAAAAEXUwX2EzMjVAbG9jYWxob3N0AQIDBA==
-----END OPENSSH PRIVATE KEY-----"

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
echo "$SSH_KEY" | gh secret set PIXEL10_SSH_KEY -R "$GITHUB_USER/$GITHUB_REPO"
echo "✓ Done"

echo ""
echo "[2/3] Setting PIXEL10_IP"
echo "100.71.218.79" | gh secret set PIXEL10_IP -R "$GITHUB_USER/$GITHUB_REPO"
echo "✓ Done"

echo ""
echo "[3/3] Setting PIXEL10_SSH_PORT"
echo "8022" | gh secret set PIXEL10_SSH_PORT -R "$GITHUB_USER/$GITHUB_REPO"
echo "✓ Done"

echo ""
echo "========================================"
echo "SECRETS CONFIGURED"
echo "========================================"
echo ""
echo "Next step: Go to GitHub Actions and run the workflow"
echo "URL: https://github.com/$GITHUB_USER/$GITHUB_REPO/actions"
echo ""
