# HashiCorp Vault Integration — Garcar Enterprise

**Vault is the single source of truth.**  
GitHub Actions secrets are only the distribution / runtime plane.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              HashiCorp Vault (KV v2)                     │
│              secret/garcar/*                             │
│  APOLLO_API_KEY | STRIPE_* | SUPABASE_* | OPENAI_* …     │
└──────────────────────────┬──────────────────────────────┘
                           │  vault/hashicorp/sync_to_github.py
                           ▼
┌─────────────────────────────────────────────────────────┐
│         systems-master-hub  (GitHub Secrets)             │
│         + all commercial repos                           │
└──────────────────────────┬──────────────────────────────┘
                           │  GitHub Actions runtime
                           ▼
              Wealth Loop / Lead Agent / Deploys
```

---

## One-Time Activation

### 1. Deploy / point at a Vault cluster

Any of:
- HashiCorp Cloud Platform (HCP Vault)
- Self-hosted Vault on Railway / Fly / K8s
- Existing company Vault

Set these in **systems-master-hub** GitHub secrets:

| Secret | Purpose |
|--------|---------|
| `VAULT_ADDR` | e.g. `https://vault.garcar.io:8200` |
| `VAULT_TOKEN` | Root or high-privilege token (bootstrap only) |
| *or* `VAULT_ROLE_ID` + `VAULT_SECRET_ID` | Preferred AppRole for CI |

### 2. Enable KV v2 and policy

```bash
export VAULT_ADDR=https://your-vault:8200
export VAULT_TOKEN=hvs....

vault secrets enable -path=secret kv-v2
vault policy write garcar-autokey vault/hashicorp/policies/garcar-autokey.hcl

# Optional AppRole for GitHub Actions
vault auth enable approle
vault write auth/approle/role/garcar-autokey \
  token_policies="garcar-autokey" \
  token_ttl=1h token_max_ttl=4h
```

### 3. Seed secrets into Vault (one time)

```bash
cp vault/.vault.env.template vault/.vault.env
# fill every real value

export VAULT_ADDR=...
export VAULT_TOKEN=...
pip install -r vault/hashicorp/requirements.txt
python vault/hashicorp/seed_from_env.py
```

Every non-empty key is written to `secret/garcar/<KEY>` with field `value`.

### 4. Sync to GitHub

Manual:
```bash
python vault/hashicorp/sync_to_github.py
```

Or via Actions:
https://github.com/Garrettc123/systems-master-hub/actions/workflows/garcar-vault-sync.yml  
→ Run workflow → type `SYNC`

The workflow also runs every 6 hours on schedule.

---

## Day-2 Operations

| Action | Command / Location |
|--------|--------------------|
| Rotate a key | Update in Vault UI / CLI → next sync pushes it |
| Add a new key | Write to `secret/garcar/NEW_KEY` → add name to `CANONICAL_KEYS` in `sync_to_github.py` |
| Audit who read | Vault audit log |
| Emergency revoke | `vault token revoke` / AppRole secret_id rotate |

---

## Why This Solves the Previous Blocker

- GitHub secrets are **write-only** (values cannot be read back).
- HashiCorp Vault is **read/write** with full audit and versioning.
- The wealth loop (and every other agent) can now be unblocked by:
  1. Putting `APOLLO_API_KEY` (and the rest) into Vault once
  2. Running the Vault → GitHub sync
  3. Re-triggering the wealth agent

**Vault holds the truth. Autokey distributes it. Agents consume it.**
