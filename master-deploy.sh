#!/usr/bin/env bash
################################################################################
# GARCAR SYSTEMS MASTER HUB — SAFE DEPLOY DISPATCHER
#
# Default mode is DRY-RUN. Real dispatch requires:
#   GARCAR_DEPLOY_CONFIRM=YES ./master-deploy.sh --deploy
################################################################################
set -euo pipefail

OWNER="Garrettc123"
API_BASE="https://api.github.com"
DEFAULT_WORKFLOW="ci.yml"
BRANCH="${BRANCH:-main}"
DRY_RUN=true
SPECIFIC_REPO=""
SPECIFIC_WORKFLOW=""
DEPLOY_LOG="./logs/master-deploy-$(date +%Y%m%d_%H%M%S).log"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_TOKEN is not set."
  exit 1
fi

if [[ "${1:-}" == "--deploy" ]]; then
  DRY_RUN=false
  shift
fi

if [[ "$DRY_RUN" == "false" && "${GARCAR_DEPLOY_CONFIRM:-}" != "YES" ]]; then
  echo "ERROR: real dispatch requires GARCAR_DEPLOY_CONFIRM=YES"
  exit 1
fi

# Registry entries are intentionally explicit. Unknown repositories are never
# dispatched by the master script.
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) SPECIFIC_REPO="$2"; shift 2 ;;
    --workflow) SPECIFIC_WORKFLOW="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --help|-h)
      echo "Usage: ./master-deploy.sh [--deploy] [--repo NAME] [--workflow FILE] [--branch BRANCH]"
      echo "Default: dry-run only."
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

mkdir -p "$(dirname "$DEPLOY_LOG")"

log() {
  echo "[$(date +'%H:%M:%S')] $*" | tee -a "$DEPLOY_LOG"
}

trigger_workflow() {
  local repo="$1"
  local workflow="$2"
  local branch="$3"
  local url="${API_BASE}/repos/${OWNER}/${repo}/actions/workflows/${workflow}/dispatches"

  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN: ${repo} / ${workflow} @ ${branch}"
    return 0
  fi

  local status
  status=$(curl -sS -o /dev/null -w '%{http_code}' \
    -X POST \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H 'Accept: application/vnd.github+json' \
    -H 'Content-Type: application/json' \
    -d "{\"ref\":\"${branch}\"}" \
    "$url")

  if [[ "$status" == "204" ]]; then
    log "DISPATCHED: ${repo} / ${workflow} @ ${branch}"
  else
    log "FAILED: ${repo} / ${workflow} @ ${branch} (HTTP ${status})"
    return 1
  fi
}

deploy_repo() {
  local repo="$1"
  local workflow="${SPECIFIC_WORKFLOW:-${REPO_WORKFLOWS[$repo]:-$DEFAULT_WORKFLOW}}"
  trigger_workflow "$repo" "$workflow" "$BRANCH"
}

PASS=0
FAIL=0

if [[ -n "$SPECIFIC_REPO" ]]; then
  if [[ -z "${REPO_WORKFLOWS[$SPECIFIC_REPO]+x}" ]]; then
    echo "ERROR: repository is not in the explicit deployment registry: $SPECIFIC_REPO"
    exit 1
  fi
  deploy_repo "$SPECIFIC_REPO" && PASS=$((PASS+1)) || FAIL=$((FAIL+1))
else
  for repo in "${!REPO_WORKFLOWS[@]}"; do
    deploy_repo "$repo" && PASS=$((PASS+1)) || FAIL=$((FAIL+1))
  done
fi

echo "Deployment dispatcher complete: pass=${PASS} fail=${FAIL} dry_run=${DRY_RUN}"
[[ "$FAIL" -eq 0 ]]
