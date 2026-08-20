# HashiCorp Vault — Full Implementation (Garcar Enterprise)

**Vault = source of truth**  
**GitHub Secrets = runtime distribution plane**  
**Agents / Wealth Loop = consumers**

---

## Quick Start (Local Dev — 5 minutes)

```bash
# 1. Start Vault
docker compose -f docker-compose.vault.yml up -d

# 2. Bootstrap policy + AppRole
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=garcar-dev-root-token
bash vault/hashicorp/bootstrap.sh
# → prints VAULT_ROLE_ID and VAULT_SECRET_ID

# 3. Seed secrets
cp vault/.vault.env.template vault/.vault.env
# edit vault/.vault.env with real keys (APOLLO, STRIPE, SUPABASE, …)
pip install -r vault/hashicorp/requirements.txt
python vault/hashicorp/seed_from_env.py

# 4. Distribute to GitHub
export GHPAT=ghp_your_pat_with_secrets_scope
python vault/hashicorp/sync_to_github.py
```

Then re-run the Wealth Agent. The `APOLLO_API_KEY` blocker is gone if the key was seeded.

---

## Production Activation

### A. Vault cluster
Use HCP Vault, self-hosted, or managed. Note `VAULT_ADDR`.

### B. Bootstrap once
```bash
export VAULT_ADDR=https://vault.yourdomain.com:8200
export VAULT_TOKEN=<privileged-token>
bash vault/hashicorp/bootstrap.sh
```

### C. GitHub secrets (systems-master-hub only)
| Secret | Required |
|--------|----------|
| `VAULT_ADDR` | Yes |
| `VAULT_ROLE_ID` | Yes (preferred) |
| `VAULT_SECRET_ID` | Yes (preferred) |
| `VAULT_TOKEN` | Bootstrap only |
| `GHPAT` | Yes (for `gh secret set`) |

### D. Seed production keys
Same as local: fill `vault/.vault.env` → `seed_from_env.py`

Or write via CLI:
```bash
vault kv put secret/garcar/APOLLO_API_KEY value="your-apollo-key"
vault kv put secret/garcar/STRIPE_SECRET_KEY value="sk_live_..."
# … every canonical key
```

### E. Sync on demand or schedule
Actions → **Garcar Vault → GitHub Sync** → type `SYNC`  
(or wait for the 6-hour cron)

---

## Canonical Key List (`secret/garcar/<KEY>`)

Revenue-critical:
- `APOLLO_API_KEY` ← unblocks wealth loop
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_*`
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_ANON_KEY`

Platform:
- `GHPAT`, `RAILWAY_TOKEN`, `VERCEL_TOKEN`
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `PERPLEXITY_API_KEY`
- `HUBSPOT_API_KEY`, `LINEAR_API_KEY`, `SLACK_WEBHOOK_URL`

Full list lives in `vault/hashicorp/sync_to_github.py` → `CANONICAL_KEYS`.

---

## File Map

| Path | Role |
|------|------|
| `docker-compose.vault.yml` | Local Vault |
| `vault/hashicorp/bootstrap.sh` | Policy + AppRole |
| `vault/hashicorp/client.py` | KV v2 client |
| `vault/hashicorp/seed_from_env.py` | .vault.env → Vault |
| `vault/hashicorp/sync_to_github.py` | Vault → GitHub secrets |
| `vault/hashicorp/policies/garcar-autokey.hcl` | Least privilege |
| `.github/workflows/garcar-vault-sync.yml` | Scheduled + manual sync |
| `docs/HASHICORP-VAULT.md` | This runbook |

---

## End-to-End: Unblock Revenue

1. Seed `APOLLO_API_KEY` (and friends) into Vault  
2. Run Vault → GitHub sync  
3. Trigger `wealth-agent.yml`  
4. Expect: payment links generated, no more `BLOCKED: missing required secrets`

**Vault holds the truth. Autokey distributes. Agents earn.**
