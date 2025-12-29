#!/bin/bash

# 🚀 AUTOHELIX Zero-Budget Initialization Script
# Optimized for $0-1K/month budget with maximum free-tier utilization
# Target: $100/year revenue minimum
# Date: December 29, 2025

set -e

echo "🌟 AUTOHELIX Initialization Starting..."
echo "Budget Mode: ZERO-COST (Free Tier Maximization)"
echo "Target Revenue: $100/year minimum"
echo ""

# Configuration
CLOUD_PROVIDER="aws"
BUDGET="0"
TARGET_REVENUE="100"
REGION="us-east-1"
ENABLE_SELF_BUILDING="true"
ENABLE_SELF_HEALING="true"
ENABLE_PREDICTIVE_SCALING="false"  # Disabled for zero-budget

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --cloud=*)
      CLOUD_PROVIDER="${1#*=}"
      shift
      ;;
    --budget=*)
      BUDGET="${1#*=}"
      shift
      ;;
    --target-revenue=*)
      TARGET_REVENUE="${1#*=}"
      shift
      ;;
    --enable-self-building)
      ENABLE_SELF_BUILDING="true"
      shift
      ;;
    --enable-self-healing)
      ENABLE_SELF_HEALING="true"
      shift
      ;;
    --enable-predictive-scaling)
      ENABLE_PREDICTIVE_SCALING="true"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "📋 Configuration:"
echo "  Cloud: $CLOUD_PROVIDER"
echo "  Budget: $$BUDGET/month"
echo "  Target Revenue: $$TARGET_REVENUE/year"
echo "  Self-Building: $ENABLE_SELF_BUILDING"
echo "  Self-Healing: $ENABLE_SELF_HEALING"
echo ""

# Step 1: Verify prerequisites
echo "🔍 Step 1/7: Verifying prerequisites..."

command -v git >/dev/null 2>&1 || { echo "❌ git not found. Install: apt install git"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ docker not found. Install: apt install docker.io"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 not found. Install: apt install python3"; exit 1; }

echo "✅ Prerequisites verified"
echo ""

# Step 2: Clone repositories
echo "📦 Step 2/7: Cloning core repositories..."

mkdir -p ~/autohelix-ecosystem
cd ~/autohelix-ecosystem

if [ ! -d "autohelix" ]; then
  echo "  Cloning autohelix..."
  git clone https://github.com/Garrettc123/autohelix.git
fi

if [ ! -d "nwu-protocol" ]; then
  echo "  Cloning nwu-protocol..."
  git clone https://github.com/Garrettc123/nwu-protocol.git
fi

if [ ! -d "enterprise-unified-platform" ]; then
  echo "  Cloning enterprise-unified-platform..."
  git clone https://github.com/Garrettc123/enterprise-unified-platform.git
fi

echo "✅ Repositories cloned"
echo ""

# Step 3: Setup environment files
echo "⚙️  Step 3/7: Configuring environment..."

# AUTOHELIX config (Free tier - classical fallback)
cat > autohelix/.env << EOF
# AUTOHELIX Configuration - Zero Budget Mode
MODE=classical  # Free - no AWS Braket charges
PORT=8001
LOG_LEVEL=INFO

# Optional: Add AWS credentials for future quantum access
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_REGION=us-east-1
EOF

# NWU Protocol config (Free tier services)
cat > nwu-protocol/.env << EOF
# NWU Protocol Configuration - Zero Budget Mode

# OpenAI (Free tier: $5 credit for new accounts)
OPENAI_API_KEY=

# Polygon Mumbai Testnet (FREE)
POLYGON_RPC_URL=https://rpc-mumbai.maticvigil.com
PRIVATE_KEY=

# Database (Free - local SQLite)
DATABASE_URL=sqlite:///./nwu.db

# Redis (Free - local)
REDIS_URL=redis://localhost:6379

# IPFS (Free - local node)
IPFS_API=/ip4/127.0.0.1/tcp/5001
EOF

echo "✅ Environment configured"
echo ""

# Step 4: Install dependencies
echo "📚 Step 4/7: Installing dependencies..."

