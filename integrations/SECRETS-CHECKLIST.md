# Garcar Enterprise — Integration Secrets Checklist

All secrets must be added to GitHub repo secrets at:
https://github.com/Garrettc123/systems-master-hub/settings/secrets/actions

## GitHub
- [ ] `GITHUB_TOKEN` — auto-injected by GitHub Actions
- [ ] `GH_PAT` — Personal Access Token (for cross-repo dispatches)

## Slack
- [ ] `SLACK_BOT_TOKEN` — From Slack App → OAuth & Permissions
- [ ] `SLACK_WEBHOOK_URL` — Incoming Webhook URL
- [ ] `SLACK_REVENUE_CHANNEL` — Channel ID (e.g., C0XXXXXX) for #garcar-revenue
- [ ] `SLACK_ALERTS_CHANNEL` — Channel ID for #garcar-alerts

## Base by Coinbase
- [ ] `BASE_RPC_URL` — Base Mainnet RPC (e.g., https://mainnet.base.org)
- [ ] `BASE_PRIVATE_KEY` — Wallet private key (treasury wallet)
- [ ] `BASE_CONTRACT_ADDRESS` — Deployed RevenueVault contract address
- [ ] `COINBASE_API_KEY` — Coinbase Developer Platform API key

## Shopify
- [ ] `SHOPIFY_API_KEY` — Shopify Admin API key
- [ ] `SHOPIFY_API_SECRET` — Shopify Admin API secret
- [ ] `SHOPIFY_ACCESS_TOKEN` — Shopify Admin API access token
- [ ] `SHOPIFY_WEBHOOK_SECRET` — Webhook HMAC verification secret

## Notion
- [ ] `NOTION_API_KEY` — Notion Integration token
- [ ] `NOTION_DEALS_DB_ID` — Database ID for Deals Pipeline
- [ ] `NOTION_REVENUE_DB_ID` — Database ID for Revenue Tracker
- [ ] `NOTION_LEADS_DB_ID` — Database ID for Lead CRM

## Linear
- [ ] `LINEAR_API_KEY` — Linear API key (from Settings → API)
- [ ] `LINEAR_TEAM_ID` — Team ID (from Linear URL or API)
- [ ] `LINEAR_REVENUE_PROJECT_ID` — Revenue project ID

## Supabase
- [ ] `SUPABASE_URL` — Project URL (e.g., https://xxxx.supabase.co)
- [ ] `SUPABASE_ANON_KEY` — Public anon key
- [ ] `SUPABASE_SERVICE_ROLE_KEY` — Service role key (admin access)
- [ ] `SUPABASE_DB_URL` — Direct Postgres connection string

## Hugging Face
- [ ] `HF_TOKEN` — Hugging Face user access token
- [ ] `HUGGINGFACE_API_KEY` — Same as HF_TOKEN or org token

---

## Supabase Table Schema (run in SQL editor)

```sql
-- gc_ledger: primary revenue ledger
CREATE TABLE IF NOT EXISTS gc_ledger (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  source TEXT NOT NULL,
  amount NUMERIC(12,2) NOT NULL DEFAULT 0,
  currency TEXT DEFAULT 'USD',
  reference_id TEXT,
  customer_email TEXT,
  metadata JSONB,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- revenue_events: real-time event stream
CREATE TABLE IF NOT EXISTS revenue_events (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  event_type TEXT NOT NULL,
  amount NUMERIC(12,2),
  source TEXT,
  ledger_id UUID REFERENCES gc_ledger(id),
  timestamp TIMESTAMPTZ DEFAULT now()
);

-- leads: enriched lead CRM
CREATE TABLE IF NOT EXISTS leads (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  email TEXT,
  company TEXT,
  title TEXT,
  source TEXT,
  score NUMERIC,
  hf_score TEXT,
  status TEXT DEFAULT 'new',
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable realtime
ALTER PUBLICATION supabase_realtime ADD TABLE gc_ledger;
ALTER PUBLICATION supabase_realtime ADD TABLE revenue_events;
```
