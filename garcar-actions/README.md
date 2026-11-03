# Garcar Actions

Independent, self-hostable CI/task runner for the Garcar ecosystem. GitHub remains source control; Garcar Actions owns its job queue and execution.

## v0.1 capabilities
- Python standard library only; SQLite WAL queue.
- Explicit action allowlist; no arbitrary shell input and no shell=True.
- Workspace path confinement.
- Bearer-token-protected job API; read-only health endpoint.
- SHA-256 hash-chained audit log and verification.
- Worker polling, bounded output, 10-minute execution timeout.
- Default API bind is loopback only. Remote bind is blocked unless explicitly enabled behind TLS/reverse proxy.

## Supported actions

| Action | Purpose |
|---|---|
| python_tests | Run Python unittest discovery |
| python_compile | Compile Python source |
| node_tests | Run npm test |
| git_status | Read working-tree status |

No deployment, payment, database migration, secret rotation, or customer-contact action is included in v0.1.

## Local run

From this directory, set a strong random GARCAR_ACTIONS_TOKEN and GARCAR_WORKSPACE to an isolated checkout. Then run:

    python -m garcar_actions.engine init
    python -m garcar_actions.engine serve

In a second terminal, with the same token and workspace:

    python -m garcar_actions.engine worker

Submit a job:

    curl -sS http://127.0.0.1:8788/v1/jobs -H "Authorization: Bearer $GARCAR_ACTIONS_TOKEN" -H "Content-Type: application/json" -d '{"action":"python_tests","repo_path":"/absolute/path/to/checkout"}'

Check status with GET /v1/jobs/JOB_ID. Check audit integrity with GET /v1/audit/verify. Health is GET /health.

## Tests

    python -m unittest discover -s tests -v

## Deployment and security
- Run API and worker as separate processes under a supervisor.
- Use a dedicated unprivileged OS account and disposable workspace.
- Keep the database on persistent storage and back it up before upgrades.
- Store the token in a secret manager, never in source control or logs.
- For remote access, terminate TLS at a trusted reverse proxy and restrict ingress to trusted networks.
- Never mount production secrets or payment credentials into the runner.
- This release is an execution kernel, not yet a webhook/polling bridge, multi-tenant scheduler, artifact store, or production deployment controller.
- Before production use, add per-job container/VM isolation, signed job definitions, quotas, and explicit operator approval for deployment capability.
