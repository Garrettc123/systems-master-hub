# Garcar Max-Security Engine

## Included controls

- Deny-by-default authorization with explicit principal/action grants.
- Separate administrator provisioning key required for permission grants; never expose provisioning to untrusted callers.
- A single `authorize_operation()` gate that completes request verification, rate limiting, permission checks, and audit logging before the caller performs a side effect.
- Constant-time bearer-token comparison; configured bearer tokens and HMAC keys must each be at least 32 bytes.
- HMAC-SHA256 request signatures bound to method, path, timestamp, nonce, and SHA-256 body digest.
- Strict timestamp type/range validation, timestamp-window enforcement, and persistent one-time nonce consumption to reject replay.
- Strict HTTP method, path, nonce, signature, and body validation.
- Configurable request-body ceiling.
- Persistent fixed-window rate limiting with subject identifiers stored as SHA-256 digests.
- SQLite WAL with FULL synchronous durability for the local evidence store.
- SHA-256 hash-chained audit records; chain verification fails closed.
- Missing secrets, unavailable replay/rate-limit stores, failed authorization, or failed audit writes deny the protected operation.

## Configuration

Set `GARCAR_BEARER_TOKEN`, `GARCAR_SIGNING_KEY`, and `GARCAR_PERMISSION_ADMIN_KEY` through the existing secret manager or protected runtime environment. Each value must contain at least 32 bytes of cryptographically random material. This change does not create, rotate, or overwrite any existing production secret. Do not commit secrets, print them in logs, rotate them automatically, or replace existing production secrets as part of this change.

Example local-only setup (generate values in a trusted environment; do not paste them into source control):

```sh
export GARCAR_BEARER_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export GARCAR_SIGNING_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export GARCAR_PERMISSION_ADMIN_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
```

Instantiate with `load_config_from_environment()`. Use `sign_request()` on the trusted client side. At the receiving boundary, call `authorize_operation()` before any side effect; it runs request verification, replay protection, rate limiting, authorization, and a final audit append. The method returns an audit receipt and does not execute the operation. The caller must not perform a side effect if it raises `SecurityDenied`. Permission provisioning requires the separate `admin_key` and is a local administrative operation; do not expose it through HTTP, agent tools, or user-controlled workflows.

## Security boundaries and limitations

This is a reusable security primitive, not a claim of complete or maximum security. It does not itself provide TLS, WebAuthn/passkeys, MFA, network firewalling, process isolation, secure key storage, distributed rate limiting, remote immutable/WORM audit retention, backup restoration, or independent penetration testing. The SQLite hash chain detects record edits but is not immutable: an attacker able to rewrite the entire database can recompute the chain. External signed checkpoints, separately administered immutable/WORM storage, and independent key custody are still required for stronger tamper evidence. This repository change does not implement or claim remote anchoring.

Do not connect this module to production execution, payment, email, deployment, or public endpoints until code review, CI, threat modeling, integration tests, key custody, recovery testing, and operator approval are complete. Existing secrets and live settings must remain unchanged. The unit tests must be run in an isolated environment; a GitHub commit is not evidence that tests passed.


## Hardening branch scope

The follow-up hardening branch adds strict input validation, explicit administrator-key checks for permission provisioning, concurrent replay/rate-limit tests, and a complete authorization gate. `authorize_operation()` only authorizes and returns an audit receipt; it does not execute protected work.

## Remaining full-scale controls

The following are intentionally not represented as implemented or verified:

- WebAuthn/passkeys and MFA integration.
- TLS termination, network segmentation, host/process isolation, and workload identity.
- External signed audit checkpoints and independently administered WORM retention.
- Backup restore drills, key escrow/recovery, and disaster-recovery objectives.
- Distributed rate limiting across multiple hosts.
- Service-by-service middleware integration and negative integration tests.
- Independent penetration test, threat-model sign-off, and production approval.

A local SQLite database is a single-host control and must not be treated as a distributed security authority.
