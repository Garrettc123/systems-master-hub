#!/bin/bash
# Trigger Pixel 10 LLM Platform Deployment

set -e

echo ""
echo "================================================================================"
echo "PIXEL 10 LLM PLATFORM - DEPLOYMENT TRIGGER"
echo "================================================================================"
echo ""

GITHUB_USER="garrettc123"
GITHUB_REPO="systems-master-hub"
WORKFLOW="pixel10-deploy.yml"
DEVICE_IP="${1:-100.71.218.79}"
SSH_PORT="${2:-8022}"
DRY_RUN="${3:-false}"

echo "Configuration:"
echo "  Repository: $GITHUB_USER/$GITHUB_REPO"
echo "  Workflow: $WORKFLOW"
echo "  Device IP: $DEVICE_IP"
echo "  SSH Port: $SSH_PORT"
echo "  Dry Run: $DRY_RUN"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "ERROR: GitHub CLI not installed"
    echo "Install from: https://cli.github.com"
    exit 1
fi

# Check authentication
if ! gh auth status > /dev/null 2>&1; then
    echo "Authenticating with GitHub..."
    gh auth login
fi

echo ""
echo "Triggering deployment workflow..."
echo ""

gh workflow run "$WORKFLOW" \
    -R "$GITHUB_USER/$GITHUB_REPO" \
    -f device_ip="$DEVICE_IP" \
    -f ssh_port="$SSH_PORT" \
    -f dry_run="$DRY_RUN"

echo ""
echo "================================================================================"
echo "✅ DEPLOYMENT TRIGGERED"
echo "================================================================================"
echo ""
echo "Monitoring deployment..."
echo ""
echo "Watch logs at:"
echo "  https://github.com/$GITHUB_USER/$GITHUB_REPO/actions"
echo ""
echo "Deployment timeline:"
echo "  Stage 1: SSH Connection Check - 1 min"
echo "  Stage 2: Environment Setup - 2 min"
echo "  Stage 3: Ollama Install - 5 min"
echo "  Stage 4: Model Download - 10-15 min"
echo "  Stage 5: Service Config - 3 min"
echo "  Stage 6: Health Check - 2 min"
echo ""
echo "Total time: 20-25 minutes"
echo ""
echo "When complete, test your model:"
echo "  curl -X POST http://$DEVICE_IP:11434/api/generate \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"model\": \"llama3.2:3b\", \"prompt\": \"Hello!\", \"stream\": false}'"
echo ""
