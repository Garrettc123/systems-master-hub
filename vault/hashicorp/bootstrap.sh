#!/usr/bin/env bash
# Garcar HashiCorp Vault bootstrap — run once against a live Vault.
# Requires: vault CLI, VAULT_ADDR, VAULT_TOKEN (root or policy-admin)
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
log() { echo -e "[*] $1"; }
ok()  { echo -e "${GREEN}[✓]${NC} $1"; }
err() { echo -e "${RED}[✗]${NC} $1"; }

if [ -z "${VAULT_ADDR:-}" ]; then err "VAULT_ADDR is required"; exit 1; fi
if [ -z "${VAULT_TOKEN:-}" ]; then err "VAULT_TOKEN is required"; exit 1; fi
if ! command -v vault &>/dev/null; then
  err "vault CLI not found: https://developer.hashicorp.com/vault/docs/install"
  exit 1
fi

export VAULT_ADDR VAULT_TOKEN

log "Checking Vault health…"
vault status >/dev/null || { err "Vault not reachable at $VAULT_ADDR"; exit 1; }
ok "Vault is up"

if vault secrets list -format=json 2>/dev/null | grep -q '"secret/"'; then
  ok "KV mount secret/ already present"
else
  log "Enabling KV v2 at secret/"
  vault secrets enable -path=secret kv-v2
  ok "KV v2 enabled"
fi

POLICY_FILE="$(cd "$(dirname "$0")" && pwd)/policies/garcar-autokey.hcl"
if [ -f "$POLICY_FILE" ]; then
  vault policy write garcar-autokey "$POLICY_FILE"
  ok "Policy garcar-autokey written"
else
  err "Policy file missing: $POLICY_FILE"
  exit 1
fi

if vault auth list -format=json 2>/dev/null | grep -q '"approle/"'; then
  ok "AppRole auth already enabled"
else
  vault auth enable approle
  ok "AppRole auth enabled"
fi

vault write auth/approle/role/garcar-autokey \
  token_policies="garcar-autokey" \
  token_ttl=1h \
  token_max_ttl=4h \
  secret_id_ttl=0 \
  secret_id_num_uses=0

ok "AppRole role/garcar-autokey configured"

ROLE_ID=$(vault read -field=role_id auth/approle/role/garcar-autokey/role-id)
SECRET_ID=$(vault write -field=secret_id -f auth/approle/role/garcar-autokey/secret-id)

echo ""
echo "=============================================="
echo " GARCAR VAULT BOOTSTRAP COMPLETE"
echo "=============================================="
echo "VAULT_ADDR=$VAULT_ADDR"
echo "VAULT_ROLE_ID=$ROLE_ID"
echo "VAULT_SECRET_ID=$SECRET_ID"
echo ""
echo "Add ONLY these to systems-master-hub GitHub Actions secrets:"
echo "  VAULT_ADDR"
echo "  VAULT_ROLE_ID"
echo "  VAULT_SECRET_ID"
echo "  GHPAT   (fine-grained PAT: secrets write on target repos)"
echo ""
echo "Then seed once:"
echo "  cp vault/.vault.env.template vault/.vault.env   # fill values"
echo "  python vault/hashicorp/seed_from_env.py"
echo "  python vault/hashicorp/rotate_internal.py"
echo "  python vault/hashicorp/sync_to_github.py"
echo "After that, workflow 'Garcar Vault GitHub Sync' keeps everything in sync."
echo "=============================================="
