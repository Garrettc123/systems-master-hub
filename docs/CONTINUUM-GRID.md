# Continuum Grid v1 — Architecture & Operations

## Purpose

Continuum Grid is the **governed** observe → plan → propose layer for the Garcar ecosystem. It consolidates inventory, readiness scoring, and upgrade proposals without competing with existing daily-evolution, self-heal, or deployment workflows.

**It does not autonomously change production payments, deployments, customer messaging, CRM, infrastructure, or secrets.**

## Components

| Path | Role |
|------|------|
| `continuum/continuum_engine.py` | Discovers systems from registry, scores readiness, emits deterministic plans |
| `continuum/repository_registry.py` | Normalizes capability-registry / SYSTEM_REGISTRY into a canonical graph |
| `continuum/upgrade_ledger.py` | Append-only JSONL ledger with SHA-256 fingerprints (dedup) |
| `templates/garcar.manifest.json` | Standard Garcar Base contract template |
| `scripts/bootstrap-garcar-standard.py` | Dry-run default; PR-only opt-in bootstrap |
| `.github/workflows/daily-evolution-v2.yml` | Scheduled + manual; observe/plan/dry-run only |

## Safety properties

1. **Read-only default** — engine never writes into foreign repositories.
2. **Pilot allowlist** — v1 only proposes against: `garcar-base`, `continuum-agents`, `systems-master-hub`, `neural-mesh-pipeline`, `garcar-enterprise-production`.
3. **High-risk domains blocked** — payments, revenue-intelligence, legal-compliance, security require human gate.
4. **No auto-merge** — workflow does not merge PRs.
5. **No secret injection** — no new secrets, no vault writes from this path.
6. **Ledger dedup** — identical fingerprints are not re-proposed.
7. **Additive** — does not replace `daily-evolution.yml`; runs later in the day as a safer twin.

## Rollout steps

1. Merge this PR (`continuum-grid-v1` → `main`) after review.
2. Run workflow manually with `mode=observe` and inspect the artifact.
3. Run `mode=dry-run` / `plan` and review `continuum/upgrade_plans/latest_plan.json`.
4. For hub itself only, optionally run:
   ```bash
   python3 scripts/bootstrap-garcar-standard.py --system systems-master-hub --no-dry-run
   ```
5. Expand pilot allowlist only by PR to `continuum_engine.py` after successful hub dry-runs.

## Required secrets

None for v1 observe/plan. Future PR-opening steps may use existing `GARCAR_PAT` / `GITHUB_TOKEN` with least privilege. Do not add Continuum-specific secrets in this release.

## Rollback

- Disable the workflow file (rename or set `if: false`).
- Delete `continuum/upgrade_plans/` artifacts if needed.
- Ledger is append-only; leave it for audit or archive the file.
- No production services depend on Continuum Grid v1.

## Relation to existing automation

- `daily-evolution.yml` (v3) still exists and can commit capability scaffolds into targets.
- Continuum Grid v2 is the **safer control plane**: inventory, risk scoring, dedup ledger, pilot gates, PR-only path.
- Prefer routing new autonomous upgrade work through Continuum before expanding the older direct-commit evolution agent.

## Ops runbook (short)

```bash
# Local observe
python3 continuum/continuum_engine.py --mode observe

# Write plan
python3 continuum/continuum_engine.py --mode plan

# Bootstrap hub manifest (dry-run)
python3 scripts/bootstrap-garcar-standard.py --system systems-master-hub
```

Inspect `continuum/upgrade_plans/latest_plan.json` and `continuum/upgrade_ledger.jsonl` after every run.
