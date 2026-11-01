# Garcar Forge Security Model — Foundation Release

## Trust boundaries

- The host operating system and Docker daemon are trusted infrastructure.
- The Forge API is a privileged control-plane component and must not be exposed publicly in this release.
- The operator bearer token is a bootstrap control credential. Store it outside source control, rotate it, and restrict access to it.
- Request bodies and repository artifacts are untrusted input.
- The event ledger is tamper-evident by hash chaining, but a privileged host operator can still alter the database and recompute the chain.

## Enforced controls

1. Management endpoints require a configured operator token.
2. Missing operator-token configuration fails closed.
3. Deployment plans must explicitly set dry_run to true.
4. The execution endpoint always returns HTTP 423.
5. The container runs as a non-root user.
6. Compose binds the API to loopback only.
7. The container drops Linux capabilities and enables no-new-privileges.
8. No secrets are embedded in the image or repository.

## Not yet implemented

- WebAuthn/passkey authentication.
- mTLS and host identity.
- Vault integration and secret leasing.
- Multi-user RBAC and dual approval.
- Signed artifact provenance and policy attestation.
- External immutable/WORM backup.
- Rate limiting, intrusion detection, and key rotation automation.
- Multi-node consensus or PostgreSQL-backed ledger.

## Release gate

Do not expose the API publicly or enable execution until the missing controls have been implemented, tested, reviewed, and documented. A passing unit test suite alone is not production certification.
