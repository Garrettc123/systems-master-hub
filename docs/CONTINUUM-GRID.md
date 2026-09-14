# Garcar Continuum Grid v1 — Architecture & Operations

## Overview

The **Garcar Continuum Grid** is the autonomous evolution layer for the 332+ repository Garcar Enterprise ecosystem. It discovers, inventories, scores, and incrementally upgrades every system through a daily scheduled workflow that produces deterministic, traceable, and reversible improvement plans — never repeating work, never modifying production systems without human approval.

---

## Core Principles

| Principle | Implementation |
|-----------|----------------|
| **Never repeat** | SHA-256 fingerprint of every proposed diff stored in `upgrade_ledger.json`; re-proposals blocked |
| **Read-first** | Discovery and planning are read-only; mutations only via PRs to target repos |
| **Risk-tiered** | Every action scored 1–8; auto-merge only for tier ≤ 2; tier ≥ 4 requires explicit approval |
| **Pilot-first** | v1 operates on 5 allowlisted repos; expansion requires validation gate |
| **Observable** | Every run produces JSON plan, workflow summary, and optional issue for high-risk items |
| **Reversible** | All changes via draft PRs; rollback = close PR + delete branch |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTINUUM GRID ORCHESTRATOR                   │
│  (systems-master-hub/.github/workflows/daily-evolution-v2.yml)   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  DISCOVER       │  │  PLAN           │  │  PROPOSE        │
│  • List all     │  │  • Score health │  │  • Create       │
│    repos        │  │  • Gap analysis │  │    branches     │
│  • Fetch        │  │  • Generate     │  │  • Push files   │
│    manifests    │  │    actions      │  │  • Open draft   │
│  • Load         │  │  • Deduplicate  │  │    PRs          │
│    registry     │  │    via ledger   │  │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           ▼
              ┌─────────────────────────┐
              │  UPGRADE LEDGER         │
              │  (SHA-256 deduplication)│
              └─────────────────────────┘
