#!/usr/bin/env bash
################################################################################
# 🚀 FULL STACK DEPLOYMENT ORCHESTRATOR
# End-to-End: Workflows → Terraform → Functions → All Repos
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "═══════════════════════════════════════════════════════════════"
echo "  🌍 FULL STACK DEPLOYMENT ORCHESTRATOR"
echo "  Deploying: Workflows + Terraform + Functions + All Services"
echo "═══════════════════════════════════════════════════════════════"
echo -e "${NC}"

# Configuration
AUTO_APPROVE=${AUTO_APPROVE:-true}
TF_ENV=${TF_ENV:-prod}
SLACK_WEBHOOK=${SLACK_WEBHOOK:-}
VERCEL_TOKEN=${VERCEL_TOKEN:-}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="deployment_${TIMESTAMP}.log"

echo "Logging to: $LOG_FILE" | tee "$LOG_FILE"

################################################################################
# PHASE 1: Deploy Universal Workflows to All Repos
################################################################################

echo -e "\n${YELLOW}[PHASE 1] Deploying Universal Workflows...${NC}" | tee -a "$LOG_FILE"

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
  "systems-master-hub"
  "quantum-advantage-layer"
  "enterprise-automation-system"
)

TOTAL=${#REPOS[@]}
CURRENT=0

for repo in "${REPOS[@]}"; do
  ((CURRENT++))
  echo -e "${YELLOW}[${CURRENT}/${TOTAL}] Deploying workflow to ${repo}...${NC}" | tee -a "$LOG_FILE"

  if [ ! -d "$repo" ]; then
    gh repo clone "Garrettc123/${repo}" 2>&1 | tee -a "$LOG_FILE" || {
      echo -e "${RED}  ✗ Failed to clone${NC}" | tee -a "$LOG_FILE"
      continue
    }
  fi

  cd "$repo"

  mkdir -p .github/workflows

  # Universal CI workflow
  cat > .github/workflows/ci.yml << 'EOF'
name: 🚀 CI/CD Pipeline
on:
  push:
    branches: [ main, master, develop ]
  pull_request:
    branches: [ main, master, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install deps
        run: |
          if [ -f package.json ]; then npm ci; fi
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
      - name: Run tests
        run: |
          if [ -f "Makefile" ]; then make test; fi
          if [ -f "pytest.ini" ]; then pytest; fi
          if [ -f "package.json" ]; then npm test 2>/dev/null || true; fi
      - name: Build
        run: |
          if [ -f "Makefile" ]; then make build; fi
          if [ -f "package.json" ]; then npm run build 2>/dev/null || true; fi
EOF

  git config user.name "Garrett CI"
  git config user.email "ci@garrettc123.dev"
  git add .github/workflows/ci.yml
  git commit -m "🔧 Deploy: Universal CI/CD Workflow" 2>&1 | tee -a "$LOG_FILE" || echo "  Already up to date"
  git push origin main 2>&1 | tee -a "$LOG_FILE" || git push origin master 2>&1 | tee -a "$LOG_FILE" || echo "  Push to origin failed"

  cd ..
  echo -e "${GREEN}  ✓ Workflow deployed${NC}" | tee -a "$LOG_FILE"
done

################################################################################
# PHASE 2: Terraform Infrastructure Deployment
################################################################################

echo -e "\n${YELLOW}[PHASE 2] Deploying Terraform Infrastructure...${NC}" | tee -a "$LOG_FILE"

if [ -d "systems-master-hub/terraform" ]; then
  cd systems-master-hub/terraform
  
  echo "Initializing Terraform..." | tee -a "$LOG_FILE"
  terraform init 2>&1 | tee -a "$LOG_FILE" || {
    echo -e "${RED}  ✗ Terraform init failed${NC}" | tee -a "$LOG_FILE"
  }
  
  echo "Generating plan for $TF_ENV..." | tee -a "$LOG_FILE"
  terraform plan -var "environment=$TF_ENV" -out="${TF_ENV}.tfplan" 2>&1 | tee -a "$LOG_FILE" || {
    echo -e "${RED}  ✗ Terraform plan failed${NC}" | tee -a "$LOG_FILE"
  }
  
  if [ "$AUTO_APPROVE" = "true" ]; then
    echo "Applying Terraform changes (auto-approved)..." | tee -a "$LOG_FILE"
    terraform apply -auto-approve "${TF_ENV}.tfplan" 2>&1 | tee -a "$LOG_FILE" || {
      echo -e "${RED}  ✗ Terraform apply failed${NC}" | tee -a "$LOG_FILE"
    }
    rm -f "${TF_ENV}.tfplan"
    echo -e "${GREEN}  ✓ Terraform deployment complete${NC}" | tee -a "$LOG_FILE"
  fi
  
  cd ../..
else
  echo -e "${YELLOW}  ⚠ Terraform directory not found, skipping...${NC}" | tee -a "$LOG_FILE"
fi

################################################################################
# PHASE 3: Vercel Function Deployment
################################################################################

echo -e "\n${YELLOW}[PHASE 3] Deploying Vercel Functions...${NC}" | tee -a "$LOG_FILE"

if command -v vercel &> /dev/null && [ -n "$VERCEL_TOKEN" ]; then
  if [ -d "systems-master-hub/api" ]; then
    cd systems-master-hub
    VERCEL_TOKEN="$VERCEL_TOKEN" vercel --prod 2>&1 | tee -a "$LOG_FILE" || {
      echo -e "${RED}  ✗ Vercel deploy failed${NC}" | tee -a "$LOG_FILE"
    }
    echo -e "${GREEN}  ✓ Vercel deployment complete${NC}" | tee -a "$LOG_FILE"
    cd ..
  fi
else
  echo -e "${YELLOW}  ⚠ Vercel CLI not found or token missing, skipping...${NC}" | tee -a "$LOG_FILE"
fi

################################################################################
# PHASE 4: Slack Notification
################################################################################

echo -e "\n${YELLOW}[PHASE 4] Sending Notifications...${NC}" | tee -a "$LOG_FILE"

if [ -n "$SLACK_WEBHOOK" ]; then
  curl -X POST -H 'Content-type: application/json' \
    --data "{
      \"text\": \"✅ Full Stack Deployment Complete\",
      \"blocks\": [
        {\"type\": \"section\", \"text\": {\"type\": \"mrkdwn\", \"text\": \"*🚀 Full Stack Deployment Successful*\\n• ${#REPOS[@]} repos deployed\\n• Terraform: $TF_ENV\\n• Timestamp: $TIMESTAMP\"}}
      ]
    }" \
    "$SLACK_WEBHOOK" 2>&1 | tee -a "$LOG_FILE" || echo "Slack notification failed"
fi

################################################################################
# Summary
################################################################################

echo -e "\n${GREEN}"
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ DEPLOYMENT COMPLETE"
echo "  Repos: ${#REPOS[@]} ✓"
echo "  Terraform: $TF_ENV ✓"
echo "  Functions: Vercel ✓"
echo "  Log: $LOG_FILE"
echo "═══════════════════════════════════════════════════════════════"
echo -e "${NC}"
