# Pixel 10 Cloud Adapters — Integration Guide

This document explains how cloud-side adapters, Perplexity/connected systems,
and the Pixel 10 edge node cooperate to form the Source Gateway.

## Why Cloud Adapters Exist

The Pixel 10 runs Termux — a capable Linux environment, but one that **cannot**:

- Host a publicly routable webhook endpoint (NAT'd mobile network)
- Maintain long-lived OAuth2 sessions (token refresh requires a server)
- Store platform API keys safely (device could be lost/stolen)
- Run MCP server processes (memory/CPU constraints)

Cloud adapters solve this by running the authenticated, network-dependent parts
of each source integration on infrastructure that can handle them, then
delivering sanitized, credential-free JSON envelopes to the phone.

## Cooperation Model

```
┌────────────┐     ┌───────────────────┐     ┌──────────────┐
│ Perplexity │────▶│  Cloud Relay /    │────▶│  Pixel 10    │
│ (research) │     │  GitHub Actions   │     │  (edge node) │
└────────────┘     │                   │     │              │
                   │  Runs adapters:   │     │  Receives:   │
┌────────────┐     │  • notion_mcp     │     │  • Envelopes │
│ Platform   │────▶│  • github_mcp     │     │  • Reports   │
│ APIs       │     │  • slack, gcal... │     │              │
└────────────┘     └───────────────────┘     └──────────────┘
                          │                        │
                          │  SSH / rsync / curl     │
                          └────────────────────────▶│
```

### Perplexity's Role

Perplexity acts as the **research and orchestration brain**:

1. **Web source**: Perplexity searches and summarizes web content, then pushes
   normalized results through the `web` cloud adapter.
2. **Cross-source correlation**: When events from multiple sources need context
   (e.g., a GitHub PR that references a Linear ticket), Perplexity can join
   the data before delivering a unified summary.
3. **Natural language queries**: The edge node can queue a question (via
   `dispatch-outbound.sh`), and Perplexity processes it cloud-side, returning
   the answer as an envelope.

### GitHub Actions as Adapter Runtime

For sources that only need periodic polling, GitHub Actions scheduled workflows
are the simplest cloud adapter runtime:

```yaml
# .github/workflows/source-gateway-poll.yml (example)
on:
  schedule:
    - cron: '*/15 * * * *'  # every 15 min
  workflow_dispatch:

jobs:
  poll-sources:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run GitHub adapter
        env:
          GITHUB_PAT: ${{ secrets.SOURCE_GITHUB_PAT }}
          PIXEL10_IP: ${{ secrets.PIXEL10_IP }}
          PIXEL10_SSH_PORT: ${{ secrets.PIXEL10_SSH_PORT }}
        run: |
          echo "${{ secrets.PIXEL10_SSH_KEY }}" > /tmp/key && chmod 600 /tmp/key
          PIXEL10_SSH_KEY_PATH=/tmp/key bash termux/gateway/adapters/github_mcp_direct.sh
```

### Webhook Sources (Slack, Stripe)

Sources that push events via webhooks need a persistent server:

| Option | Pros | Cons |
|--------|------|------|
| Lightweight VPS (e.g., a $5/mo droplet) | Always on, real-time events | Monthly cost |
| Cloudflare Worker / Vercel Edge Function | Serverless, free tier | Cold starts, limited runtime |
| ngrok + local machine | Quick dev setup | Not production-grade |

The webhook server receives events, normalizes them into envelopes, and
either pushes to the edge node via SSH or queues them for the next sync.

## Adapter Lifecycle

### 1. Development

```bash
# Copy the template
cp termux/gateway/adapters/adapter-template.sh termux/gateway/adapters/my_source.sh

# Implement fetch_and_normalize()
# Test locally with PIXEL10_IP unset (dry-run mode)
SOURCE_NAME=my_source bash termux/gateway/adapters/my_source.sh
```

### 2. Registration

Add the source to `termux/gateway/sources.json`:

```json
"my_source": {
  "enabled": true,
  "plane": "cloud",
  "mode": "poll",
  "poll_interval_minutes": 30,
  "cloud_adapter": "adapters/my_source.sh",
  "secrets_required": ["MY_SOURCE_API_KEY"]
}
```

### 3. Secrets

Add required secrets to GitHub repository settings:

```
Settings → Secrets and variables → Actions → New repository secret
```

**Never add secrets to `sources.json` or any file in the repo.**

### 4. Scheduling

- **Poll adapters**: Add a cron trigger to the GitHub Actions workflow
- **Webhook adapters**: Deploy the webhook server and configure the platform's
  webhook URL to point to it

### 5. Monitoring

The edge node's `status-report.sh` (with `--json`) includes queue depths.
The watchdog can be extended to alert on stale queues (no new events in
expected windows).

## Secrets Inventory

All secrets live in GitHub Secrets or a cloud vault. This table tracks what
each adapter needs — **do not fill in actual values here**.

| Secret Name | Used By | Scope |
|-------------|---------|-------|
| `PIXEL10_SSH_KEY` | All adapters | SSH delivery to edge |
| `PIXEL10_IP` | All adapters | Edge node address |
| `PIXEL10_SSH_PORT` | All adapters | SSH port (default 8022) |
| `GITHUB_PAT` | github_mcp_direct | Repo + Actions read |
| `NOTION_MCP_TOKEN` | notion_mcp | Workspace read |
| `LINEAR_API_KEY` | linear_alt | Issues read |
| `SLACK_BOT_TOKEN` | slack_direct | Channel history |
| `SLACK_SIGNING_SECRET` | slack_direct | Webhook verification |
| `VERCEL_TOKEN` | vercel | Deployments read |
| `GODADDY_API_KEY` | godaddy | Domains read |
| `GODADDY_API_SECRET` | godaddy | Domains read |
| `WIX_API_KEY` | wix | Site data read |
| `STRIPE_RESTRICTED_KEY` | stripe | Events read-only |
| `STRIPE_WEBHOOK_SECRET` | stripe | Webhook verification |
| `GOOGLE_OAUTH_CLIENT_ID` | gcal, google_drive | Google APIs |
| `GOOGLE_OAUTH_CLIENT_SECRET` | gcal, google_drive | Google APIs |
| `GOOGLE_REFRESH_TOKEN` | gcal, google_drive | Token refresh |
| `MICROSOFT_CLIENT_ID` | outlook | MS Graph |
| `MICROSOFT_CLIENT_SECRET` | outlook | MS Graph |
| `MICROSOFT_REFRESH_TOKEN` | outlook | Token refresh |
| `SOCIAL_AGGREGATOR_KEY` | social | Social API |
| `PERPLEXITY_API_KEY` | web | Search/research |

## Edge Fallback Sources

Two sources (`blockscout`, `scholar`) have `edge_fallback: true` in the
manifest. This means the phone can query their public APIs directly when the
cloud relay is unavailable — no credentials needed.

The `ingest-local.sh` script can be extended to handle these:

```bash
# Example: direct Blockscout query from the phone
curl -sf "https://eth.blockscout.com/api/v2/addresses/0x.../transactions" \
  | jq '...' > envelope.json
```

This is intentionally limited to read-only, public, unauthenticated endpoints.

## Queue Management

Events flow through a simple file-based queue on the edge node:

```
~/edge-node/gateway/queue/
  pending/   ← new events land here (from cloud delivery or local ingestion)
  sent/      ← successfully dispatched to cloud relay
  failed/    ← dispatch failures (retried by --retry flag)
```

**Garbage collection**: Events older than `ttl_seconds` (from the envelope
metadata) can be purged. A simple cron job handles this:

```bash
# Add to crontab: purge events older than 24 hours from sent/
find ~/edge-node/gateway/queue/sent -name '*.json' -mmin +1440 -delete
```
