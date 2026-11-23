# Garcar Actions v0.2

An independent, Python standard-library job runner for reviewed code on a dedicated POSIX host. GitHub holds source; this service holds the local queue and executes allowed actions. This release is a tested local canary. Account-wide migration and unattended production isolation remain open.

## Run the complete local checks

From `garcar-actions/` in the hub checkout:

```bash
make ci
```

This compiles the Python files, runs the unit suite, starts a disposable authenticated loopback API, runs separate worker processes against success/failure/empty-test fixtures, verifies the audit chain, and runs the pinned hub structure canary. Test credentials and databases are temporary; the scripts clean up their processes. No external services are contacted by these checks.

The checks can also run separately:

```bash
python -m unittest discover -s tests -v
python -m garcar_actions.smoke
python scripts/hub-canary.py
```

## Actions and limits

| Action | Behavior |
|---|---|
| `python_tests` | Discovers `tests/` when present, otherwise the checkout root; zero tests fails with code 5 |
| `python_compile` | Compiles Python source in the checkout |
| `node_tests` | Runs `npm test`; npm must exist on the trusted host PATH |
| `git_status` | Reads working-tree status |
| `hub_structure` | Checks hub required files and JSON; prints inventory declarations |

- Minimal child environment and temporary HOME; parent API/cloud credentials and Python/loader overrides are excluded.
- Workspace paths checked at submission and immediately before execution.
- 100 pending jobs, 10-minute runtime limit, 1 MiB total output quota, last 12,000 output bytes retained plus an error suffix. Capture is bounded while the process runs.
- POSIX process-group cleanup on success, timeout, output-limit failure, or execution exceptions. A process that deliberately escapes its group requires stronger isolation.
- One executing worker per database using an OS file lock. Idempotency keys reuse the same request and reject conflicting requests.
- Audit integrity checked before queue/worker mutations; state changes and their audit entries commit together.
- Existing v0.1 databases receive additive nullable columns and a unique idempotency index; existing jobs/audit rows are preserved. Back up existing state before an upgrade.

## Run a local service

Use the existing secret manager to provide `GARCAR_ACTIONS_TOKEN` (32–512 characters). Keep state outside the checkout and run under a dedicated account with no production credentials. From `garcar-actions/`, these commands use the actual enclosing hub checkout:

```bash
export GARCAR_WORKSPACE="$(git rev-parse --show-toplevel)"
export GARCAR_ACTIONS_DB="$HOME/.local/state/garcar-actions/actions.db"
python -m garcar_actions.engine init
python -m garcar_actions.engine serve
```

In another terminal with the same configuration, run `python -m garcar_actions.engine worker`. For one job only, use `worker --once`.

Submit the reviewed structure canary through the CLI:

```bash
python -m garcar_actions.migration.workflow
python -m garcar_actions.migration.workflow --submit
python -m garcar_actions.engine status
python -m garcar_actions.engine audit-verify
```

Planning is read-only. Submission pins `.github/workflows/ci.yml` by SHA-256, and the worker checks that pin again. A changed workflow fails until reviewed and repinned. The pin covers the workflow definition; it is not a full checkout digest, signed release, or filesystem race protection.

HTTP endpoints are `GET /health`, `POST /v1/jobs`, `GET /v1/jobs/{id}`, and `GET /v1/audit/verify`. All except health require a Bearer token. Submission takes an action plus optional `repo_path` and `requested_by`; an optional `Idempotency-Key` header protects retries. Invalid requests return 400, unauthenticated requests 401, a full queue 429, and unavailable/corrupt queue state 503. A detected audit mismatch returns 409 from verification. Health reports API liveness only.

The API binds to `127.0.0.1:8788`. Remote binding requires `GARCAR_ACTIONS_ALLOW_REMOTE=1`; TLS, ingress restrictions, and a production HTTP server are still operator responsibilities. Remote exposure is outside this canary's verification.

## Interrupted jobs

A running job left by a worker crash blocks further execution. First stop the previous job's processes or destroy its disposable host. Then use:

```bash
python -m garcar_actions.engine recover --confirm-stopped
```

Recovery marks interrupted jobs failed with exit code 130 and records audit events. It never retries the job or guesses whether its side effects completed. Confirmation is an operator assertion, not an automatic proof that orphaned processes stopped.

## Migration evidence and boundaries

The `structure-check` port is defined in `migration/hub-structure.json`. Malformed JSON now fails reliably; the upstream shell pipeline could hide JSON errors. Advisory YAML/ShellCheck/Compose behavior and GitHub triggers have not been ported. The other three hub CI jobs remain untranslated. Original GitHub workflows remain enabled as configured.

`validation/` contains local test/canary reports and a hashed inventory of the hub's 53 workflows. The wider 51-repository discovery list is still partial. Scanner classifications are triage signals; shell steps and imported code can perform side effects even when their workflow looks read-only.

Environment filtering, timeouts, path checks, and process groups do not isolate untrusted code from the worker's filesystem or network. Before unattended or multi-tenant use, add disposable per-job containers/VMs, network and CPU/memory/disk limits, signed definitions and checkout digests, artifact retention, and an external audit anchor. The local SHA-256 chain detects altered entries; it cannot prove that a privileged writer has not rewritten or truncated the entire chain.

Deployments, financial actions, outreach, secret writes, and automatic merges are not implemented as runner actions. Docker/Termux target-host operation and public serving have not been verified in this environment.
