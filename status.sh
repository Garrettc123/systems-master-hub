#!/usr/bin/env bash
################################################################################
# 📊 SYSTEMS MASTER HUB - Live Status Dashboard
# Queries GitHub API to show health/CI status of all major repos
#
# Usage:
#   ./status.sh                    # Show status of all repos
#   ./status.sh --repo <name>      # Show status of a specific repo
#   ./status.sh --format json      # Output in JSON format
#   GITHUB_TOKEN=<token> ./status.sh   # Authenticated (higher rate limits)
################################################################################

set -euo pipefail

# ── Color codes ────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Configuration ──────────────────────────────────────────────────────────────
OWNER="Garrettc123"
API_BASE="https://api.github.com"
FORMAT="${FORMAT:-table}"
SPECIFIC_REPO=""

# Auth header (optional – avoids 60 req/hr anonymous limit)
AUTH_HEADER=""
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    AUTH_HEADER="Authorization: Bearer ${GITHUB_TOKEN}"
fi

# ── Repository list ────────────────────────────────────────────────────────────
REPOS=(
    "systems-master-hub"
    "APEX-Universal-AI-Operating-System"
    "autohelix"
    "enterprise-mlops-platform"
    "nwu-protocol"
    "enterprise-unified-platform"
    "ai-business-platform"
    "zero-human-enterprise-grid"
    "hypervelocity-orchestrator"
    "process-copilot"
    "ai-ops-studio"
    "tree-of-life-system"
    "portfolio-website"
    "zero-human-governance-core"
    "zero-human-ai-platform"
    "neural-mesh-pipeline"
    "multimodal-input-api"
    "stablecoin-protocol"
    "nexusai-platform"
)

# ── Helpers ────────────────────────────────────────────────────────────────────
gh_api() {
    local url="$1"
    if [[ -n "$AUTH_HEADER" ]]; then
        curl -sf -H "$AUTH_HEADER" -H "Accept: application/vnd.github+json" "$url" 2>/dev/null || echo "null"
    else
        curl -sf -H "Accept: application/vnd.github+json" "$url" 2>/dev/null || echo "null"
    fi
}

ci_status_icon() {
    case "$1" in
        success)   echo "${GREEN}✅ passing${NC}" ;;
        failure)   echo "${RED}❌ failing${NC}" ;;
        pending)   echo "${YELLOW}⏳ pending${NC}" ;;
        no_status) echo "${BLUE}ℹ️  no CI${NC}" ;;
        *)         echo "${YELLOW}❓ ${1}${NC}" ;;
    esac
}

issues_icon() {
    local n="$1"
    if   [[ "$n" -eq 0 ]];   then echo "${GREEN}0${NC}"
    elif [[ "$n" -le 5 ]];   then echo "${YELLOW}${n}${NC}"
    else                          echo "${RED}${n}${NC}"
    fi
}

# ── Parse arguments ────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo)    SPECIFIC_REPO="$2"; shift 2 ;;
        --format)  FORMAT="$2";        shift 2 ;;
        --help|-h)
            echo "Usage: $0 [--repo <name>] [--format table|json]"
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -n "$SPECIFIC_REPO" ]]; then
    REPOS=("$SPECIFIC_REPO")
fi

# ── Banner ─────────────────────────────────────────────────────────────────────
if [[ "$FORMAT" != "json" ]]; then
    echo -e "${CYAN}${BOLD}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║       📊 SYSTEMS MASTER HUB — LIVE STATUS DASHBOARD         ║"
    echo "║           github.com/${OWNER}                    ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "  Queried at: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
    echo -e "  Auth: $([ -n "$AUTH_HEADER" ] && echo 'token (5,000 req/hr)' || echo 'anonymous (60 req/hr)')"
    echo ""
    printf "  %-42s %-10s %-8s %-12s %s\n" "REPOSITORY" "LANGUAGE" "ISSUES" "CI STATUS" "LAST PUSH"
    printf "  %-42s %-10s %-8s %-12s %s\n" "$(printf '─%.0s' {1..42})" "$(printf '─%.0s' {1..10})" "$(printf '─%.0s' {1..8})" "$(printf '─%.0s' {1..12})" "$(printf '─%.0s' {1..12})"
fi

# ── JSON array accumulator ─────────────────────────────────────────────────────
JSON_RESULTS="["
FIRST_JSON=true

# ── Per-repo status ────────────────────────────────────────────────────────────
TOTAL_ISSUES=0
PASS_COUNT=0
FAIL_COUNT=0
NO_CI_COUNT=0

