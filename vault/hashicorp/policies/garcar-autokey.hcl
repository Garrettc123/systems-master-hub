# Garcar AutoKey — least-privilege policy
# vault policy write garcar-autokey vault/hashicorp/policies/garcar-autokey.hcl

path "secret/data/garcar/*" {
  capabilities = ["create", "update", "read", "list"]
}

path "secret/metadata/garcar/*" {
  capabilities = ["read", "list", "delete"]
}

path "sys/health" {
  capabilities = ["read"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}
