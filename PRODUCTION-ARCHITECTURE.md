# Garcar Enterprise — Production Architecture (Finalized 2026-11-04)

The live, running, zero-cost production architecture. Everything in the
**LIVE** section is deployed and verified today. Everything in **STAGED**
is built and tested but awaiting one owner action. Everything in
**BLOCKED** needs credentials only the owner holds.

## LIVE — running in production now

### Money path (customer → checkout → delivery)
| Surface | URL | Status |
|---|---|---|
| 5 Stripe checkout links | $47 audit · $497/wk sprint · $1,497/mo engine + 2 storefront links | ✅ HTTP 200, accepting payments |
| Main storefront | https://garrettc123.github.io/ | ✅ live |
| garcar-landing | https://garrettc123.github.io/garcar-landing/ | ✅ live |
| believe-revenue-site | https://garrettc123.github.io/believe-revenue-site/ | ✅ live |
| Product pages (7) | systems-master-hub · garcar-revenue-wizard · garrettc1 · garrettc3 · garrettc4 · dfw-lead-audit · lead-leak-audit | ✅ 5 live, 2 building (GitHub Pages queue) |

### Production agent (autonomous, daily 08:00 CT)
Perplexity automation **"Garcar production ops — daily money & fleet agent"**:
1. Verifies every money surface (Stripe links + all pages)
2. Reads lead and order channels; files each lead/order as an issue in
   `revenue-orchestrator` (the existing Issues → CRM → Stripe loop)
3. Checks fleet heartbeats from `ai-control` agents; flags offline machines
4. Notifies on leads, orders, or failures; stays quiet when all-clear

First run verified 2026-11-04: a test lead flowed form → channel → agent →
`revenue-orchestrator` issue #1 in under a minute.

### Channels (free, zero-account)
- Leads: ntfy `aiczleadszohepktry` — fed by the funnel lead form
- Orders: ntfy `aiczorderszwrjep2of` — fed by the order confirmation page
- Command channel (HMAC-signed): ntfy `aiczthubgpotkj5m` (ai-control)

### Fleet control (ready, dual-channel)
`ai-control` agent (GitHub issues + signed ntfy) — installers for
Linux/Windows/macOS in the private repo. Machines report heartbeats to
`status/`; the daily agent monitors them.

## LIVE-READY — verified running locally 2026-11-04 (needs credentials to take money)

### garcar-product-factory (digital products)
- **45 digital products** (trade callback kits, business tools, creator templates — $29 avg, $1,063 catalog value)
- All assets built deterministically (`python3 factory.py build`), SHA-256 verified
- **22/22 tests passing**; marketplace boots and serves catalog + storefront
- Revenue loop is fail-closed by design: `PAYMENTS_MODE=disabled` until
  `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` (+ Supabase for asset delivery) are set
- Owner action to sell: set test keys → verify → flip to live

### TITAN (platform node)
- Package-import bug fixed (src/ sibling imports) — pushed to main
- Boots and serves `/` + `/health`; system registry + API bank import clean
- Domain logic (AI CEO, M&A, trading) is scaffolding — no external execution without credentials

### Perfect customer acquisition
- The acquisition loop is the production agent + funnel: capture → channel →
  ICP scoring (0-100) → prioritized issue with suggested offer → owner closes
- Outbound channels (LinkedIn/Apollo/email/SMS) remain unspecified in the
  source repo and require consent infrastructure + provider keys — not built

## STAGED — built, tested, awaiting one owner action

| Asset | What's left |
|---|---|
| `garcar-funnel` (offer hub, lead form, order page, 3 SEO guides) | Publish decision — site is complete and tested; needs owner approval to go public (collects visitor PII) |
| Stripe success URLs | In Stripe dashboard, point payment links at `garcar-funnel/order.html` so every buyer auto-confirms and delivery starts |
| `ai-control` on your machines | Run the installer on each machine (~5 min each) |
| Storefront intake wiring | Swap `intake.html` redirect in once funnel is published |

## BLOCKED — needs owner credentials

| System | What unlocks it |
|---|---|
| NEXUS / RHNS / ATLAS agent runtimes (Railway deploys) | `RAILWAY_TOKEN` per repo (garcar-rhns-core README documents the 7-job pipeline) |
| Stripe sales visibility + webhook automation | Stripe API key (read-only) for revenue reporting; webhook secret for garcar-payment-loop |
| Supabase-backed ops (garcar-product-factory) | Supabase credentials |
| Vercel deployments | Vercel token re-auth (current token locked out of scope `carrolgarrett5-5537s-projects`) |
| HubSpot CRM loop (revenue-orchestrator) | HubSpot token |

## Fleet (313 repos)

Verified 2026-11-04: 109/109 tests passing across the five core systems;
inventory rebuilt live in `garcar-repo-foundry/inventory/repos.json`.
See [SYNC-2026-11-04.md](SYNC-2026-11-04.md) for the full verification matrix.
