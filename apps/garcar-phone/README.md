# Garcar Enterprise — Phone Command Center

Mobile-first PWA served by the existing FastAPI app at `revenue/garcar_core/static`. The frontend and API share one origin.

## Implemented in this branch

- PWA shell, responsive layout, and same-origin API health check.
- `GET /api/phone/status`: reports provider credential presence only; never returns credential values.
- `POST /api/knowledge/search`: read-only parallel search across GitHub issues/PRs, Slack messages, Notion pages, and Perplexity research.
- Bounded query length, provider timeouts, partial-failure reporting, and server-side credentials only.
- Existing `POST /v1/events/lead` behavior preserved.
- No provider writes, outbound messages, payments, deployments, or autonomous action execution.

## Required runtime configuration

Provision these server-side values through the existing authorized secret-management workflow; do not paste credentials into chat:

- `GITHUB_TOKEN` — GitHub token scoped to only the repositories/issues the command center should search. The Vault mapping key is `GITHUB_READ_TOKEN`; it is intentionally separate from the broader `GHPAT` used for repository administration.
- `SLACK_USER_TOKEN` — Slack user token with `search:read` and intended channel access. A bot token alone does not support `search.messages`.
- `NOTION_API_KEY` — Notion integration token with only the pages/data sources explicitly shared to it.
- `PERPLEXITY_API_KEY` — Perplexity API key; user-triggered research may incur usage charges.
- Optional `PERPLEXITY_MODEL` — defaults to `sonar`.

The current Vercel project has no environment variables or project connector connections. Therefore provider adapters are implemented but not live-connected until authorized credentials are provisioned and smoke-tested. ChatGPT's connected apps do not automatically become Vercel server credentials. The new `vault/hashicorp/sync_to_vercel_preview.py` reads these keys from canonical Vault and writes only to the `feat/garcar-phone-command-center` Preview environment. It does not write Production variables. The existing scheduled/manual Vault workflow calls it in `sync` mode after this change is merged to the default branch; absent Vault keys are reported by name and are never synthesized.

## Security / deployment gate

Keep Vercel Deployment Protection (SSO) enabled for every hostname serving this app. Do not attach an unprotected custom domain or make the API public. Provider adapters are read-only. No approval queue or action-execution API is currently integrated.

## Verification gates

- Run both `test_app.py` and `test_phone_integrations.py` in CI.
- Confirm each provider using a read-only live smoke test.
- Keep this PR draft and do not promote to production until CI, provider tests, and access protection are verified.
