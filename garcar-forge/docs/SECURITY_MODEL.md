# Garcar Forge Security Model — v0.2 foundation

## Trust boundaries

- The host OS and container engine are privileged infrastructure.
- The API is a privileged control plane. Compose binds it to loopback only.
- The operator bearer token is a bootstrap credential. Store it outside source control and rotate it.
- Job payloads and artifact identifiers are untrusted input.
- The event ledger is tamper-evident by hash chaining, not certified WORM storage. A host administrator can alter the database and recompute hashes. Separately retain signed/exported chain heads to detect truncation.

## Enforced controls

1. Management routes require a bearer token of at least 32 characters.
2. Missing or weak token configuration fails closed.
3. Deployment plan artifacts must use a SHA-256 digest.
4. Only explicit dry-run deployment plans are accepted.
5. Only the internal ledger.verify job is accepted by the job queue.
6. Job idempotency keys cannot be reused for a different task or payload.
7. Deployment execution always returns HTTP 423.
8. Containers run as non-root, with read-only root filesystems, dropped capabilities, and no-new-privileges.
9. Host preflight checks local prerequisites but does not start or change services.
10. The scheduler is disabled by default.

## Not implemented yet

- Passkey/WebAuthn authentication and multi-user RBAC.
- mTLS host enrollment and signed host identity.
- Vault secret leasing.
- PostgreSQL-backed multi-node job and metadata store.
- External immutable backups and restore drills.
- Artifact signature verification and policy attestations.
- Rate limiting, IDS, automated credential rotation.
- Real deployment execution, rollback, and production kill-switch integration.

## Release gate

Do not expose the API publicly or enable execution until these controls are implemented, tested, independently reviewed, and documented. A passing unit suite is not production certification.
