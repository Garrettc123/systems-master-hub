#!/usr/bin/env bash
###############################################################################
# Cloud Adapter: blockscout (placeholder)
#
# Polls Blockscout public API for on-chain transaction data.
# This source has edge_fallback=true — the phone can query public endpoints
# directly when the cloud relay is unavailable.
#
# Required secrets: none (public API)
# Endpoint: https://eth.blockscout.com/api/v2/
#
# TODO: Implement address transaction polling + token transfer tracking.
###############################################################################
set -euo pipefail
SOURCE_NAME="blockscout"
echo "=== Cloud Adapter: ${SOURCE_NAME} (placeholder) ==="
echo "    Scaffold for Blockscout blockchain explorer polling."
echo "    Public API — phone can also query directly as fallback."
exit 0
