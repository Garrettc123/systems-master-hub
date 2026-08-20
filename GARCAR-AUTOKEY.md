# Garcar Master Autokey System

One vault. One run. All core repos fully keyed and deployed.

## How it works

`systems-master-hub` is the single source of truth for every Garcar secret.
The `garcar-autokey-propagate.yml` workflow uses `gh secret set` to push
every key to the core stack, then triggers deploy workflows.

**MultiModelRouter** reads these at runtime via `build_router_from_env()`:
- `ANTHROPIC_API_KEY` → Claude
- `OPENAI_API_KEY` → ChatGPT
- `GEMINI_API_KEY` / `GOOGLE_API_KEY` → Gemini
- `PERPLEXITY_API_KEY` → Perplexity

Missing keys → provider simply not registered (graceful degrade).

**Wealth Loop** requires:
- `APOLLO_API_KEY` → verified lead source (without this the agent exits BLOCKED)
- `STRIPE_SECRET_KEY` → payment link generation

## Add these secrets HERE (systems-master-hub) only

https://github.com/Garrettc123/systems-master-hub/settings/secrets/actions

### Required (Revenue + Core)
| Secret | Where to get it |
|--------|-----------------|
| `GHPAT` | github.com → Settings → Developer → PAT (`repo` + `secrets` + `workflow` scope) |
| `RAILWAY_TOKEN` | railway.app → Account → Tokens |
| `STRIPE_SECRET_KEY` | Stripe → Developers → API Keys |
| `APOLLO_API_KEY` | Apollo.io → Settings → Integrations → API |
| `STRIPE_PRICE_STARTER` | Stripe → Products → copy price ID |
| `STRIPE_PRICE_PRO` | Stripe → Products → copy price ID |
| `STRIPE_PRICE_AGENCY` | Stripe → Products → copy price ID |
| `OPENAI_API_KEY` | platform.openai.com → API Keys |
| `SUPABASE_URL` | Supabase → Project → Settings → API |
| `SUPABASE_ANON_KEY` | Supabase → Project → Settings → API |
| `APP_BASE_URL_PAYMENTS` | Railway → garcar-payments domain |
| `APP_BASE_URL_RHNS` | Railway → garcar-rhns-core domain |
| `APP_BASE_URL_ATLAS` | Vercel/Railway → atlas-dashboard domain |
| `APP_BASE_URL_ZEUS` | Vercel/Railway → zeus-dashboard domain |

### Strongly Recommended (Wealth Loop + Agents)
| Secret | Purpose |
|--------|---------|
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `SUPABASE_SERVICE_KEY` | Admin ledger writes (agent_runs, outcomes, genomes) |
| `HUBSPOT_API_KEY` | CRM sync + bidirectional outcome feedback |
| `LINEAR_API_KEY` | Task automation |
| `ANTHROPIC_API_KEY` | Claude — deep qualify, high-stakes reasoning |
| `GEMINI_API_KEY` | Gemini — bulk score, long-context |
| `PERPLEXITY_API_KEY` | Live web / market signals |

### Optional
| Secret | Purpose |
|--------|---------|
| `DATABASE_URL` | Shared Postgres |
| `REDIS_URL` | Shared Redis / Supabase Realtime |
| `VERCEL_TOKEN` | Atlas + Zeus frontend deploys |
| `NEXT_PUBLIC_APP_URL` | Frontend public base URL |
| `SLACK_WEBHOOK_URL` | Ops notifications |

## Run it

1. Add required + recommended secrets above to **systems-master-hub**
2. Go to Actions:
   https://github.com/Garrettc123/systems-master-hub/actions/workflows/garcar-autokey-propagate.yml
3. Click **Run workflow**
4. Type `PROPAGATE` → click **Run workflow**

That's it. The workflow validates, pushes all secrets (including APOLLO + multi-model keys),
and fires deploys. Every secret rotation: update here, re-run. Never touch individual repos.

## Runtime contract (orchestrator)

```python
from providers.router import build_router_from_env

router = build_router_from_env()  # only providers with keys are registered
router.load_from_genome(genome.modules)
```

No hard-coded keys. No per-repo secret management. Autokey is the only vault.
