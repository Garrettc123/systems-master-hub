# Garcar Enterprise — Phone Command Center

A mobile-first installable web-app shell for the existing Garcar control plane. It is intentionally honest about connection status: Slack, Perplexity, Notion, and the approval queue are labelled **unverified** until authenticated server adapters and live evidence exist.

## Current scope

- Responsive mobile UI and PWA manifest/service worker.
- Same-origin `GET /healthz` check with timestamp and visible failure state.
- Knowledge-search UI that calls `POST /api/knowledge/search` only when a user submits a query; missing endpoint is reported as disconnected.
- No API keys, tokens, or session credentials are embedded in static assets.
- No action execution, email sending, payment creation, deployment, or approval mutation from this UI.

## Existing API mismatch

The currently inspected `revenue/garcar_core/app.py` exposes `GET /healthz` and `POST /v1/events/lead`. It does **not** expose `/api/knowledge/search`, an approvals API, Slack OAuth, or a Perplexity adapter. The current Vercel project metadata reported `live: false`, despite a latest deployment marked `READY`; a successful live request still needs to be demonstrated. This frontend must not be represented as production-ready until served and tested against an authenticated API.

## Integration contract before production

1. Serve this directory over HTTPS from the intended app domain. Keep the existing lead API behavior intact.
2. Add an authenticated backend-for-frontend; do not call provider APIs directly from the browser.
3. Use server-side OAuth/token storage for Slack and server-side Perplexity credentials. Never expose credentials to client JavaScript.
4. Require owner identity, CSRF protection for cookie sessions, rate limits, request IDs, schema validation, and audit events.
5. Read-only knowledge queries may be allowed by policy. Mutations must be proposed as action requests, show the exact action/target/impact, require explicit owner approval, and be independently re-authorized at execution time.
6. Keep control-plane MCP on stdio or behind a separately authenticated private transport; never expose an unauthenticated MCP listener.
7. Persist approval/audit state in a durable database for multi-worker production. SQLite is local/single-node development only.
8. Add tests for auth denial, cross-origin/CSRF, duplicate idempotency keys, approval expiry/replay, fail-closed adapters, audit integrity, and provider timeouts.

## Run locally

From this directory, serve the static files with any local static HTTP server, then open `index.html` through that server. PWA install and service-worker behavior require HTTPS or localhost. The API status will fail unless a same-origin `/healthz` endpoint is configured. This is expected and visible.

## Status

UI source created; deployment, live API connectivity, OAuth, Slack, Perplexity, approval queue, and production security tests are **not yet verified**.