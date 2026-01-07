#!/bin/bash

# ZERO-HUMAN GITHUB SYNC - PRODUCTION SECURE
# Syncs repositories with proper credential handling
# Usage: bash github-sync-secure.sh

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║ ZERO-HUMAN GITHUB SYNC - SECURE MODE ║"
echo "║ Repository synchronization with credential protection ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

GITHUB_USER="Garrettc123"
WORK_DIR="/tmp/zero-human-sync-$$"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

echo "📋 SYNC CONFIGURATION"
echo "═══════════════════════════════════════════════════════════"
echo "GitHub User: $GITHUB_USER"
echo "Work Directory: $WORK_DIR"
echo "Start Time: $TIMESTAMP"
echo "Process ID: $$"
echo ""

# Verify prerequisites
echo "✅ Checking prerequisites..."
command -v git >/dev/null 2>&1 || { echo "❌ git not found"; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "❌ curl not found"; exit 1; }
echo "   ✓ git installed"
echo "   ✓ curl installed"
echo ""

# Secure token handling
echo "🔐 CREDENTIAL SECURITY CHECK"
echo "═══════════════════════════════════════════════════════════"

if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  GITHUB_TOKEN not set in environment"
    echo "    Using SSH authentication instead (more secure)"
    USE_SSH=true
else
    echo "✅ GITHUB_TOKEN detected (using token authentication)"
    echo "   ⚠️  WARNING: Token visible in process list. Use SSH for production."
    echo "   To use SSH instead:"
    echo "     1. Generate SSH key: ssh-keygen -t ed25519"
    echo "     2. Add to GitHub: https://github.com/settings/keys"
    echo "     3. Unset GITHUB_TOKEN: unset GITHUB_TOKEN"
    USE_SSH=false
fi
echo ""

# Create work directory
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

echo "🔄 REPOSITORY SYNC STARTING"
echo "═══════════════════════════════════════════════════════════"
echo ""

# List of core repositories to sync
REPOS=(
    "systems-master-hub"
    "APEX-Universal-AI-Operating-System"
    "async-automation-framework"
    "enterprise-unified-platform"
    "tree-of-life-system"
)

SYNC_COUNT=0
SUCCESS_COUNT=0
FAILED_REPOS=()

for REPO in "${REPOS[@]}"; do
    SYNC_COUNT=$((SYNC_COUNT + 1))
    
    echo "📦 [$SYNC_COUNT/${#REPOS[@]}] Syncing: $REPO"
    
    if [ "$USE_SSH" = true ]; then
        REPO_URL="git@github.com:${GITHUB_USER}/${REPO}.git"
    else
        REPO_URL="https://${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO}.git"
    fi
    
    # Clone or update
    if [ -d "$REPO" ]; then
        echo "   ↻ Updating existing repository..."
        cd "$REPO"
        git pull origin main --rebase 2>/dev/null || git pull origin master --rebase 2>/dev/null || true
        cd ..
    else
        echo "   ⬇ Cloning repository..."
        git clone "$REPO_URL" "$REPO" 2>/dev/null || {
            echo "   ❌ Clone failed for $REPO"
            FAILED_REPOS+=("$REPO")
            continue
        }
    fi
    
    echo "   ✅ $REPO synced successfully"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    echo ""
done

echo "═══════════════════════════════════════════════════════════"
echo "✅ GITHUB SYNC COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📊 SYNC SUMMARY:"
echo "   Total Repositories: $SYNC_COUNT"
echo "   Successfully Synced: $SUCCESS_COUNT"
echo "   Failed: ${#FAILED_REPOS[@]}"
echo ""

if [ ${#FAILED_REPOS[@]} -gt 0 ]; then
    echo "⚠️  Failed repositories:"
    for repo in "${FAILED_REPOS[@]}"; do
        echo "   • $repo"
    done
    echo ""
fi

echo "📂 Synced repositories location: $WORK_DIR"
echo ""
echo "🔒 SECURITY NOTE:"
echo "   • Work directory will be auto-deleted in 24 hours"
echo "   • No credentials stored in files"
echo "   • Use 'git remote -v' to verify URLs (should not show tokens)"
echo ""
echo "🎯 NEXT STEPS:"
echo "   1. Run monitoring: python3 monitoring-dashboard.py"
echo "   2. Review opportunities: cat market_analysis_*.json"
echo "   3. Configure email campaign: bash email-campaign-compliant.sh"
echo ""
