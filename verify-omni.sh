#!/usr/bin/env bash
################################################################################
# Omnibus Deployment Verification Script
# Tests that all components are correctly configured
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔍 Verifying Omnibus Deployment Configuration..."
echo ""

ERRORS=0

# Test 1: Check if run-all-omni.sh exists and is executable
echo -n "✓ Checking run-all-omni.sh... "
if [ -x "./run-all-omni.sh" ]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC} - Script not found or not executable"
    ERRORS=$((ERRORS + 1))
fi

# Test 2: Check if docker-compose.yml exists
echo -n "✓ Checking docker-compose.yml... "
if [ -f "./docker-compose.yml" ]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC} - docker-compose.yml not found"
    ERRORS=$((ERRORS + 1))
fi

# Test 3: Validate docker-compose.yml syntax
echo -n "✓ Validating docker-compose.yml syntax... "
if docker compose config > /dev/null 2>&1; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC} - Invalid docker-compose.yml syntax"
    ERRORS=$((ERRORS + 1))
fi

# Test 4: Check Makefile targets
echo -n "✓ Checking Makefile omni target... "
if grep -q "^omni:" Makefile 2>/dev/null; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC} - omni target not found in Makefile"
    ERRORS=$((ERRORS + 1))
fi

# Test 5: Check for required directories
echo -n "✓ Checking folder structure... "
REQUIRED_DIRS=(
    "01-core-infrastructure"
    "02-ai-ml-platforms"
    "03-protocols-blockchain"
    "10-monitoring-observability"
)
DIR_MISSING=0
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        DIR_MISSING=1
    fi
done

if [ $DIR_MISSING -eq 0 ]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${YELLOW}WARN${NC} - Some directories will be created on first run"
fi

# Test 6: Check Docker daemon
echo -n "✓ Checking Docker daemon... "
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC} - Docker daemon not running"
    ERRORS=$((ERRORS + 1))
fi

# Test 7: Check disk space
echo -n "✓ Checking disk space... "
AVAILABLE=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$AVAILABLE" -gt 10 ]; then
    echo -e "${GREEN}PASS${NC} (${AVAILABLE}GB available)"
else
    echo -e "${YELLOW}WARN${NC} - Low disk space: ${AVAILABLE}GB (10GB+ recommended)"
fi

# Test 8: Verify omnibus script syntax
echo -n "✓ Validating run-all-omni.sh syntax... "
if bash -n ./run-all-omni.sh 2>/dev/null; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC} - Script has syntax errors"
    ERRORS=$((ERRORS + 1))
fi

# Test 9: Check if OMNI-README.md exists
echo -n "✓ Checking documentation... "
if [ -f "./OMNI-README.md" ]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${YELLOW}WARN${NC} - OMNI-README.md not found"
fi

# Test 10: Check for logs directory in gitignore
echo -n "✓ Checking .gitignore configuration... "
if grep -q "logs/" .gitignore 2>/dev/null; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${YELLOW}WARN${NC} - logs/ not in .gitignore"
fi

echo ""
echo "════════════════════════════════════════════════════"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All critical tests passed!${NC}"
    echo ""
    echo "Ready to deploy with:"
    echo "  make omni"
    echo ""
    exit 0
else
    echo -e "${RED}❌ $ERRORS critical test(s) failed${NC}"
    echo ""
    echo "Please fix the errors before deploying."
    echo ""
    exit 1
fi
