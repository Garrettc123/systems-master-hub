# Garcar Max-Security Engine

## Included controls

- Deny-by-default authorization with explicit principal/action grants.
- Constant-time bearer-token comparison; configured bearer tokens and HMAC keys must each be at least 32 bytes.
- HMAC-SHA256 request signatures bound to method, path, timestamp, nonce, and SHA-256 body digest.
- Timestamp-window enforcement and persistent one-time nonce consumption to reject replay.
- Configurable request-body ceiling.
- Persistent fixed-window rate limiting with subject identifiers stored as SHA-256 digests.
- SQLite WAL with FULL synchronous durability for the local evidence store.
- SHA-256 hash-chained audit records; chain verification fails closed.
- Missing secrets, unavailable replay/rate-limit stores, failed authorization, or failed audit writes deny the protected operation.

## Configuration

Set `GARCAR_BEARER_TOKEN` and `GARCAR_SIGNING_KEY` through the existing secret manager or protected runtime environment. Each value must contain at least 32 bytes of cryptographically random material. Do not commit secrets, print them in logs, rotate them automatically, or replace existing production secrets as part of this change.

Example local-only setup (generate values in a trusted environment; do not paste them into source control):

```sh
export GARCAR_BEARER_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export GARCAR_SIGNING_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
```

Instantiate with `load_config_from_environment()`. Use `sign_request()` on the trusted client side and `verify_request()` at the receiving boundary. Call `consume_rate_limit()` and `require_permission()` before each protected operation. Permission grants are administrative provisioning operations and must never be exposed to untrusted callers.

## Security boundaries and limitations

This is a reusable security primitive, not a claim of complete or maximum security. It does not itself provide TLS, WebAuthn/passkeys, MFA, network firewalling, process isolation, secure key storage, distributed rate limiting, remote immutable/WORM audit retention, backup restoration, or independent penetration testing. The SQLite hash chain detects accidental or unsophisticated record edits, but an attacker able to rewrite the entire database can recompute the chain; periodically anchor signed checkpoints in a separately administered immutable store before treating the ledger as independently tamper-resistant.

Do not connect this module to production execution, payment, email, deployment, or public endpoints until code review, CI, threat modeling, integration tests, key custody, and operator approval are complete. Existing secrets and live settings must remain unchanged.
