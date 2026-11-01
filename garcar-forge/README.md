# Garcar Forge

Garcar Forge is the self-managed control-plane foundation for Garcar Enterprise. It is designed to run on a single Linux host first, then expand to multiple hosts without making Railway, Vercel, or another hosting vendor a required control plane.

## Release scope

- FastAPI control API with public liveness/readiness probes.
- Operator-token authentication for management routes.
- SQLite event ledger with a SHA-256 hash chain and verification endpoint.
- Deployment-plan endpoint that accepts dry-run plans only.
- Execution endpoint that is deliberately locked.
- Non-root Docker image, localhost-only Compose binding, automated tests and CI.

## Explicit limitations

This is a foundation, not a production orchestration platform. It does not yet schedule containers, provision servers, run workers, manage DNS, integrate Vault, connect to Supabase, or process payments. The ledger is tamper-evident, not certified WORM storage. SQLite is suitable for a single-node canary, not a multi-node control plane.

No secrets are committed. No live services are changed by this repository. Live execution remains disabled by design.

## Quick start

1. Install Docker Engine and the Compose plugin on a Linux host.
2. Copy .env.example to .env.
3. Generate a strong operator token locally with openssl rand -hex 32 and put it in .env.
4. Run docker compose up --build -d.
5. Check http://127.0.0.1:8080/healthz and http://127.0.0.1:8080/readyz.
6. Use the operator token for management routes. Do not expose port 8080 publicly until TLS, network policy, token rotation, backups, and a security review are complete.

## API

- GET /healthz — liveness probe.
- GET /readyz — checks that the local ledger is available.
- GET /v1/status — authenticated status.
- POST /v1/plans — records a dry-run deployment plan; dry_run must be true.
- POST /v1/deployments/execute — returns HTTP 423 while execution is disabled.
- GET /v1/ledger/verify — authenticated hash-chain verification.
- GET /v1/ledger/events — authenticated recent ledger events.

Management requests use Authorization: Bearer <GARCAR_OPERATOR_TOKEN>.

## Local development

    python -m venv .venv
    . .venv/bin/activate
    pip install -e '.[dev]'
    GARCAR_OPERATOR_TOKEN=local-test-token uvicorn app.main:app --host 127.0.0.1 --port 8080
    pytest

## Next milestones

1. Add signed deployment manifests and artifact digest verification.
2. Add a separate approval service and policy evaluation; keep execution disabled.
3. Add PostgreSQL as the multi-node metadata store and object storage for immutable snapshots.
4. Add an isolated worker runtime with a strict job allowlist.
5. Add host enrollment, mTLS, audit backup/restore drills, and disaster recovery.
6. Only after independent security review, add a bounded canary executor with rollback and kill switch.

## Security defaults

- Bind to localhost in Compose.
- Run as a non-root container user.
- Require an operator token for management routes.
- Fail closed if the operator token is absent.
- Reject non-dry-run deployment plans.
- Keep execution locked regardless of request content.
- Never place credentials in source control.
