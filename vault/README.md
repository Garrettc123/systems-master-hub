# Garcar HashiCorp Vault — Zero-Touch Secrets

**Vault is the only place humans put secrets. GitHub Actions Secrets is a mirror.**

After a one-time bootstrap + seed, you never touch keys again. The `Garcar Vault GitHub Sync` workflow rotates internal keys and propagates everything to every mapped repo every 6 hours.

## Architecture

```
.vault.env  ──(seed once)──►  HashiCorp Vault KV v2  ──(sync)──►  GitHub Secrets
                                  secret/garcar/*                    per-repo map
                                       ▲
                                       │ AppRole (CI)
                                  GitHub Actions
```

## One-time setup (you do this once)

### A. Start Vault (dev) or point at HCP / self-hosted

```bash
docker compose -f vault/docker-compose.vault.yml up -d
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=garcar-root-dev-token
```

Production: set `VAULT_ADDR` to your HCP or HA cluster and use a root/admin token only for bootstrap.

### B. Bootstrap policy + AppRole

```bash
bash vault/hashicorp/bootstrap.sh
# prints VAULT_ROLE_ID + VAULT_SECRET_ID
```

Add to **systems-master-hub** → Settings → Secrets → Actions:

| Secret | Purpose |
|--------|---------|
| `VAULT_ADDR` | Vault URL |
| `VAULT_ROLE_ID` | AppRole for CI |
| `VAULT_SECRET_ID` | AppRole secret |
| `GHPAT` | PAT with `secrets:write` on all target repos |

Do **not** store root `VAULT_TOKEN` in GitHub long-term.

### C. Seed all keys once

```bash
cp vault/.vault.env.template vault/.vault.env
# edit .vault.env — Stripe, Apollo, Supabase, OpenAI, Railway, etc.
export VAULT_ADDR=... VAULT_TOKEN=...   # or AppRole
pip install -r vault/hashicorp/requirements.txt
python vault/hashicorp/seed_from_env.py
python vault/hashicorp/rotate_internal.py   # generates AUTOKEY_* etc.
python vault/hashicorp/sync_to_github.py    # pushes to every repo in manifest
```

`.vault.env` is gitignored. Never commit it.

## Ongoing (hands-off)

| Trigger | What happens |
|---------|----------------|
| Schedule every 6h | Rotate internal keys → sync all repos |
| Workflow dispatch `sync` | Propagate current Vault → GitHub |
| Workflow dispatch `rotate_and_sync` | Rotate internals then sync |
| Workflow dispatch `dry_run` | Log only |

Workflow: `.github/workflows/garcar-vault-sync.yml`

## Manifest

`vault/hashicorp/manifest.json` defines:

- Every secret name + plane (revenue / ai / app / deploy / edge / internal)
- Which repos receive which keys
- Aliases (`PAT_TOKEN` ← `GHPAT`, `SUPABASE_KEY` ← `SUPABASE_SERVICE_KEY`)
- Which keys are auto-rotatable

Edit the manifest when you add a repo or secret; next sync applies it.

## Scripts

| Script | Role |
|--------|------|
| `hashicorp/bootstrap.sh` | KV v2 + policy + AppRole |
| `hashicorp/seed_from_env.py` | Load `.vault.env` → Vault |
| `hashicorp/rotate_internal.py` | Regenerate internal tokens |
| `hashicorp/sync_to_github.py` | Vault → GitHub sealed secrets |
| `hashicorp/client.py` | Shared hvac client |
| `rotate-secrets.sh` / `validate-secrets.sh` | Legacy shell helpers |

## Security notes

- External keys (Stripe, Apollo, cloud PATs) **cannot** be invented — put them in Vault once via seed.
- Internal keys (`AUTOKEY_*`, `INTERNAL_API_TOKEN`, `WEBHOOK_SIGNING_SECRET`) rotate automatically.
- AppRole token TTL is 1h; CI authenticates per run.
- Public Safety Gate blocks committed private keys; keep material only in Vault.
