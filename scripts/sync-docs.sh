#!/usr/bin/env bash
################################################################################
# 📚 SYSTEMS MASTER HUB — Documentation Sync Script
# Auto-syncs key documentation files to all repositories
#
# Usage:
#   ./scripts/sync-docs.sh                      # Sync to all repos (dry-run)
#   ./scripts/sync-docs.sh --apply              # Actually push changes
#   ./scripts/sync-docs.sh --repo <name>        # Sync to a single repo
#   GITHUB_TOKEN=<token> ./scripts/sync-docs.sh --apply
#
# What it syncs:
#   - CONTRIBUTING.md  (contribution guidelines)
#   - CODE_OF_CONDUCT.md (community standards)
#   - SECURITY.md       (security policy)
#   - .github/ISSUE_TEMPLATE/ (issue templates)
################################################################################

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

OWNER="Garrettc123"
API_BASE="https://api.github.com"
APPLY=false
SPECIFIC_REPO=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
SYNC_LOG="${REPO_ROOT}/logs/sync-docs-$(date +%Y%m%d_%H%M%S).log"
COMMIT_MSG="docs: sync shared documentation from systems-master-hub [skip ci]"

# Repos to sync docs into
REPOS=(
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
    "stablecoin-protocol"
)

# Files to sync (relative to REPO_ROOT/docs/shared/)
SYNC_FILES=(
    "CONTRIBUTING.md"
    "CODE_OF_CONDUCT.md"
    "SECURITY.md"
)

# ── Parse args ─────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --apply)   APPLY=true;           shift ;;
        --repo)    SPECIFIC_REPO="$2";   shift 2 ;;
        --help|-h) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *)         echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    echo -e "${RED}ERROR: GITHUB_TOKEN is not set.${NC}"
    exit 1
fi

AUTH_HEADER="Authorization: Bearer ${GITHUB_TOKEN}"
mkdir -p "$(dirname "$SYNC_LOG")"

log() { echo -e "[$(date +'%H:%M:%S')] $*" | tee -a "$SYNC_LOG"; }

gh_get() {
    curl -sf -H "$AUTH_HEADER" -H "Accept: application/vnd.github+json" "$1" 2>/dev/null || echo "null"
}

gh_put() {
    local url="$1"
    local data="$2"
    curl -sf -X PUT \
        -H "$AUTH_HEADER" \
        -H "Accept: application/vnd.github+json" \
        -H "Content-Type: application/json" \
        -d "$data" \
        "$url" 2>/dev/null || echo "null"
}

# ── Ensure shared source docs exist ───────────────────────────────────────────
SHARED_DIR="${REPO_ROOT}/docs/shared"
mkdir -p "$SHARED_DIR"

# Create CONTRIBUTING.md if not present
if [[ ! -f "${SHARED_DIR}/CONTRIBUTING.md" ]]; then
cat > "${SHARED_DIR}/CONTRIBUTING.md" << 'EOF'
# Contributing

Thank you for your interest in contributing to this project!

## How to Contribute

1. **Fork** the repository and create your branch from `main`.
2. **Describe** your changes clearly in the pull request.
3. **Test** your changes before submitting.
4. **Reference** any related issues in your PR description.

## Code Style

- Follow the existing code style for the language used.
- Add comments for non-obvious logic.
- Keep PRs focused and small when possible.

## Reporting Issues

- Search existing issues before opening a new one.
- Use the bug report or feature request templates.
- Provide as much context as possible.

## Questions

Open a Discussion or reach out via the issue tracker.
EOF
fi

# Create CODE_OF_CONDUCT.md if not present
if [[ ! -f "${SHARED_DIR}/CODE_OF_CONDUCT.md" ]]; then
cat > "${SHARED_DIR}/CODE_OF_CONDUCT.md" << 'EOF'
# Code of Conduct

## Our Pledge

We are committed to providing a welcoming and inspiring community for all.

## Our Standards

- Be respectful and constructive.
- Accept differing viewpoints and experiences.
- Focus on what is best for the community.
- Show empathy toward other community members.

## Enforcement

Instances of unacceptable behavior may be reported to the repository maintainers.
All complaints will be reviewed and investigated promptly and fairly.

## Attribution

