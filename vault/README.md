# Garcar HashiCorp Vault — Unprecedented Zero-Touch Secrets

**You should not touch secret values for ongoing operations.**

- Vault = source of truth  
- GitHub Actions secrets = distribution mirror  
- Internals (`AUTOKEY_*`, `INTERNAL_API_TOKEN`, `WEBHOOK_SIGNING_SECRET`) = auto-generated forever  
- Externals (Stripe, Apollo, …) = set **once** in GitHub or Vault, then never again  

## Unprecedented abilities

| Ability | How |
|---------|-----|
| No `.vault.env` edits in ops | `ingest_from_github.py` lifts Actions secrets → Vault |
| No hand rotation | `rotate_internal.py` every schedule |
| No per-repo copy-paste | `sync_to_github.py` + `manifest.json` |
| Works without Vault | `ensure_github_only.py` still mints internals |
| Single button | Workflow mode `full` = ingest + rotate + sync |

## Bootstrap once (minimal human surface)

### Option A — You already put secrets in GitHub Actions

1. Set only control-plane secrets on **systems-master-hub**:
   - `VAULT_ADDR`, `VAULT_ROLE_ID`, `VAULT_SECRET_ID` (from `bootstrap.sh`)
   - `GHPAT` (secrets:write on target repos)
   - Any external keys you already use (`STRIPE_*`, `SUPABASE_*`, …) **once** in this repo’s Actions secrets  
2. Run workflow **Garcar Vault GitHub Sync** → mode **`full`**.  
3. Ingest copies them into Vault; sync fans out to every repo in the manifest.  
4. Stop touching secrets.

### Option B — Seed from file once

```bash
docker compose -f vault/docker-compose.vault.yml up -d
export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=garcar-root-dev-token
bash vault/hashicorp/bootstrap.sh
cp vault/.vault.env.template vault/.vault.env   # fill once
pip install -r vault/hashicorp/requirements.txt
python vault/hashicorp/seed_from_env.py
python vault/hashicorp/zero_touch.py full
```

Put AppRole + `GHPAT` into hub Actions secrets. Delete local `.vault.env` when done.

## Ongoing (hands off)

| Schedule / mode | Behavior |
|-----------------|----------|
| Every 6 hours | `full`: ingest (non-destructive) → rotate internals → sync |
| `full` | Same as schedule |
| `ingest` | CI env → Vault (skip if already set) → rotate → sync |
| `ensure` / `rotate` | Internals only → sync |
| `sync` | Vault → GitHub only |
| `dry_run` | Log only |
| `github_only` | No Vault; mint internals on GitHub |

## Scripts

| File | Role |
|------|------|
| `zero_touch.py` | Orchestrator |
| `ingest_from_github.py` | Actions/env → Vault |
| `seed_from_env.py` | File → Vault (optional once) |
| `rotate_internal.py` | Auto generators |
| `sync_to_github.py` | Vault → all repos |
| `ensure_github_only.py` | Internals without Vault |
| `client.py` / `bootstrap.sh` / `manifest.json` | Core |

## Hard rule

External vendor keys cannot be invented. Put Stripe/Apollo/cloud tokens **once** (GitHub or seed file). After that, automation owns distribution and internal rotation — **do not touch secrets**.
