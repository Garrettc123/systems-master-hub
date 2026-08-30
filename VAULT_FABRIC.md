# Garcar Unprecedented Vault Fabric — Multi-Repo Map

Single Vault instance. Shared paths under `secret/data/garcar/*`.
JWT role `garcar-github-actions` bound to all listed repos.

## Control plane (source of truth)

| Repo | Role |
|------|------|
| **autonomous-butler-core** | Bootstrap, Automater, Injector, Waypoint, policies |

## Consumer repos (Vault-native CI)

| Repo | Primary paths |
|------|----------------|
| NEXUS-AI-CORE | ai, stripe, github, slack, supabase, enrichment, infra |
| apex-revenue-system | stripe, ai, enrichment, github, slack |
| lead-enrichment-engine | enrichment, apollo, hubspot, ai, github |
| garcar-payments | stripe, base, github, slack |

## Activation (once)

```bash
cd autonomous-butler-core
export VAULT_ADDR=... VAULT_TOKEN=...
./vault/automater/automate-all.sh
# write real secrets into secret/garcar/*
```

Then add **only** `VAULT_ADDR` to Actions secrets in **every** consumer repo.

## JWT role bound repositories

Update the role if you add more repos:

```bash
vault write auth/jwt/role/garcar-github-actions \
  role_type=jwt \
  bound_audiences="https://github.com/Garrettc123" \
  bound_claims_type=glob \
  bound_claims='{"repository":["Garrettc123/autonomous-butler-core","Garrettc123/NEXUS-AI-CORE","Garrettc123/apex-revenue-system","Garrettc123/lead-enrichment-engine","Garrettc123/garcar-payments"]}' \
  user_claim=repository \
  token_policies=garcar-github-actions \
  token_ttl=15m
```
