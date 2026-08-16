# GARCAR Operations Sweep

The control plane is repaired to be evidence-driven:

1. `empire-orchestrator.yml` no longer hard-codes the retired Railway endpoint.
2. `systems-sweep.yml` validates workflow YAML, repository references, stale infrastructure gates, and obvious credential leakage.
3. `revenue-loop.yml` fails closed when required production revenue configuration is absent instead of reporting a false-success execution.

## Production health contract

Set the repository secret `GARCAR_HEALTH_URL` to the canonical production `/health` endpoint when an external application is deployed. The orchestrator will verify it before dispatching the revenue loop.

Set `STRIPE_SECRET_KEY` and `REVENUE_WEBHOOK_URL` only through GitHub Actions secrets. Never commit credentials to the repository.

A green GitHub workflow means the tested control-plane gates passed. It does not by itself prove that every portfolio repository is deployed.
