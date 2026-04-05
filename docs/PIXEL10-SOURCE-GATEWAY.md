# Pixel 10 Source Gateway Architecture

The Source Gateway is a harmonized ingestion layer that connects the Pixel 10 edge
node to all approved data sources. Because the phone cannot directly call
platform-only connectors (OAuth flows, long-lived server credentials, webhook
receivers), the architecture splits cleanly into two planes:

| Plane | Runs on | Responsibility |
|-------|---------|---------------|
| **Edge (on-device)** | Pixel 10 / Termux | Local telemetry collection, queue management, outbound event dispatch, polling public/local endpoints |
| **Cloud (off-device)** | GitHub Actions / VPS / Perplexity | OAuth token management, webhook ingestion, platform API polling, secret storage |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  Cloud Plane  (GitHub Actions / VPS / Perplexity)                  │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ notion_mcp   │  │ linear_alt   │  │ github_mcp   │  ...        │
│  │ adapter      │  │ adapter      │  │ adapter      │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
│         │                 │                 │                      │
│         └────────┬────────┴────────┬────────┘                      │
│                  ▼                 ▼                                │
│         ┌───────────────────────────────┐                          │
│         │  cloud-relay/                 │                          │
│         │  normalize → JSON envelope    │                          │
│         │  push to edge via SSH / sync  │                          │
│         └───────────────┬───────────────┘                          │
│                         │                                          │
└─────────────────────────┼──────────────────────────────────────────┘
                          │  SSH (port 8022) / rsync / curl
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Edge Plane  (Pixel 10 / Termux)                                   │
│                                                                    │
│  ~/edge-node/                                                      │
│    ├── gateway/                                                    │
│    │   ├── ingest-local.sh       collect device telemetry          │
│    │   ├── dispatch-outbound.sh  push events to cloud relay        │
│    │   └── queue/                JSON event files (FIFO)           │
│    │       ├── pending/                                            │
│    │       ├── sent/                                               │
│    │       └── failed/                                             │
│    ├── config/                                                     │
│    │   ├── node-identity.json    (existing)                        │
│    │   └── sources.json          approved source manifest          │
│    └── reports/                                                    │
│        └── *.json                normalized event reports           │
│                                                                    │
│  ┌──────────────────────────────────────────────────────┐          │
│  │  Local-only sources (direct polling)                 │          │
│  │  • battery, storage, network, sensors (termux-api)   │          │
│  │  • Ollama model status (:11434)                      │          │
│  │  • on-device logs and cron history                   │          │
│  └──────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

## Source Categories

Each source has a `plane` assignment (where it runs) and a `mode` (how it polls):

| Source | Plane | Mode | Notes |
|--------|-------|------|-------|
| `web` | cloud | webhook / poll | General web content via Perplexity or scraping |
| `notion_mcp` | cloud | poll | Notion API via MCP server; needs OAuth token |
| `linear_alt` | cloud | poll | Linear API; needs API key |
| `github_mcp_direct` | cloud | webhook + poll | GitHub API via MCP; needs PAT |
| `slack_direct` | cloud | webhook | Slack Events API; needs bot token |
| `vercel` | cloud | poll | Vercel API for deploy status |
| `godaddy` | cloud | poll | Domain status via GoDaddy API |
| `blockscout` | cloud/edge | poll | Public blockchain explorer; some endpoints phone-reachable |
| `wix` | cloud | poll | Wix site data via API |
| `stripe` | cloud | webhook | Payment events; needs restricted key |
| `google_drive` | cloud | poll | Drive API; needs OAuth |
| `social` | cloud | poll | Social media aggregator |
| `gcal` | cloud | poll | Google Calendar API; needs OAuth |
| `outlook` | cloud | poll | Microsoft Graph API; needs OAuth |
| `scholar` | cloud/edge | poll | Google Scholar; public pages phone-reachable |
| `device_telemetry` | edge | local | Battery, storage, network, sensors |
| `ollama_status` | edge | local | Ollama model and inference status |

## Data Flow

### 1. Cloud → Edge (pull model)

Cloud adapters run on a schedule (cron, GitHub Actions, or a lightweight relay
server). Each adapter:

1. Authenticates with the source API using secrets stored in the cloud environment
2. Fetches new data since the last checkpoint
3. Normalizes the response into a **Source Event Envelope** (see schema below)
4. Delivers the envelope to the Pixel via SSH/rsync or stores it for the
   next device sync

### 2. Edge → Cloud (push model)

The on-device `dispatch-outbound.sh` script:

1. Reads events from `~/edge-node/gateway/queue/pending/`
2. Pushes each event to a cloud relay endpoint (configurable webhook URL)
3. Moves successful events to `sent/`, failed ones to `failed/` for retry

### 3. Local telemetry (edge-only loop)

The on-device `ingest-local.sh` script:

1. Collects device telemetry (battery, storage, network, services)
2. Writes a normalized event to the local queue
3. Optionally dispatches to cloud for aggregation

## Source Event Envelope Schema

Every event — regardless of origin — uses the same JSON envelope:

```json
{
  "schema_version": "1.0",
  "event_id": "uuid-v4",
  "source": "notion_mcp",
  "category": "cloud",
  "timestamp": "2026-04-05T12:00:00Z",
  "node_id": "pixel10-edge",
  "payload": {
    "type": "page_updated",
    "data": { }
  },
  "metadata": {
    "adapter_version": "1.0.0",
    "polling_mode": "scheduled",
    "ttl_seconds": 86400
  }
}
```

## Security Model

- **Secrets never touch the phone.** All OAuth tokens, API keys, and bot tokens
  live in GitHub Secrets or a cloud vault. Cloud adapters use them; the phone
  only receives normalized, credential-free JSON payloads.
- **SSH is the transport layer.** The existing ed25519 keypair and sshd on port
  8022 serve as the authenticated channel between cloud and edge.
- **Outbound webhooks use a relay token.** The phone dispatches events to a
  single cloud relay URL with a rotating HMAC signature — no platform
  credentials needed on-device.
- **Envelope payloads are sanitized.** Cloud adapters strip raw API responses
  down to the fields the edge node needs; no raw tokens or internal IDs leak
  through.

## Polling & Scheduling

| Cadence | Sources |
|---------|---------|
| Every 5 min | `device_telemetry`, `ollama_status` |
| Every 15 min | `github_mcp_direct`, `linear_alt`, `slack_direct` |
| Every 30 min | `notion_mcp`, `gcal`, `outlook`, `vercel` |
| Every 60 min | `google_drive`, `stripe`, `social`, `web` |
| Every 6 hours | `godaddy`, `wix`, `blockscout`, `scholar` |

These defaults are configured in `termux/gateway/sources.json` and can be
overridden per-source.

## File Layout

```
termux/gateway/
├── sources.json              # approved source manifest + polling config
├── ingest-local.sh           # collect on-device telemetry
├── dispatch-outbound.sh      # push queued events to cloud relay
├── schema/
│   └── event-envelope.json   # JSON schema for the envelope format
└── sample/
    ├── device-telemetry.json # example local telemetry event
    └── cloud-event.json      # example cloud-sourced event

docs/
├── PIXEL10-SOURCE-GATEWAY.md # this file
└── PIXEL10-CLOUD-ADAPTERS.md # cloud-side adapter integration guide
```
