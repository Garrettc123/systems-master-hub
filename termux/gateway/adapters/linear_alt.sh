#!/usr/bin/env bash
###############################################################################
# Cloud Adapter: linear_alt (placeholder)
#
# Polls Linear GraphQL API for recent issue updates.
#
# Required secrets: LINEAR_API_KEY
# Endpoint: https://api.linear.app/graphql
#
# TODO: Implement query:
#   query { issues(filter: { updatedAt: { gt: "$SINCE" } }, first: 50) {
#     nodes { id identifier title state { name } updatedAt assignee { name } }
#   }}
###############################################################################
set -euo pipefail
SOURCE_NAME="linear_alt"
echo "=== Cloud Adapter: ${SOURCE_NAME} (placeholder) ==="
echo "    Scaffold for Linear GraphQL polling."
echo "    See adapters/adapter-template.sh for envelope pattern."
exit 0
