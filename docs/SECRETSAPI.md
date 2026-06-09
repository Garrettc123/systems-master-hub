# 🔐 SECRETSAPI — Garcar Enterprise Canonical Secrets Spec

> **THE LAW.** This document is the single source of truth for every secret used  
> across the Garcar Enterprise stack. All repos, all workflows, all deploy contracts  
> must use these exact names. No divergence. No per-repo invention.
>
> Last updated: 2026-06-09 | Owner: Garrettc123 | Repo: systems-master-hub

---

## 🏛️ Architecture

The vault has three planes:

```
┌─────────────────────────────────────────────────────────────┐
│             GARCAR MASTER VAULT (GitHub Org/Repo Secrets)    │
│                                                             │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────┐  │
│  │  ORCHESTRATION  │  │  PAYMENT RUNTIME │  │  SHARED   │  │
│  │    PLANE        │  │     PLANE        │  │   PLANE   │  │
│  │                 │  │                  │  │           │  │
│  │ GITHUB_TOKEN    │  │ STRIPE_SECRET_   │  │ SUPABASE_ │  │
│  │ LINEAR_API_KEY  │  │   KEY            │  │   URL     │  │
│  │ SLACK_WEBHOOK_  │  │ STRIPE_WEBHOOK_  │  │ SUPABASE_ │  │
│  │   URL           │  │   SECRET         │  │   SERVICE │  │
│  │                 │  │ STRIPE_          │  │   _KEY    │  │
│  │                 │  │   PUBLISHABLE_   │  │ APP_URL   │  │
│  │                 │  │   KEY            │  │           │  │
│  └────────┬────────┘  └────────┬─────────┘  └─────┬─────┘  │
│           │                   │                   │         │
│           ▼                   ▼                   ▼         │
│     systems-master-hub  garcar-payments      all repos      │
│     neural-mesh         garcar-payment-loop                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Secret Registry

### Orchestration Plane — `systems-master-hub`, `neural-mesh`

| Secret Name | Type | Description | Rotation | Repos |
|-------------|------|-------------|----------|-------|
| `GITHUB_TOKEN` | Auto-injected | GitHub Actions auth — auto-provided by Actions runtime, never store manually | Per-run | All workflows |
| `LINEAR_API_KEY` | API key | Linear issue tracking — issue creation, status sync, sweep ledger | 90 days | `systems-master-hub`, `garcar-payments`, `mars-api`, `TITAN` |
| `SLACK_WEBHOOK_URL` | Webhook URL | Slack alert delivery for deploy events, failures, sweep status | On change | All repos with alerting |

### Payment Runtime Plane — `garcar-payments`, `garcar-payment-loop`

| Secret Name | Type | Description | Rotation | Repos |
|-------------|------|-------------|----------|-------|
| `STRIPE_SECRET_KEY` | API key | Stripe server-side API auth — session creation, subscription management. **Never expose client-side.** | On compromise or 90d | `garcar-payments`, `garcar-payment-loop`, `TITAN`, `ai-business-platform` |
| `STRIPE_WEBHOOK_SECRET` | Signing secret | Webhook event signature verification. Rotate when endpoint changes. | On endpoint rotate | `garcar-payments`, `garcar-payment-loop` |
| `STRIPE_PUBLISHABLE_KEY` | Public key | Stripe.js frontend init. Safe to expose in client code. | Rarely | `garcar-payments` frontend |

### Shared App Plane — All Stateful Repos

| Secret Name | Type | Description | Rotation | Repos |
|-------------|------|-------------|----------|-------|
| `SUPABASE_URL` | Connection URL | Supabase project endpoint. Format: `https://<project>.supabase.co` | On project change | `garcar-payments`, `garcar-payment-loop`, `mars-api`, `TITAN`, `atlas-dashboard`, `zeus-dashboard` |
| `SUPABASE_SERVICE_KEY` | Service role key | Full DB access — bypasses RLS. **Server-side only. Never expose client-side.** | 90 days | Same as above |
| `APP_URL` | URL | Base URL of the deployed app instance. Used for Stripe webhook registration, CORS, callbacks. | On deploy URL change | `garcar-payments`, `mars-api` |

### Deploy Platform Plane — CI/CD Workflows

| Secret Name | Type | Description | Rotation | Repos |
|-------------|------|-------------|----------|-------|
| `RAILWAY_TOKEN` | API token | Railway deploy API — trigger deploys, get service status. | 90 days | All Railway-hosted repos |
| `VERCEL_TOKEN` | API token | Vercel deploy API — trigger builds, manage env vars. | 90 days | `atlas-dashboard`, `zeus-dashboard`, `garcar-landing` |
| `RENDER_API_KEY` | API key | Render deploy API (if used). | 90 days | Render-hosted repos |

