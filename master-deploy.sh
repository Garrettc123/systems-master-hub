#!/usr/bin/env bash
################################################################################
# 🚀 SYSTEMS MASTER HUB — Master Deploy Script
# Triggers deployments across all major repositories
#
# Usage:
#   ./master-deploy.sh                       # Deploy all repos
#   ./master-deploy.sh --repo <name>         # Deploy single repo
#   ./master-deploy.sh --workflow <file>     # Target specific workflow file
#   ./master-deploy.sh --dry-run             # Print actions without executing
#
# Requires:
#   GITHUB_TOKEN env var with repo/workflow scopes
################################################################################

set -euo pipefail

# ── Colors ─────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Config ─────────────────────────────────────────────────────────────────────
OWNER="Garrettc123"
API_BASE="https://api.github.com"
DEFAULT_WORKFLOW="ci.yml"   # Workflow file to trigger (workflow_dispatch)
BRANCH="${BRANCH:-main}"
DRY_RUN=false
SPECIFIC_REPO=""
SPECIFIC_WORKFLOW=""
DEPLOY_LOG="./logs/master-deploy-$(date +%Y%m%d_%H%M%S).log"

# ── Verify token ───────────────────────────────────────────────────────────────
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    echo -e "${RED}ERROR: GITHUB_TOKEN is not set.${NC}"
    echo "  Export a personal access token with 'repo' and 'workflow' scopes:"
    echo "    export GITHUB_TOKEN=ghp_..."
    exit 1
fi

AUTH_HEADER="Authorization: Bearer ${GITHUB_TOKEN}"

# ── Repositories + their preferred deploy workflow ────────────────────────────
# Format: "repo_name:workflow_file"
# Use "dispatch" as the workflow file to trigger a repository_dispatch event
declare -A REPO_WORKFLOWS=(
    ["systems-master-hub"]="auto-deploy-all-systems.yml"
    ["APEX-Universal-AI-Operating-System"]="ci.yml"
    ["autohelix"]="ci.yml"
    ["enterprise-mlops-platform"]="ci.yml"
    ["nwu-protocol"]="ci.yml"
    ["enterprise-unified-platform"]="ci.yml"
    ["ai-business-platform"]="ci.yml"
    ["zero-human-enterprise-grid"]="ci.yml"
    ["hypervelocity-orchestrator"]="ci.yml"
    ["process-copilot"]="ci.yml"
    ["ai-ops-studio"]="ci.yml"
    ["tree-of-life-system"]="ci.yml"
    ["portfolio-website"]="ci.yml"
    ["zero-human-governance-core"]="ci.yml"
    ["zero-human-ai-platform"]="ci.yml"
    ["neural-mesh-pipeline"]="ci.yml"
    ["stablecoin-protocol"]="ci.yml"
    ["nexusai-platform"]="ci.yml"
)

# ── Parse args ─────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo)       SPECIFIC_REPO="$2";     shift 2 ;;
        --workflow)   SPECIFIC_WORKFLOW="$2"; shift 2 ;;
        --branch)     BRANCH="$2";            shift 2 ;;
        --dry-run)    DRY_RUN=true;           shift ;;
        --help|-h)
            sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Helpers ────────────────────────────────────────────────────────────────────
mkdir -p "$(dirname "$DEPLOY_LOG")"

log() {
    local msg="[$(date +'%H:%M:%S')] $*"
    echo -e "$msg" | tee -a "$DEPLOY_LOG"
}

gh_post() {
    local url="$1"
    local data="$2"
    curl -sf -X POST \
        -H "$AUTH_HEADER" \
        -H "Accept: application/vnd.github+json" \
        -H "Content-Type: application/json" \
        -d "$data" \
        "$url" 2>/dev/null
}

gh_get() {
    curl -sf -H "$AUTH_HEADER" -H "Accept: application/vnd.github+json" "$1" 2>/dev/null || echo "null"
}

