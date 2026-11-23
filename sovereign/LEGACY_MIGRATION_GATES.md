# Legacy Platform Migration Gates

## Why this exists

The existing omnibus material is a broad Docker-based multi-service deployment design. It is not a suitable default runtime for Android/Termux and must not be treated as a verified production deployment.

The currently documented omnibus requirements include Docker, multiple databases, Prometheus, Grafana, Elasticsearch/Kibana and Jaeger, with a stated recommended baseline of 8 GB RAM and 50 GB disk. The documented compose configuration also contains example credentials and service ports. Those defaults are not acceptable for an internet-facing production environment.

The master deployment guide describes AWS/Terraform and Vercel steps and an `AUTO_APPROVE=true` setting. Those are explicitly outside the sovereign zero-cost deployment path.

## Migration policy

1. Do not run the legacy `make omni` or full-stack deployment on the phone as part of this MVP.
2. Do not enable automatic production approval.
3. Do not reuse sample database or dashboard passwords.
4. Do not expose database, cache, metrics, tracing, or admin ports to a public interface.
5. Do not delete or rotate existing secrets automatically. Inventory ownership and dependencies first, then perform a separately approved migration.
6. Do not mass-deploy all repositories. Select one low-risk service and prove the entire build/deploy/rollback cycle first.
7. Preserve the existing repository and deployment state. New integration work stays on the feature branch until reviewed.

## Migration sequence

### Gate 0 — Evidence inventory
For each service, record repository, default branch, current commit, language/runtime, manifest, data stores, environment-variable names (never values), health/readiness routes, ports, owner, and evidence date.

### Gate 1 — Source validation
Clone or use an existing local checkout. Run its documented tests locally. Record exact command, exit code, timestamp, and commit. No remote CI is required.

### Gate 2 — Local manifest
Add a `garcar.deploy.json` with argument-array build/start commands, loopback binding contract, health path, distinct canary/service ports, and explicit environment-variable name allowlist.

### Gate 3 — Canary
Deploy a disposable service on localhost. Confirm health, logs, process ownership, port binding, stop behavior, and restart behavior.

### Gate 4 — Rollback
Deploy a known-good release, introduce a deliberately failing candidate, and prove that the old release returns healthy. Preserve logs and audit-chain verification output.

### Gate 5 — Shared integration
Only after the canary gates pass, integrate the service's identity, event envelope, metrics and financial contracts. Do not connect trading execution or live payment operations during this phase.

### Gate 6 — Production decision
Production requires an always-on host under owner control, firewall verification, TLS, DNS, durable backups, restore test, least-privilege secrets, authenticated administration, monitoring, and an explicit owner approval. Android alone does not satisfy the availability requirement.

## Evidence labels

- `repository_identified`: repository exists and was fetched.
- `source_tested`: a recorded local test run passed at a specific commit.
- `canary_healthy`: a real process passed its health/readiness checks.
- `production_deployed`: traffic is routed to the service on an approved always-on host.
- `revenue_verified`: authoritative payment and ledger records reconcile.

Never promote a system to a stronger label based only on README wording, badges, architecture documents, or a successful liveness endpoint.
