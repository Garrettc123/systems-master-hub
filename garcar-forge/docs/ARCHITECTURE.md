# Garcar Forge Architecture — v0.2

## Operating model

Garcar Forge separates the management API from background processing. All components are processes on one host and share one persistent SQLite volume. This is a deliberate first-stage design: simple to operate, portable, and inexpensive. It is not a multi-host control plane.

```text
Operator
   |
   | Bearer token
   v
FastAPI Control Plane
   |-- health/readiness
   |-- dry-run deployment planner
   |-- allowlisted job intake
   |-- status and ledger inspection
   |
   v
SQLite data volume
   |-- append-only event table (SHA-256 linked)
   |-- durable jobs table (idempotency + lease)
   |
   +----------+----------------+
              |                |
              v                v
        Worker process   Scheduler process
        allowlist only   disabled by default
        ledger.verify    queues ledger.verify
              |                |
              +--------+-------+
                       v
                Ledger verification
```

## Control plane

The API authenticates management requests using an operator bearer token. Tokens shorter than 32 characters are rejected. The service accepts only dry-run deployment plans whose artifact identity is a SHA-256 digest. The execution endpoint is permanently locked in this release.

## Event ledger

Each event contains a unique event ID, UTC timestamp, type, actor, payload, previous event hash, and its own SHA-256 hash. Appends use SQLite write transactions. Job state transitions and matching audit events share a transaction, preventing an acknowledged queue state from being separated from its audit event.

The chain detects edits to retained event history. It cannot, by itself, detect removal of the final event if no independently retained chain head exists. It is not certified WORM storage. Backups include a file SHA-256 and independently checked chain head in a JSON manifest.

## Job lifecycle

1. Authenticated operator submits a dry-run ledger verification job.
2. The API requires a bounded idempotency key and refuses unsupported task names or non-empty payloads.
3. The job and its job.queued event are committed together.
4. A worker claims a queued job under a SQLite transaction and records job.claimed atomically.
5. The worker executes only ledger.verify; it cannot run commands, deploy applications, send messages, or access payment providers.
6. Success or failure state and its audit event are committed together.
7. A worker crash leaves a lease. Another worker may reclaim it after the lease expires, up to three attempts. Further expiry moves the job to failed.

## Scheduler

The scheduler is a separate process but is disabled by default. When explicitly enabled, it creates only periodic ledger.verify jobs. It does not run arbitrary scripts or business actions.

## Deployment model

Docker Compose builds one image and runs three services. All use a non-root user, read-only root filesystems, dropped Linux capabilities, and no-new-privileges. Only the API port is published, bound to 127.0.0.1. The database volume is local to the host.

Termux runs the same API, worker, and scheduler as separate local processes. The API also binds to 127.0.0.1. The phone is a local development/canary node, not a high-availability server.

## Production evolution path

Before multi-host or public production use, replace the shared SQLite store with PostgreSQL and external object storage, add mTLS host identity, passkey/WebAuthn and role-based approvals, integrate Vault secret leasing, add signed artifact provenance, publish backups off-host, exercise disaster recovery, and complete an independent security review. Only then should constrained deployment execution and rollback be introduced.