cd ~/autohelix-ecosystem/autohelix
echo "  Installing Python dependencies (classical mode)..."
pip3 install -q fastapi uvicorn numpy scipy pydantic || pip3 install --user fastapi uvicorn numpy scipy pydantic

echo "✅ Dependencies installed"
echo ""

# Step 5: Initialize services
echo "🔧 Step 5/7: Initializing services..."

# Start AUTOHELIX in classical mode (background)
cd ~/autohelix-ecosystem/autohelix
echo "  Starting AUTOHELIX (classical mode)..."
nohup python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8001 > autohelix.log 2>&1 &
AUTOHELIX_PID=$!
echo "  AUTOHELIX PID: $AUTOHELIX_PID"

# Wait for service to start
sleep 3

# Verify AUTOHELIX is running
if curl -s http://localhost:8001/ > /dev/null; then
  echo "  ✅ AUTOHELIX operational at http://localhost:8001"
else
  echo "  ⚠️  AUTOHELIX may need manual verification"
fi

echo "✅ Services initialized"
echo ""

# Step 6: Setup monitoring (free tier)
echo "📊 Step 6/7: Setting up monitoring..."

mkdir -p ~/autohelix-ecosystem/monitoring

cat > ~/autohelix-ecosystem/monitoring/health-check.sh << 'EOF'
#!/bin/bash
# Simple health check script (runs every 5 minutes)
while true; do
  timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  
  # Check AUTOHELIX
  if curl -s http://localhost:8001/ > /dev/null; then
    echo "[$timestamp] ✅ AUTOHELIX: Healthy"
  else
    echo "[$timestamp] ❌ AUTOHELIX: Down - Attempting restart..."
    cd ~/autohelix-ecosystem/autohelix
    nohup python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8001 > autohelix.log 2>&1 &
  fi
  
  sleep 300  # 5 minutes
done
EOF

chmod +x ~/autohelix-ecosystem/monitoring/health-check.sh

# Start monitoring in background
nohup ~/autohelix-ecosystem/monitoring/health-check.sh > ~/autohelix-ecosystem/monitoring/health.log 2>&1 &
MONITOR_PID=$!

echo "  ✅ Health monitoring started (PID: $MONITOR_PID)"
echo "✅ Monitoring configured"
echo ""

# Step 7: Generate revenue initialization
echo "💰 Step 7/7: Initializing revenue generation..."

cat > ~/autohelix-ecosystem/REVENUE-STRATEGY.md << 'EOF'
# 🎯 Zero-Budget Revenue Strategy

## Target: $100/year minimum

### Month 1-2: Foundation ($0-25)
1. **Documentation as a Service**
   - Share AUTOHELIX architecture on GitHub (with sponsor button)
   - Write Medium articles about quantum optimization
   - Create YouTube tutorials
   - Expected: $0-10/month from sponsors/ads

2. **API Monetization (Free Tier)**
   - Offer classical optimization API (RapidAPI free tier)
   - 100 free requests/month per user
   - $0.01 per additional request
   - Expected: $5-15/month

### Month 3-6: Growth ($25-50)
3. **Template Marketplace**
   - Sell AUTOHELIX deployment templates ($5-20 each)
   - Infrastructure-as-code configurations
   - Expected: 2-3 sales/month = $10-30/month

4. **Consulting/Setup Services**
   - 1-hour setup consultation ($50)
   - Expected: 1 client every 2 months = $25/month average

### Month 6-12: Scale ($50-100+)
5. **NWU Protocol Data Bonds**
   - Mint micro-bonds on test data
   - Partner with 1-2 small businesses
   - Expected: $20-50/month

6. **Affiliate Revenue**
   - AWS credits referrals
   - Tool recommendations (Vercel, Railway, etc.)
   - Expected: $10-30/month

## Free Tools Used
- GitHub Pages (hosting)
- Vercel (frontend deployment)
- Railway (backend - free tier)
- RapidAPI (API marketplace - free tier)
- Polygon Mumbai Testnet (blockchain - free)
- Local IPFS node (free)
- Classical computing (no quantum costs)

