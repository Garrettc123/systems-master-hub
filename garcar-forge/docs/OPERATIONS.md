# Garcar Forge Operations — v0.2

## Linux host with Docker

1. Install Docker Engine and the Compose plugin.
2. Copy .env.example to .env and insert a unique 64-character operator token. Do not place the token in source control or chat logs.
3. Run ./scripts/preflight.sh. A successful preflight changes no containers.
4. Start the services with docker compose up --build -d.
5. Inspect docker compose ps and docker compose logs --tail=100.
6. Verify the API locally: curl http://127.0.0.1:8080/readyz.
7. Stop with docker compose down. Do not add -v; that would delete the persistent ledger volume.

## Android Termux local node

Run bash scripts/termux.sh install, then bash scripts/termux.sh start. The start action waits for the API readiness check and fails with a log instruction if it does not come up. Inspect with bash scripts/termux.sh status and bash scripts/termux.sh logs. Stop with bash scripts/termux.sh stop.

Android may pause background processes to conserve battery. Do not use this device as the only production host or expose the API publicly.

## Local validation

- make ci compiles Python, runs unit tests, checks shell syntax, builds a wheel, and checks Compose config when Docker is available.
- bash scripts/e2e-smoke.sh starts the API and worker as separate processes, submits a dry-run job, verifies worker completion, and checks the event hash chain.
- The CI script reports Docker as skipped when the Docker CLI is absent. A skip is not a container build pass.

## Backups

Create a consistent, integrity-checked local backup with python -m app.backup create. Verify a backup and its manifest with python -m app.backup verify <backup.sqlite3>. Copy both the database and JSON manifest to storage outside the host. The local utility does not itself provide remote or immutable storage.

## Restore

Stop all Forge processes first. Restore only to a new, unused target path with python -m app.backup restore <backup.sqlite3> --target ./data/recovered.sqlite3 --confirm-restore. The command validates the manifest digest, SQLite integrity, event count, and chain head. It refuses to overwrite an existing file. Review the restored state before switching the service to it.

## Current release limits

- Single-host only; SQLite shared-volume access is not a multi-node database.
- Scheduler off by default.
- Only ledger.verify is executable by the worker.
- Deployment execution is locked.
- No passkeys, mTLS, Vault, external WORM storage, public TLS endpoint, or HA failover.