```

### Data Flow

1. **Scheduled trigger** (02:30 UTC daily) or manual dispatch
2. **Discovery** — GitHub API enumerates all non-archived repos in `Garrettc123` org
3. **Manifest load** — Each repo checked for `garcar.manifest.json`; validated against schema
4. **Health scoring** — 0–100 based on manifest, CI, tests, docs, activity, dependabot, tier
5. **Gap analysis** — Planner generates actions for missing manifest, CI, tests, docs, deps, tier promotion
6. **Deduplication** — Each action fingerprinted; ledger prevents re-proposal
7. **Risk tiering** — Actions scored 1–8; pilot cohort filtered; count capped
8. **PR creation** (execute mode only) — Branch, commit, draft PR per action
9. **Notification** — Workflow summary + optional issue for high-risk items

---

## Manifest Contract (`garcar.manifest.json`)

Every system in the Continuum Grid **must** publish a manifest at repository root. Schema: `garcar.manifest.schema.json`.

```json
{
  "system_id": "kebab-case-unique-id",
  "display_name": "Human Readable Name",
  "layer": "revenue|intelligence|infrastructure|data|compliance|interface",
  "version": "0.1.0",
  "tier": "prototype|production|intelligent|autonomous",
  "capabilities": ["api", "agent", "lang:python"],
  "apis": [{"name": "health", "endpoint": "https://...", "protocol": "http"}],
  "events_published": ["system.deployed", "revenue.collected"],
  "events_consumed": ["config.updated", "secret.rotated"],
  "health_endpoints": ["https://.../health", "https://.../ready"],
  "dependencies": ["garcar-base", "supabase"],
  "owners": ["Garrettc123"]
}
```

### Layer Definitions

| Layer | Purpose | Example Systems |
|-------|---------|-----------------|
| **revenue** | Payments, commerce, billing, Stripe/Shopify integration | `garcar-payments`, `garcar-shopify-app`, `apex-revenue-system` |
| **intelligence** | AI agents, ML models, reasoning, cognitive architectures | `autonomous-butler-core`, `NEXUS-AI-CORE`, `continuum-agents`, `mars-api` |
| **infrastructure** | Deploy, CI/CD, Terraform, Kubernetes, networking | `garcar-deploy-engine`, `enterprise-devops-platform`, `neural-mesh-pipeline` |
| **data** | Analytics, warehouses, CDP, knowledge graphs, monetization | `intelligent-customer-data-platform`, `semantic-knowledge-nexus`, `nwu-data-monetization` |
| **compliance** | Security, audit, legal, contracts, IP, secrets | `GARCAR-SECURITY-OPS`, `garcar-audit-trail`, `garcar-ip-vault`, `supersecret` |
| **interface** | Dashboards, portals, landing pages, admin UIs | `zeus-dashboard`, `atlas-dashboard`, `believe-revenue-site` |

### Tier Progression

| Tier | Health Score | Autonomy Level | Upgrade Authority |
|------|--------------|----------------|-------------------|
| **prototype** | 0–49 | Manual only | Human initiates all changes |
| **production** | 50–69 | CI/CD automated | Dependabot, lint, test PRs auto-proposed |
| **intelligent** | 70–84 | Self-healing | Tier promotion, refactor, config PRs proposed |
| **autonomous** | 85–100 | Full auto-evolve | All non-breaking upgrades auto-proposed; merge still requires approval |

---

## Risk Tier Matrix

| Tier | Action Types | Auto-Merge | Approval Required | Max Per Run |
|------|--------------|------------|-------------------|-------------|
| 1 | Docs, README, comments | ✅ | None | Unlimited |
| 2 | CI config, lint rules, formatting | ✅ | Any maintainer | 5 |
| 3 | Test scaffolding, dependabot | 🔄 Draft PR | Any maintainer | 3 |
| 4 | Refactor, config, schema, non-breaking features | ❌ | @Garrettc123 | 2 |
| 5 | Security patches, infra changes | ❌ | @Garrettc123 + review | 1 |
| 6 | Payment flows, deploy pipelines | ❌ | Explicit sign-off + staging | 1 |
| 7 | Data migrations, breaking changes | ❌ | Architecture review | 0 (manual only) |
| 8 | Critical infra, secrets, legal | ❌ | Never via Continuum | 0 (manual only) |

---

## Pilot Cohort (v1)

The initial rollout operates **only** on these five repositories:

| Repository | Layer | Rationale |
|------------|-------|-----------|
| `garcar-base` | infrastructure | Universal FastAPI contract — foundation for all Python/TypeScript systems |
| `continuum-agents` | intelligence | Persistent agent loop — core of autonomous operation |
| `systems-master-hub` | infrastructure | Orchestration center — this repo |
| `neural-mesh-pipeline` | infrastructure | Self-healing CI/CD — validates repair capability |
| `garcar-enterprise-production` | infrastructure | Production stack — validates end-to-end deployment |

**Expansion criteria** (all must pass for 2 consecutive weeks):
- [ ] Zero failed PR merges
- [ ] Zero rollback incidents
- [ ] All PRs pass CI in target repos
- [ ] Health scores improve ≥ 5 points avg
- [ ] No high-risk (tier ≥ 6) actions generated erroneously

---

## Required Secrets

Add to **`Garrettc123/systems-master-hub`** → Settings → Secrets → Actions:

| Secret | Scope | Purpose |
|--------|-------|---------|
| `GITHUB_TOKEN` | Auto-provided | Repository access for API calls |
| `CONTINUUM_GITHUB_TOKEN` | Optional (PAT) | Elevated token for cross-repo PR creation if GITHUB_TOKEN insufficient |
| `SUPABASE_URL` | Optional | Event bus endpoint for inter-system events |
| `SUPABASE_ANON_KEY` | Optional | Event bus publish/subscribe |

> **Note**: The engine uses the workflow's `GITHUB_TOKEN` by default. For creating PRs in *other* repositories, a PAT with `repo` scope may be needed if the default token lacks cross-repo write permission. Store as `CONTINUUM_GITHUB_TOKEN` and the engine will prefer it.

---

## Local Development

```bash
# Clone master hub
git clone https://github.com/Garrettc123/systems-master-hub
cd systems-master-hub

