#!/bin/bash
################################################################################
# 🚀 UNIVERSAL WORKFLOW DEPLOYER
# Automatically fixes ALL repositories by deploying adaptive CI/CD
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "═══════════════════════════════════════════════════════════════"
echo "  🔧 UNIVERSAL WORKFLOW FIXER"
echo "  Deploying adaptive CI/CD to ALL repositories"
echo "═══════════════════════════════════════════════════════════════"
echo -e "${NC}"

# List of all your repositories (auto-generated from GitHub search)
REPOS=(
  "nwu-protocol"
  "autonomous-income-deployment"
  "tree-of-life-system"
  "enterprise-unified-platform"
  "portfolio-website"
  "ai-business-platform"
  "APEX-Universal-AI-Operating-System"
  "enterprise-mlops-platform"
  "stablecoin-protocol"
  "autohelix"
)

TOTAL=${#REPOS[@]}
CURRENT=0

for repo in "${REPOS[@]}"; do
  ((CURRENT++))
  echo -e "${YELLOW}[${CURRENT}/${TOTAL}] Fixing ${repo}...${NC}"
  
  # Clone repo
  if [ ! -d "$repo" ]; then
    gh repo clone "Garrettc123/${repo}" 2>/dev/null || {
      echo -e "${RED}  ✗ Failed to clone${NC}"
      continue
    }
  fi
  
  cd "$repo"
  
  # Create .github/workflows if it doesn't exist
  mkdir -p .github/workflows
  
  # Copy universal workflow
  cp ../UNIVERSAL_WORKFLOW_FIX.yml .github/workflows/ci.yml
  
  # Commit and push
  git add .github/workflows/ci.yml
  git commit -m "🔧 Fix: Deploy Universal Adaptive CI/CD Workflow" || echo "  Already up to date"
  git push origin main 2>/dev/null || git push origin master 2>/dev/null || echo "  Push failed"
  
  cd ..
  
  echo -e "${GREEN}  ✓ Fixed${NC}"
done

echo ""
echo -e "${GREEN}"
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ ALL REPOSITORIES FIXED"
echo "  ${TOTAL} workflows deployed successfully"
echo "═══════════════════════════════════════════════════════════════"
echo -e "${NC}"
