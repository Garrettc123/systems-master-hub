# Garcar AutoKey — least-privilege policy for the synchronizer
# Apply with:
#   vault policy write garcar-autokey vault/hashicorp/policies/garcar-autokey.hcl

# Read + list the entire Garcar KV namespace
path "secret/data/garcar/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/garcar/*" {
  capabilities = ["read", "list"]
}

# Allow the seeder / rotation job to write (optional — split into two policies in production)
path "secret/data/garcar/*" {
  capabilities = ["create", "update", "read", "list"]
}

# Health & token lookup
path "sys/health" {
  capabilities = ["read"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}
