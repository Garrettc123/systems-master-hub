# Garcar Enterprise — Phone Command Center

Mobile-first PWA served by the existing FastAPI app at `revenue/garcar_core/static`. The frontend and API share one origin.

## Implemented in this branch

- PWA shell, responsive layout, service worker, and same-origin API health check.
- `GET /api/phone/status`: reports provider credential presence only; never returns credential values.
- `POST /api/knowledge/search`: read-only parallel search across configured Slack, Notion, and Perplexity APIs. Partial provider failure is surfaced rather than hidden.
- Server-side adapters in `revenue/garcar_core/phone_integrations.py`, with bounded query length and request timeout.
- Existing `POST /v1/events/lead` behavior preserved.
- No provider credentials in browser assets; no provider write actions, outbound messaging, payments, or approval mutation.

## Required runtime configuration

Set these server-side environment variables using the existing authorized secret-management workflow:

- `SLACK_USER_TOKEN` — Slack user token with `search:read` and access to intended channels. Slack's `search.messages` API is not enabled by a bot token alone.
- `NOTION_API_KEY` — Notion integration token with the pages/data sources explicitly shared to that integration.
- `PERPLEXITY_API_KEY` — Perplexity API key; user-triggered research may incur provider usage charges.
- Optional `PERPLEXITY_MODEL` — defaults to `sonar`.

The existing Vercel project currently reports no environment variables and no project connector connections, so provider calls fail closed until existing authorized credentials are provisioned into the project. ChatGPT's Slack/Notion connectors do not automatically become Vercel server credentials.

## Security / deployment gate

**Keep Vercel Deployment Protection (SSO) enabled on every hostname serving this app.** The FastAPI provider endpoints rely on the protected deployment boundary; do not attach an unprotected custom domain or make the API public. The provider adapters are read-only. They do not expose Slack posting, Notion editing, payments, deployments, or autonomous action execution.

## Still not implemented / not verified

- Credential provisioning from the canonical vault to Vercel.
- Live provider authentication and search results in the deployed app.
- Approval queue and action execution.
- Durable multi-worker audit/approval storage.
- Passing CI and verified provider smoke tests. Do not promote to production until these gates pass.

## Tests

`revenue/garcar_core/test_phone_integrations.py` covers credential redaction, bot-token rejection for Slack search, fail-closed behavior when no providers are configured, request validation, and UI serving. CI must run both `test_app.py` and `test_phone_integrations.py`.