This Code of Conduct is adapted from the [Contributor Covenant](https://www.contributor-covenant.org).
EOF
fi

# Create SECURITY.md if not present
if [[ ! -f "${SHARED_DIR}/SECURITY.md" ]]; then
cat > "${SHARED_DIR}/SECURITY.md" << 'EOF'
# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| Latest  | ✅ Yes    |

## Reporting a Vulnerability

**Do not** open a public GitHub issue for security vulnerabilities.

Please report security vulnerabilities by:
1. Opening a [GitHub Security Advisory](../../security/advisories/new) in this repository.
2. Or emailing the maintainer directly.

You will receive a response within 72 hours. If the issue is confirmed,
a patch will be released as soon as possible.
EOF
fi

# ── Sync a single file to a single repo ───────────────────────────────────────
sync_file_to_repo() {
    local repo="$1"
    local filename="$2"
    local source_file="${SHARED_DIR}/${filename}"

    if [[ ! -f "$source_file" ]]; then
        log "${YELLOW}⚠️  Source file not found: ${source_file}${NC}"
        return 1
    fi

    local target_path="$filename"
    local encoded_content
    encoded_content=$(base64 < "$source_file" | tr -d '\n')

    # Check if file already exists in the target repo
    local existing
    existing=$(gh_get "${API_BASE}/repos/${OWNER}/${repo}/contents/${target_path}")
    local sha=""
    if [[ "$existing" != "null" ]]; then
        sha=$(echo "$existing" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('sha',''))" 2>/dev/null || echo "")
    fi

    if [[ "$APPLY" == "false" ]]; then
        if [[ -n "$sha" ]]; then
            log "${BLUE}[DRY-RUN]${NC} Would update ${repo}/${target_path}"
        else
            log "${BLUE}[DRY-RUN]${NC} Would create ${repo}/${target_path}"
        fi
        return 0
    fi

    # Build payload
    local payload
    if [[ -n "$sha" ]]; then
        payload=$(python3 -c "
import json, sys
print(json.dumps({
    'message': '${COMMIT_MSG}',
    'content': sys.argv[1],
    'sha': sys.argv[2]
}))" "$encoded_content" "$sha")
    else
        payload=$(python3 -c "
import json, sys
print(json.dumps({
    'message': '${COMMIT_MSG}',
    'content': sys.argv[1]
}))" "$encoded_content")
    fi

    local result
    result=$(gh_put "${API_BASE}/repos/${OWNER}/${repo}/contents/${target_path}" "$payload")

    if echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'content' in d else 1)" 2>/dev/null; then
        local action
        [[ -n "$sha" ]] && action="Updated" || action="Created"
        log "${GREEN}✅ ${action}${NC} ${repo}/${target_path}"
    else
        log "${RED}❌ Failed${NC}: ${repo}/${target_path}"
        return 1
    fi
}

sync_repo() {
    local repo="$1"

    # Verify repo exists
    local repo_data
    repo_data=$(gh_get "${API_BASE}/repos/${OWNER}/${repo}")
    if [[ "$repo_data" == "null" ]]; then
        log "${YELLOW}⚠️  Repo not found or private: ${repo} — skipping${NC}"
        return 0
    fi

    log "${CYAN}── Syncing docs to: ${repo}${NC}"
    local fails=0
    for f in "${SYNC_FILES[@]}"; do
        sync_file_to_repo "$repo" "$f" || fails=$((fails+1))
    done
    return "$fails"
}

# ── Banner ─────────────────────────────────────────────────────────────────────
echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       📚 SYSTEMS MASTER HUB — DOCUMENTATION SYNC            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
[[ "$APPLY" == "false" ]] && echo -e "  ${YELLOW}DRY-RUN MODE — pass --apply to actually push changes${NC}\n"
echo "  Files to sync: ${SYNC_FILES[*]}"
echo "  Source dir:    ${SHARED_DIR}"
echo "  Log:           ${SYNC_LOG}"
echo ""

# ── Run ────────────────────────────────────────────────────────────────────────
TOTAL_PASS=0
TOTAL_FAIL=0

if [[ -n "$SPECIFIC_REPO" ]]; then
    sync_repo "$SPECIFIC_REPO" && TOTAL_PASS=$((TOTAL_PASS+1)) || TOTAL_FAIL=$((TOTAL_FAIL+1))
else
    for repo in "${REPOS[@]}"; do
        sync_repo "$repo" && TOTAL_PASS=$((TOTAL_PASS+1)) || TOTAL_FAIL=$((TOTAL_FAIL+1))
        sleep 0.3  # Respect rate limits
    done
fi

echo ""
echo -e "  ${BOLD}Sync Summary${NC}"
echo "  ─────────────────────────────────────────"
printf "  %-28s ${GREEN}%d${NC}\n" "Repos synced:"  "$TOTAL_PASS"
printf "  %-28s ${RED}%d${NC}\n"   "Repos failed:"  "$TOTAL_FAIL"
echo ""

[[ "$TOTAL_FAIL" -gt 0 ]] && exit 1 || exit 0