---

## 🗺️ Secret-to-Repo Matrix

| Secret | garcar-payments | garcar-payment-loop | systems-master-hub | mars-api | TITAN | enterprise-mlops | atlas-dashboard | zeus-dashboard | neural-mesh |
|--------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| `GITHUB_TOKEN` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `LINEAR_API_KEY` | ✅ | ✅ | ✅ | ✅ | ✅ | – | – | – | – |
| `SLACK_WEBHOOK_URL` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `STRIPE_SECRET_KEY` | ✅ | ✅ | – | – | ✅ | – | – | – | – |
| `STRIPE_WEBHOOK_SECRET` | ✅ | ✅ | – | – | – | – | – | – | – |
| `STRIPE_PUBLISHABLE_KEY` | ✅ | – | – | – | – | – | – | – | – |
| `SUPABASE_URL` | ✅ | ✅ | – | ✅ | ✅ | ✅ | ✅ | ✅ | – |
| `SUPABASE_SERVICE_KEY` | ✅ | ✅ | – | ✅ | ✅ | ✅ | ✅ | ✅ | – |
| `APP_URL` | ✅ | – | – | ✅ | – | – | – | – | – |
| `RAILWAY_TOKEN` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | – | – | – |
| `VERCEL_TOKEN` | – | – | – | – | – | – | ✅ | ✅ | – |

---

## 🔄 Rotation Protocol

### When `STRIPE_SECRET_KEY` rotates
1. Update in Stripe Dashboard → Developers → API Keys
2. Update `STRIPE_SECRET_KEY` in GitHub Repo Secrets for: `garcar-payments`, `garcar-payment-loop`, `TITAN`
3. Trigger redeploy: run `./orchestrate/garcar-sweep.sh full` or dispatch `garcar-all-in-one-sweep.yml`
4. Verify: hit `/health` on `garcar-payments` — confirm `stripe_verified: true`

### When `STRIPE_WEBHOOK_SECRET` rotates
1. In Stripe Dashboard, rotate the webhook endpoint signing secret
2. Update `STRIPE_WEBHOOK_SECRET` in `garcar-payments` and `garcar-payment-loop` GitHub Secrets
3. Redeploy both repos
4. Send a test event from Stripe Dashboard → confirm 200 response

### When `SUPABASE_SERVICE_KEY` rotates
1. Generate new service role key in Supabase Dashboard → Settings → API
2. Update `SUPABASE_SERVICE_KEY` in all affected repos (see matrix above)
3. Trigger sweep: `./orchestrate/garcar-sweep.sh full`
4. Verify DB connectivity on `/health` for each affected service

### When `RAILWAY_TOKEN` rotates
1. Generate new token in Railway Dashboard → Account → Tokens
2. Update `RAILWAY_TOKEN` in `systems-master-hub` GitHub Secrets (shared)
3. All Railway-hosted repos pick it up on next deploy dispatch

---

## 🚀 One-Command Vault Setup

```bash
# Step 1: Copy template and fill in your real values
cp vault/.vault.env.template vault/.vault.env
# Edit vault/.vault.env — never commit this file

# Step 2: Load all secrets into GitHub Org/Repo Secrets
bash vault/vault-setup.sh

# Step 3: Verify
export GITHUB_TOKEN=your_token
python3 orchestrate/sweep-status.py
```

---

## 🛡️ Security Rules

1. **Never commit `.vault.env`** — it is in `.gitignore`
2. **Never commit `.env`** — only `.env.example` with placeholders
3. **Never hardcode secrets in code** — only read from `process.env` or equivalent
4. **Stripe secret keys are Stripe-managed** — do not generate them yourself; rotate via Stripe Dashboard
5. **`SUPABASE_SERVICE_KEY` bypasses RLS** — never expose client-side, only server-side injection
6. **`GITHUB_TOKEN` is auto-injected** — never store manually; it is provided by the Actions runtime per-run
7. **Rotate on any suspected exposure** — follow the Rotation Protocol above immediately

---

## 📁 Vault Template Location

`vault/.vault.env.template` — fill once, load with `vault/vault-setup.sh`

```bash
# ORCHESTRATION PLANE
GITHUB_TOKEN=
LINEAR_API_KEY=
SLACK_WEBHOOK_URL=

# PAYMENT RUNTIME PLANE
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PUBLISHABLE_KEY=

# SHARED APP PLANE
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
APP_URL=

# DEPLOY PLATFORM PLANE
RAILWAY_TOKEN=
VERCEL_TOKEN=
RENDER_API_KEY=
```

---

*Garcar Enterprise | systems-master-hub | SECRETSAPI v1.0.0 | 2026-06-09*  
*This document supersedes all prior Autokey specs, secret naming conventions, and per-repo .env documentation.*