for REPO in "${REPOS[@]}"; do
    # Fetch repo metadata
    REPO_DATA=$(gh_api "${API_BASE}/repos/${OWNER}/${REPO}")

    if [[ "$REPO_DATA" == "null" ]] || [[ -z "$REPO_DATA" ]]; then
        if [[ "$FORMAT" != "json" ]]; then
            printf "  %-42s ${RED}%-30s${NC}\n" "$REPO" "⚠️  not found / private"
        fi
        continue
    fi

    LANGUAGE=$(echo "$REPO_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('language') or 'N/A')" 2>/dev/null || echo "N/A")
    OPEN_ISSUES=$(echo "$REPO_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('open_issues_count', 0))" 2>/dev/null || echo "0")
    PUSHED_AT=$(echo "$REPO_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('pushed_at') or '')[:10])" 2>/dev/null || echo "unknown")
    DEFAULT_BRANCH=$(echo "$REPO_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('default_branch','main'))" 2>/dev/null || echo "main")
    DESCRIPTION=$(echo "$REPO_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('description') or '')[:80])" 2>/dev/null || echo "")

    TOTAL_ISSUES=$((TOTAL_ISSUES + OPEN_ISSUES))

    # Fetch CI status (combined commit status on default branch HEAD)
    CI_STATUS_DATA=$(gh_api "${API_BASE}/repos/${OWNER}/${REPO}/commits/${DEFAULT_BRANCH}/status")
    CI_STATE=$(echo "$CI_STATUS_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('state','no_status'))" 2>/dev/null || echo "no_status")

    # Also check check-runs (GitHub Actions)
    CHECK_RUNS_DATA=$(gh_api "${API_BASE}/repos/${OWNER}/${REPO}/commits/${DEFAULT_BRANCH}/check-runs")
    CHECK_TOTAL=$(echo "$CHECK_RUNS_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_count',0))" 2>/dev/null || echo "0")

    if [[ "$CI_STATE" == "no_status" ]] && [[ "$CHECK_TOTAL" -gt 0 ]]; then
        # Derive from check-runs
        FAILED=$(echo "$CHECK_RUNS_DATA" | python3 -c "
import sys, json
d = json.load(sys.stdin)
runs = d.get('check_runs', [])
statuses = [r.get('conclusion','') for r in runs if r.get('status') == 'completed']
if any(s in ('failure','action_required','timed_out','cancelled') for s in statuses):
    print('failure')
elif all(s == 'success' for s in statuses) and statuses:
    print('success')
else:
    print('pending')
" 2>/dev/null || echo "pending")
        CI_STATE="$FAILED"
    fi

    case "$CI_STATE" in
        success) PASS_COUNT=$((PASS_COUNT + 1)) ;;
        failure) FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
        *)       NO_CI_COUNT=$((NO_CI_COUNT + 1)) ;;
    esac

    if [[ "$FORMAT" == "json" ]]; then
        [[ "$FIRST_JSON" == "true" ]] && FIRST_JSON=false || JSON_RESULTS+=","
        JSON_RESULTS+=$(printf '{"repo":"%s","language":"%s","open_issues":%s,"ci_state":"%s","last_push":"%s","description":"%s"}' \
            "$REPO" "$LANGUAGE" "$OPEN_ISSUES" "$CI_STATE" "$PUSHED_AT" "$(echo "$DESCRIPTION" | sed 's/"/\\"/g')")
    else
        LANG_TRUNC="${LANGUAGE:0:10}"
        CI_ICON=$(ci_status_icon "$CI_STATE")
        ISSUES_DISPLAY=$(issues_icon "$OPEN_ISSUES")
        printf "  %-42s %-10s %-8b %-30b %s\n" \
            "$REPO" "$LANG_TRUNC" "$ISSUES_DISPLAY" "$CI_ICON" "$PUSHED_AT"
    fi
done

# ── Summary ────────────────────────────────────────────────────────────────────
if [[ "$FORMAT" == "json" ]]; then
    JSON_RESULTS+="]"
    echo "$JSON_RESULTS" | python3 -c "import sys,json; print(json.dumps(json.loads(sys.stdin.read()), indent=2))"
else
    echo ""
    echo -e "  ${BOLD}Summary${NC}"
    echo "  ─────────────────────────────────────────"
    printf "  %-28s %s\n" "Total repos checked:"   "${#REPOS[@]}"
    printf "  %-28s ${GREEN}%s${NC}\n" "CI passing:"          "$PASS_COUNT"
    printf "  %-28s ${RED}%s${NC}\n"   "CI failing:"          "$FAIL_COUNT"
    printf "  %-28s ${BLUE}%s${NC}\n"  "No CI / pending:"     "$NO_CI_COUNT"
    printf "  %-28s ${YELLOW}%s${NC}\n" "Total open issues:"  "$TOTAL_ISSUES"
    echo ""
    echo -e "  ${CYAN}Full details: https://github.com/${OWNER}${NC}"
    echo ""
fi