trigger_workflow() {
    local repo="$1"
    local workflow="$2"
    local branch="${3:-$BRANCH}"

    local url="${API_BASE}/repos/${OWNER}/${repo}/actions/workflows/${workflow}/dispatches"
    local data="{\"ref\":\"${branch}\"}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "${YELLOW}[DRY-RUN]${NC} Would trigger ${repo} / ${workflow} @ ${branch}"
        return 0
    fi

    local http_status
    http_status=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST \
        -H "$AUTH_HEADER" \
        -H "Accept: application/vnd.github+json" \
        -H "Content-Type: application/json" \
        -d "$data" \
        "$url")

    if [[ "$http_status" == "204" ]]; then
        log "${GREEN}✅ Triggered${NC} ${BOLD}${repo}${NC} / ${workflow} @ ${branch}"
        return 0
    elif [[ "$http_status" == "404" ]]; then
        log "${YELLOW}⚠️  Workflow not found${NC}: ${repo} / ${workflow} — skipping"
        return 1
    elif [[ "$http_status" == "422" ]]; then
        log "${YELLOW}⚠️  Workflow not dispatchable${NC}: ${repo} / ${workflow} — skipping"
        return 1
    else
        log "${RED}❌ Failed${NC} ${repo} / ${workflow} (HTTP ${http_status})"
        return 1
    fi
}

trigger_repository_dispatch() {
    local repo="$1"
    local event_type="${2:-deploy}"

    local url="${API_BASE}/repos/${OWNER}/${repo}/dispatches"
    local data="{\"event_type\":\"${event_type}\"}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "${YELLOW}[DRY-RUN]${NC} Would send repository_dispatch '${event_type}' to ${repo}"
        return 0
    fi

    local http_status
    http_status=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST \
        -H "$AUTH_HEADER" \
        -H "Accept: application/vnd.github+json" \
        -H "Content-Type: application/json" \
        -d "$data" \
        "$url")

    if [[ "$http_status" == "204" ]]; then
        log "${GREEN}✅ Dispatched${NC} ${BOLD}${repo}${NC} (event: ${event_type})"
        return 0
    else
        log "${RED}❌ Dispatch failed${NC}: ${repo} (HTTP ${http_status})"
        return 1
    fi
}

deploy_repo() {
    local repo="$1"
    local workflow="${SPECIFIC_WORKFLOW:-${REPO_WORKFLOWS[$repo]:-$DEFAULT_WORKFLOW}}"

    # Check repo exists first
    local repo_data
    repo_data=$(gh_get "${API_BASE}/repos/${OWNER}/${repo}")
    if [[ "$repo_data" == "null" ]]; then
        log "${YELLOW}⚠️  Repo not found or private${NC}: ${repo} — skipping"
        return 1
    fi

    local default_branch
    default_branch=$(echo "$repo_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('default_branch','main'))" 2>/dev/null || echo "main")
    local target_branch="${BRANCH:-$default_branch}"

    trigger_workflow "$repo" "$workflow" "$target_branch"
}

# ── Banner ─────────────────────────────────────────────────────────────────────
echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       🚀 SYSTEMS MASTER HUB — MASTER DEPLOY                 ║"
echo "║           github.com/${OWNER}                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
[[ "$DRY_RUN" == "true" ]] && echo -e "  ${YELLOW}DRY-RUN MODE — no actual deployments will be triggered${NC}\n"
echo "  Started: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "  Log:     ${DEPLOY_LOG}"
echo ""

# ── Run deployments ────────────────────────────────────────────────────────────
PASS=0
FAIL=0
SKIP=0

if [[ -n "$SPECIFIC_REPO" ]]; then
    deploy_repo "$SPECIFIC_REPO" && PASS=$((PASS+1)) || FAIL=$((FAIL+1))
else
    for repo in "${!REPO_WORKFLOWS[@]}"; do
        deploy_repo "$repo" && PASS=$((PASS+1)) || FAIL=$((FAIL+1))
        # Brief pause to respect GitHub rate limits
        sleep 0.5
    done
fi

# ── Summary ────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${BOLD}Deployment Summary${NC}"
echo "  ─────────────────────────────────────────"
printf "  %-28s ${GREEN}%d${NC}\n" "Triggered successfully:" "$PASS"
printf "  %-28s ${RED}%d${NC}\n"   "Failed / skipped:"       "$FAIL"
echo ""
echo -e "  Monitor progress at: ${CYAN}https://github.com/${OWNER}?tab=repositories${NC}"
echo ""

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
