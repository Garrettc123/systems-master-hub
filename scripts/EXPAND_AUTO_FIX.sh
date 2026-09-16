#!/usr/bin/env bash
# Expanded Auto-Fix for Palantir-type + Government-grade sweep
# Run from a machine with gh authenticated as Garrettc123
set -euo pipefail

OWNER="Garrettc123"
CANONICAL_SECURITY_URL="https://raw.githubusercontent.com/Garrettc123/systems-master-hub/main/SECURITY.md"

echo "=== GARCAR FULL SWEEP AUTO-FIX (Palantir-type) ==="

REPOS=(
  "systems-master-hub"
  "autonomous-butler-core"
  "autonomous-income-deployment"
  "garcar-apex-nexus"
  "NEXUS-AI-CORE"
  "APEX-Universal-AI-Operating-System"
  "enterprise-mlops-platform"
  "enterprise-unified-platform"
  "zero-human"
  "garcar-product-factory"
)

for repo in "${REPOS[@]}"; do
  echo ">>> Processing $repo"
  if ! gh repo view "$OWNER/$repo" &>/dev/null; then
    echo "  skip (not found or no access)"
    continue
  fi

  tmp=$(mktemp -d)
  gh repo clone "$OWNER/$repo" "$tmp/$repo" -- --depth 1 2>/dev/null || {
    echo "  clone failed"
    rm -rf "$tmp"
    continue
  }
  cd "$tmp/$repo"

  if [[ ! -f SECURITY.md ]]; then
    curl -sL "$CANONICAL_SECURITY_URL" -o SECURITY.md || true
    git add SECURITY.md
    git commit -m "security: add canonical SECURITY.md (Palantir-type / gov-grade)" || true
  fi

  git push origin HEAD:main 2>/dev/null || git push origin HEAD:master 2>/dev/null || echo "  push skipped"
  cd -
  rm -rf "$tmp"
  echo "  done"
done

echo "=== SWEEP PASS COMPLETE ==="
