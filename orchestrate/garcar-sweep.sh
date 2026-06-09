#!/usr/bin/env bash
# ============================================================
# GARCAR ENTERPRISE — SINGLE COMMAND ALL-IN-ONE SWEEP
# Usage: ./orchestrate/garcar-sweep.sh [full|payments|health|deploy]
# Requires: GITHUB_TOKEN in env or ~/.env.master
# ============================================================
set -euo pipefail

MODE="${1:-full}"
OWNER="Garrettc123"
REPO="systems-master-hub"
WORKFLOW="garcar-all-in-one-sweep.yml"
BRANCH="main"

# ── Load secrets from .env.master if present ──────────────────
if [[ -f "${HOME}/.env.master" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${HOME}/.env.master"
  set +a
  echo "🔑 Loaded secrets from ~/.env.master"
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "❌ GITHUB_TOKEN not set. Add it to ~/.env.master or export it."
  exit 1
fi

echo ""
echo "🚀 GARCAR ALL-IN-ONE SWEEP"
echo "   Mode   : ${MODE}"
echo "   Target : ${OWNER}/${REPO}"
echo "   Workflow: ${WORKFLOW}"
echo "   Time   : $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "────────────────────────────────────────────────────────────"

# ── Trigger workflow dispatch ─────────────────────────────────
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}/dispatches" \
  -d "{\"ref\":\"${BRANCH}\",\"inputs\":{\"mode\":\"${MODE}\"}}")

if [[ "${RESPONSE}" == "204" ]]; then
  echo "✅ Sweep triggered successfully (HTTP 204)"
  echo ""
  echo "📊 Monitor at:"
  echo "   https://github.com/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}"
else
  echo "❌ Trigger failed (HTTP ${RESPONSE})"
  echo "   Check GITHUB_TOKEN permissions (needs: actions:write, repo scope)"
  exit 1
fi

# ── Optional: run local status check ─────────────────────────
if command -v python3 &>/dev/null; then
  echo ""
  echo "🔍 Running local status check..."
  sleep 5
  GITHUB_TOKEN="${GITHUB_TOKEN}" python3 orchestrate/sweep-status.py
fi

echo ""
echo "🎯 Sweep complete. All 8 revenue systems dispatched."
echo "   Issue ledger will be auto-created in systems-master-hub."
