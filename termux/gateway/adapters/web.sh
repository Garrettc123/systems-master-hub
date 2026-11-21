#!/usr/bin/env bash
###############################################################################
# Cloud Adapter: web — Perplexity Agent API
#
# Emits a normalized JSON research result to stdout. It does not write to the
# data room or trigger actions; the caller must validate and persist evidence.
#
# Required secret: PERPLEXITY_API_KEY (injected by the host secret manager)
###############################################################################
set -euo pipefail
SOURCE_NAME="web"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
QUERY="${1:-${QUERY:-}}"

if [[ -z "$QUERY" ]]; then
  echo "usage: $0 \"research query\"" >&2
  exit 2
fi

if [[ -z "${PERPLEXITY_API_KEY:-}" ]]; then
  echo "ERROR: PERPLEXITY_API_KEY is not configured in the runtime secret store" >&2
  exit 3
fi

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m orchestrator.providers.perplexity_client --query "$QUERY"
