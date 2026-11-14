# Garcar Forge

Garcar Forge is a self-managed control-plane foundation for Garcar Enterprise. It runs on a Linux host or Android Termux for local development and can later expand to multiple hosts. Railway and Vercel are not required to operate this service.

## v0.2 scope

- FastAPI control API with liveness/readiness checks.
- Operator bearer authentication with fail-closed configuration.
- SHA-256 chained SQLite audit ledger.
- Strict dry-run deployment plans; live execution is hard-locked.
- Durable SQLite job queue with idempotency and one allowlisted internal task: ledger.verify.
- Separate worker and scheduler processes; scheduler is disabled by default.
- Bounded worker lease recovery and retry cap.
- Verified local backup/restore with a manifest, file hash, and explicit restore confirmation.
- Hardened Docker Compose deployment and Termux start/stop scripts.
- Host preflight, local CI runner, end-to-end smoke test, and unit tests.

This is a single-host canary foundation, not a complete production orchestrator. It does not yet provision hosts, deploy arbitrary workloads, manage DNS, integrate Vault, or perform payments. SQLite is not suitable for multi-host concurrency. Ledger hash chaining is tamper-evident but not certified WORM storage.

## Linux + Docker

1. Install Docker Engine and the Compose plugin.
2. Copy .env.example to .env and replace the operator token with a unique 64-character random value. Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'.
3. Run make preflight. This does not start or modify containers.
4. Run docker compose up --build -d.
5. Verify curl http://127.0.0.1:8080/healthz and curl http://127.0.0.1:8080/readyz.
6. Run make ci and bash scripts/e2e-smoke.sh for application-level validation.
7. Do not expose port 8080 publicly until TLS, network policy, token rotation, external backups, and security review are complete.

Compose starts three processes sharing a persistent single-host volume: API, worker, and scheduler. The scheduler remains disabled unless explicitly enabled in .env; even when enabled, it only queues the internal ledger verification task.

## Android Termux

From the repository root, run bash scripts/termux.sh install, then bash scripts/termux.sh start. Use status, logs, and stop to manage processes. The API binds to localhost only. This is suitable for a local node/canary, not an always-on production server or public endpoint.

## Backups and restore

Create a consistent backup with python -m app.backup create. Verify it with python -m app.backup verify ./backups/garcar-forge-<timestamp>.sqlite3. Restore only while all services are stopped, to an unused destination path, using python -m app.backup restore <backup.sqlite3> --target ./data/restored.sqlite3 --confirm-restore. The restore command checks the manifest and digest, refuses to overwrite an existing database, and verifies the restored ledger. Store backup files and manifests away from the host for disaster recovery; these commands create local backups only.

## API

Management requests use Authorization: Bearer <GARCAR_OPERATOR_TOKEN>.

- GET /healthz — liveness.
- GET /readyz — database reachability and ledger integrity.
- GET /v1/status — authenticated state and policy.
- POST /v1/plans — accepts only dry-run plans with sha256:<64 hex> artifact digest.
- POST /v1/jobs — accepts only dry-run ledger.verify tasks with an idempotency key.
- GET /v1/jobs/{job_id} — inspect job state.
- GET /v1/ledger/verify — verify event hash chain.
- GET /v1/ledger/events — recent events.
- POST /v1/deployments/execute — always returns HTTP 423.

## Local development

    python -m venv .venv
    . .venv/bin/activate
    pip install -e '.[dev]'
    export GARCAR_OPERATOR_TOKEN="$(python -c 'import secrets; print(secrets.token_hex(32))')"
    make ci
    bash scripts/e2e-smoke.sh

## Next production milestones

1. Separate approval service with dual control and passkey/WebAuthn identity.
2. Vault secret leasing and mTLS host enrollment.
3. PostgreSQL for multi-host metadata and queue; object storage for artifacts.
4. Signed artifacts, attestation, policy evaluation and constrained deployments.
5. Externally stored immutable backups, restore exercises, monitoring, rollback and independent security review.
