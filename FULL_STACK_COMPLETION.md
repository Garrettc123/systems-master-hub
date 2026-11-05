# Garcar full-stack completion run

The integrated local stack has **108 passing tests** and passing real-process canaries. Production is not complete: one required host identity test is blocked and five production-readiness gates remain open. See [the recorded result](validation/full-stack/completion.json).

## Reproduce

In a fresh checkout, install dependencies in an isolated environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-completion.lock
make completion PYTHON=.venv/bin/python
```

Reports are written to `validation/full-stack/`. The runner uses temporary tokens, fixture leads, SQLite files, child processes, and loopback ports. It cleans up its canaries. It does not deploy, provision credentials, contact customers, process payments, or call paid providers.

Exit 0 means selected checks passed; exit 1 means software validation failed; exit 2 means dependencies, a required host check, or production evidence is missing. `completion-local` can waive production-readiness checks for its exit code but cannot convert failed software or blocked host identity checks into passes. The default Make target is completion. Legacy `all`, `build`, `run`, and `omni` require its gate before proceeding.

## Observed checks

| Component | Result |
|---|---|
| Phone console | Served by a real API process; local Forge and Actions status authenticated and displayed by its API |
| Lead API | Tenant-scoped, atomic retries; conflicting key reuse returns HTTP 409 |
| Lead persistence | SQLite WAL records reused after an API-process restart |
| Sensitive notes | Blocked note text withheld from storage and response |
| Forge API/worker | Separate processes complete an allowlisted ledger-verification job |
| Forge recovery | Backup verification and restore to a disposable new target pass |
| Actions API/worker | Real unittest job completes without inherited operator credentials |
| Audit chains | Both service chains verify after their jobs finish |
| Local deployment | Healthy promotion succeeds; unhealthy promotion restores the prior healthy release |
| Execution policy | Live deployment endpoint remains HTTP 423 locked |
| Source/packaging | Python, JavaScript, shell, JSON, YAML checks and Forge wheel build pass |

The total is 28 security/provider/registry/completion-gate tests, 8 local-controller tests, 25 phone/core/lead-store tests, 15 Forge tests, and 32 Actions tests. Process canaries and packaging are additional checks. Security primitives and provider contracts are tested offline; public security, WebAuthn, distributed authorization, and external provider connectivity are not established by these results.

Sources from PRs 44, 45, 47, 48, 49, 51, and 53 are combined for verification. [Provenance](validation/full-stack/provenance.json) records their exact revisions; this run does not merge them into main.

## Runtime configuration

`GARCAR_CORE_DB` selects a private persistent SQLite file. Without it, core keeps an in-memory database for existing preview compatibility; `/healthz` reports the mode. The canary supplies a file and verifies restart persistence. New database files receive owner-only permissions; existing file permissions are preserved.

The phone status bridge uses `GARCAR_FORGE_URL`, `GARCAR_ACTIONS_URL`, and the existing server-side operator/Actions tokens. URLs must be literal `127.0.0.1` HTTP addresses with explicit ports. Redirects and environment proxy settings are disabled for these requests. Provider credentials never enter browser assets.

Legacy Compose now requires passwords/connection data from the existing secret manager and binds published ports to loopback. No deployed configuration or secret values were changed. The repaired upgrade workflow is manual-only and defaults to a plan with writes disabled.

## Remaining gates

- Docker is unavailable here, so image builds and Compose startup were not verified.
- Seven legacy application build directories/Dockerfiles referenced by root Compose are missing. Those applications are not claimed running.
- This host denies reading child-process environment data through `/proc`. The Termux identity guard stays fail-closed and needs target-host verification; it is not counted as passing.
- Persistent target volumes/recovery, isolated jobs, external audit anchoring, and protected public ingress need deployment evidence.
- Live integrations and actual payment receipts were not exercised. A running payment service is not verified revenue.

The production registry's declarations are not runtime proof.

## Railway repair

The read-only snapshot shows web and payment-loop services online, worker offline, and the latest scheduler execution failed. The scheduler is a read-only health canary; the inspected output provides no completed diagnosis for its latest failure.

The worker's syntax error was reproduced and repaired in [tree-of-life-system PR 180](https://github.com/Garrettc123/tree-of-life-system/pull/180). Parsing and synthesis success/rejection checks pass locally. The repair is published for review and has not been deployed by this run. The timestamped cloud snapshot is separate from local test evidence.
