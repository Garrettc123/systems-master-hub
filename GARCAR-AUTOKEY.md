# Garcar Master Autokey System

**Preferred path: HashiCorp Vault → GitHub Secrets**  
Fallback: manual secrets in systems-master-hub only.

See **[docs/HASHICORP-VAULT.md](docs/HASHICORP-VAULT.md)** for the full Vault implementation.

---

## How it works

1. **HashiCorp Vault** stores every secret under `secret/garcar/*` (readable, rotatable, auditable).
2. **Vault → GitHub Sync** (`garcar-vault-sync.yml` or `sync_to_github.py`) pushes keys into commercial repos.
3. **Agents / workflows** read secrets only from the GitHub Actions environment at runtime.

GitHub secrets remain write-mostly. Vault is the only place values can be read back.

---

## Activation (Vault path — recommended)

```bash
# Local
docker compose -f docker-compose.vault.yml up -d
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=garcar-dev-root-token
bash vault/hashicorp/bootstrap.sh

cp vault/.vault.env.template vault/.vault.env
# fill keys
pip install -r vault/hashicorp/requirements.txt
python vault/hashicorp/seed_from_env.py
python vault/hashicorp/sync_to_github.py
```

Production: point `VAULT_ADDR` at your cluster, store AppRole credentials in systems-master-hub, run **Garcar Vault → GitHub Sync** with `SYNC`.

---

## Fallback (GitHub-only)

Add secrets only at:
https://github.com/Garrettc123/systems-master-hub/settings/secrets/actions

Then run:
- `garcar-autokey-propagate.yml` with `PROPAGATE`, or
- `garcar-autokey-inventory-propagate.yml` with `PROPAGATE`

### Required for revenue
| Secret | Purpose |
|--------|---------|
| `APOLLO_API_KEY` | Wealth loop lead source |
| `STRIPE_SECRET_KEY` | Payment links |
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` | Agent ledger |
| `GHPAT` | Propagation |
| `RAILWAY_TOKEN` | Deploys |

Full list: `vault/.vault.env.template` and `vault/hashicorp/sync_to_github.py`.

---

## Runtime contract

```python
from providers.router import build_router_from_env
router = build_router_from_env()  # only providers with keys registered
```

No hard-coded keys. Vault is truth. Autokey distributes.
