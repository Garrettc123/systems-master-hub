#!/bin/bash
# Garcar Enterprise — Wealth Loop Verification Script
# Run from Termux: bash scripts/verify_wealth_loop.sh

RAILWAY_URL=${RAILWAY_URL:-"https://YOUR-RAILWAY-URL.up.railway.app"}
ZEUS_URL=${ZEUS_URL:-"https://YOUR-ZEUS-URL.vercel.app"}

echo "====================================="
echo " GARCAR WEALTH LOOP VERIFICATION"
echo " $(date)"
echo "====================================="

# 1. Stripe webhook endpoint
echo ""
echo "[1/4] Testing Stripe webhook endpoint..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$RAILWAY_URL/webhooks/stripe" \
  -H 'Content-Type: application/json' -d '{}')
if [ "$STATUS" = "400" ] || [ "$STATUS" = "401" ]; then
  echo "    ✅ Webhook endpoint LIVE (returned $STATUS — signature check active)"
else
  echo "    ❌ Webhook endpoint issue (returned $STATUS)"
fi

# 2. Payment server health
echo ""
echo "[2/4] Testing garcar-payments health..."
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$RAILWAY_URL/health")
if [ "$HEALTH" = "200" ]; then
  echo "    ✅ Payment server HEALTHY"
else
  echo "    ❌ Payment server DOWN (returned $HEALTH)"
fi

# 3. Zeus MRR endpoint
echo ""
echo "[3/4] Checking Zeus MRR..."
MRR=$(curl -s "$ZEUS_URL/api/revenue/mrr" 2>/dev/null)
if echo "$MRR" | grep -q 'mrr'; then
  echo "    ✅ Zeus MRR endpoint LIVE: $MRR"
else
  echo "    ❌ Zeus MRR endpoint not responding"
fi

# 4. GitHub Actions status hint
echo ""
echo "[4/4] GitHub Actions — check manually:"
echo "    https://github.com/Garrettc123/garcar-payments/actions"
echo "    https://github.com/Garrettc123/garcar-autonomous-wealth-system/actions"
echo "    https://github.com/Garrettc123/autonomous-income-deployment/actions"

echo ""
echo "====================================="
echo " Verification complete"
echo "====================================="