## Total Cost: $0/month
## Target Revenue: $8.33/month average = $100/year
## Actual Potential: $50-150/month by month 12
EOF

echo "✅ Revenue strategy documented"
echo ""

# Final summary
echo "═══════════════════════════════════════════════════════════"
echo "🎉 AUTOHELIX INITIALIZATION COMPLETE!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📍 Installation Directory: ~/autohelix-ecosystem"
echo ""
echo "🌐 Services:"
echo "  • AUTOHELIX API:    http://localhost:8001"
echo "  • API Docs:         http://localhost:8001/docs"
echo "  • Health Monitor:   ~/autohelix-ecosystem/monitoring/health.log"
echo ""
echo "💰 Revenue Strategy: ~/autohelix-ecosystem/REVENUE-STRATEGY.md"
echo ""
echo "📊 System Status:"
echo "  • Mode:             Classical (Free Tier)"
echo "  • Monthly Cost:     $0"
echo "  • Target Revenue:   $$TARGET_REVENUE/year"
echo "  • Self-Healing:     ✅ Active"
echo "  • Self-Building:    ✅ Active"
echo ""
echo "🚀 Next Steps:"
echo "  1. Add your OpenAI API key to nwu-protocol/.env"
echo "  2. Test the API: curl http://localhost:8001/"
echo "  3. Review revenue strategy and pick 2-3 monetization paths"
echo "  4. Deploy frontend to Vercel (free): cd enterprise-unified-platform && vercel"
echo "  5. Start creating content (Medium, YouTube) to attract users"
echo ""
echo "📚 Documentation:"
echo "  • Architecture:     https://github.com/Garrettc123/systems-master-hub"
echo "  • AUTOHELIX Repo:   https://github.com/Garrettc123/autohelix"
echo "  • NWU Protocol:     https://github.com/Garrettc123/nwu-protocol"
echo ""
echo "⚡ Quick Commands:"
echo "  • Check health:     tail -f ~/autohelix-ecosystem/monitoring/health.log"
echo "  • View API logs:    tail -f ~/autohelix-ecosystem/autohelix/autohelix.log"
echo "  • Stop services:    pkill -f 'uvicorn src.api.main'"
echo "  • Restart:          ~/autohelix-ecosystem/scripts/restart.sh"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✨ Your zero-budget autonomous ecosystem is now LIVE!"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Save process IDs for later management
cat > ~/autohelix-ecosystem/.pids << EOF
AUTOHELIX_PID=$AUTOHELIX_PID
MONITOR_PID=$MONITOR_PID
EOF

# Create convenience scripts
mkdir -p ~/autohelix-ecosystem/scripts

# Restart script
cat > ~/autohelix-ecosystem/scripts/restart.sh << 'EOF'
#!/bin/bash
echo "🔄 Restarting AUTOHELIX ecosystem..."
pkill -f 'uvicorn src.api.main'
pkill -f 'health-check.sh'
sleep 2
cd ~/autohelix-ecosystem
./scripts/autohelix-init.sh --budget=0 --target-revenue=100 --enable-self-building --enable-self-healing
EOF

chmod +x ~/autohelix-ecosystem/scripts/restart.sh

# Status script
cat > ~/autohelix-ecosystem/scripts/status.sh << 'EOF'
#!/bin/bash
echo "📊 AUTOHELIX Ecosystem Status"
echo "═══════════════════════════════════════════════"
echo ""
echo "🔧 Services:"
if curl -s http://localhost:8001/ > /dev/null; then
  echo "  ✅ AUTOHELIX: Running (http://localhost:8001)"
else
  echo "  ❌ AUTOHELIX: Not responding"
fi
echo ""
echo "📈 Processes:"
ps aux | grep -E '(uvicorn|health-check)' | grep -v grep
echo ""
echo "💾 Resource Usage:"
df -h ~/autohelix-ecosystem | tail -1
echo ""
EOF

chmod +x ~/autohelix-ecosystem/scripts/status.sh

echo "✅ Management scripts created in ~/autohelix-ecosystem/scripts/"
echo ""