# Install deps
pip install requests pyyaml

# Dry run (safe, no PRs)
python continuum_engine.py --token $GITHUB_TOKEN --dry-run --output plan.json

# Inspect plan
cat plan.json | jq '.actions[] | {repo, title, risk: .risk_tier}'

# Execute (requires CONTINUUM_GITHUB_TOKEN with cross-repo write)
python continuum_engine.py --token $CONTINUUM_GITHUB_TOKEN --execute --max-repos 5
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub PAT or workflow token |
| `GITHUB_ORG` | No | Override org (default: Garrettc123) |
| `CONTINUUM_DRY_RUN` | No | Set to "false" to enable execution |

---

## Operational Runbook

### Daily Operations (Automated)

1. **02:30 UTC** — Workflow triggers automatically
2. **Discovery & Plan** — Runs in ~3–5 min; uploads `plan.json` artifact
3. **Review** — Check workflow summary for high-risk items
4. **Manual dispatch** — If plan looks good, re-run workflow with `dry_run: false`

### Manual Override

```bash
# Trigger with custom params
gh workflow run daily-evolution-v2.yml \
  -f dry_run=false \
  -f max_repos=5 \
  -f allowlist="garcar-base,continuum-agents"
```

### Rollback Procedure

If a merged PR causes issues:
1. **Revert in target repo**: `gh pr revert <PR_NUMBER> --repo Garrettc123/<repo>`
2. **Update ledger**: Manually set status to `rejected` in `upgrade_ledger.json`
3. **Block re-proposal**: The diff hash remains in ledger; engine will not re-propose
4. **Investigate**: Check workflow logs for root cause

### Emergency Stop

To halt all Continuum Grid activity:
1. Disable workflow: `gh workflow disable daily-evolution-v2.yml --repo Garrettc123/systems-master-hub`
2. Or add `if: false` to job conditions temporarily
3. No target repository is modified without explicit PR merge

---

## Monitoring & Observability

### Workflow Artifacts

Each run produces:
- `upgrade-plan/plan.json` — Full plan with all actions
- Workflow summary — Human-readable table in Actions UI
- Optional issue — Auto-created for tier ≥ 6 actions in dry-run

### Key Metrics to Track

| Metric | Target | Alert If |
|--------|--------|----------|
| Plan generation time | < 5 min | > 10 min |
| Actions per run | 5–15 | > 20 or = 0 |
| PR creation success rate | 100% | < 95% |
| PR merge rate (pilot) | > 80% | < 50% |
| Health score delta (pilot) | +5/run | Negative trend |
| High-risk false positives | 0 | Any |

### Dashboards

- **GitHub Actions** → `daily-evolution-v2` workflow runs
- **Systems Master Hub** → `SYSTEMS_STATUS.md` (updated by `update-status-dashboard.yml`)
- **Continuum Grid** → `upgrade_ledger.json` (append-only audit trail)

---

## Extending the Engine

### Adding New Action Types

1. Add risk tier to `RISK_TIERS` in `continuum_engine.py`
2. Implement `_plan_<type>(repo)` method in `UpgradePlanner`
3. Add template generator `_<type>_template(repo)`
4. Update deduplication key if needed
5. Test in dry-run on pilot cohort

### Adding New Layers

1. Add to `MANIFEST_SCHEMA` enum in both engine and schema file
2. Update `_infer_layer()` heuristics
3. Add layer-specific upgrade rules if needed
4. Document in this file

### Cross-Repo Coordination

For multi-repo upgrades (e.g., API contract change):
1. Create a **meta-action** with `depends_on` listing child action diff hashes
2. Engine creates dependent PRs in sequence
3. Use `garcar-events` bus to signal completion

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-09-13 | Initial Continuum Grid: discovery, planning, ledger, PR generation, pilot cohort, daily workflow |

---

## Support & Escalation

- **Primary**: @Garrettc123
- **Issues**: `Garrettc123/systems-master-hub` with label `continuum-grid`
- **Emergency**: Disable workflow + revert PRs + manual investigation

---

*Part of the Garcar Enterprise Autonomous Evolution Platform — "One mastery-level architectural feat"*