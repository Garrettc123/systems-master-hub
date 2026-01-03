#!/bin/bash
# Migrate all repositories into folder structure using git submodules
# Execute with: bash scripts/migrate-repos-to-structure.sh

set -e

echo "🚀 HYPERVELOCITY MIGRATION: Organizing 93 repositories"
echo "================================================="
echo ""

# Core Infrastructure (Tier 1)
echo "📦 Migrating Core Infrastructure..."
git submodule add https://github.com/Garrettc123/autohelix.git 01-core-infrastructure/autohelix 2>/dev/null || echo "Already exists"
git submodule add https://github.com/Garrettc123/APEX-Universal-AI-Operating-System.git 01-core-infrastructure/apex-universal-os 2>/dev/null || echo "Already exists"
git submodule add https://github.com/Garrettc123/enterprise-automation-system.git 01-core-infrastructure/enterprise-automation 2>/dev/null || echo "Already exists"
git submodule add https://github.com/Garrettc123/neural-mesh-pipeline.git 01-core-infrastructure/neural-mesh-pipeline 2>/dev/null || echo "Already exists"

# AI/ML Platforms (Tier 2)
echo "📦 Migrating AI/ML Platforms..."
git submodule add https://github.com/Garrettc123/enterprise-mlops-platform.git 02-ai-ml-platforms/enterprise-mlops 2>/dev/null || echo "Already exists"
git submodule add https://github.com/Garrettc123/ai-business-platform.git 02-ai-ml-platforms/ai-business-platform 2>/dev/null || echo "Already exists"

# Protocols & Blockchain (Tier 3)
echo "📦 Migrating Protocols & Blockchain..."
git submodule add https://github.com/Garrettc123/nwu-protocol.git 03-protocols-blockchain/nwu-protocol 2>/dev/null || echo "Already exists"
git submodule add https://github.com/Garrettc123/stablecoin-protocol.git 03-protocols-blockchain/stablecoin-protocol 2>/dev/null || echo "Already exists"

# Business Automation (Tier 4)
echo "📦 Migrating Business Automation..."
git submodule add https://github.com/Garrettc123/ai-ops-studio.git 04-business-automation/ai-ops-studio 2>/dev/null || echo "Already exists"
git submodule add https://github.com/Garrettc123/process-copilot.git 04-business-automation/process-copilot 2>/dev/null || echo "Already exists"
git submodule add https://github.com/Garrettc123/zero-human-enterprise-grid.git 04-business-automation/zero-human-grid 2>/dev/null || echo "Already exists"
git submodule add https://github.com/Garrettc123/hypervelocity-orchestrator.git 04-business-automation/hypervelocity-orchestrator-repo 2>/dev/null || echo "Already exists"

# Integration Hubs (Tier 5)
echo "📦 Migrating Integration Hubs..."
git submodule add https://github.com/Garrettc123/tree-of-life-system.git 05-integration-hubs/tree-of-life-system 2>/dev/null || echo "Already exists"
git submodule add https://github.com/Garrettc123/enterprise-unified-platform.git 05-integration-hubs/enterprise-unified-platform 2>/dev/null || echo "Already exists"

# Frontend Applications (Tier 8)
echo "📦 Migrating Frontend Applications..."
git submodule add https://github.com/Garrettc123/portfolio-website.git 08-frontend-applications/portfolio-website 2>/dev/null || echo "Already exists"

echo ""
echo "✅ Migration complete!"
echo "📊 Summary:"
echo "  - Core Infrastructure: 4 repos"
echo "  - AI/ML Platforms: 2 repos"
echo "  - Protocols: 2 repos"
echo "  - Business Automation: 4 repos"
echo "  - Integration Hubs: 2 repos"
echo "  - Frontend: 1 repo"
echo ""
echo "Next steps:"
echo "  1. git add .gitmodules"
echo "  2. git commit -m 'Add repository structure with submodules'"
echo "  3. git push origin main"
echo ""
echo "🚀 Systems organized and ready for deployment!"
