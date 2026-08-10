# 🏗️ Systems Master Hub

## Enterprise AI Ecosystem - $102M+ Multi-System Architecture

---

## 📊 Live Status Dashboard

```bash
# Show health & CI status of all major repos (requires curl + python3)
./status.sh

# Authenticated (5,000 req/hr instead of 60)
GITHUB_TOKEN=<token> ./status.sh

# JSON output
./status.sh --format json
```

See **[SYSTEMS_STATUS.md](./SYSTEMS_STATUS.md)** for a full inventory of every repository.

---

## 🚀 Quick Start — Run Everything (Omnibus)

Run the entire enterprise ecosystem with one command:

```bash
make omni
```

This launches:
- 🤖 AI/ML Systems (APEX, MLOps)
- ⛓️ Blockchain (AUTOHELIX, Stablecoin)
- 🏢 Enterprise Platforms
- 📊 Monitoring Stack (Prometheus, Grafana, ELK, Jaeger)
- 🗄️ Data Infrastructure (PostgreSQL, Redis)

**Documentation:** See [OMNI-README.md](./OMNI-README.md) for complete details.

**Quick Commands:**
```bash
make omni         # Deploy everything
make omni-status  # Check service status
make omni-logs    # View logs
make omni-stop    # Stop all services
```

---

## 🚀 Master Deploy — Trigger Deployments Across All Repos

```bash
# Trigger all repo workflows (requires GITHUB_TOKEN with workflow scope)
GITHUB_TOKEN=<token> ./master-deploy.sh

# Dry-run (prints actions, no API calls)
./master-deploy.sh --dry-run

# Deploy a single repo
GITHUB_TOKEN=<token> ./master-deploy.sh --repo enterprise-mlops-platform
```

---

## 📂 Repository Structure

```
systems-master-hub/
├── 🤖 ai-systems/               # All AI & ML platforms
│   ├── APEX-Universal-AI-Operating-System
│   └── enterprise-mlops-platform
├── ⛓️  blockchain/               # Crypto & Web3 protocols
│   ├── stablecoin-protocol
│   └── autohelix
├── 🏢 enterprise/               # Business automation tools
│   ├── enterprise-unified-platform
│   └── tree-of-life-system
├── 🌐 web/                      # Frontends & Portfolios
│   └── portfolio-website
├── scripts/
│   └── sync-docs.sh            # Auto-sync shared docs to all repos
├── .github/workflows/
│   └── update-status-dashboard.yml  # Daily status refresh
├── status.sh                   # Live health/CI status dashboard
├── master-deploy.sh            # Cross-repo deployment trigger
├── SYSTEMS_STATUS.md           # Full repo inventory
├── BUILD-STATUS.md             # Build status details
├── docker-compose.yml          # Master run configuration
└── Makefile                    # Simple control commands
```

---

## GitHub Actions Workflows

This hub uses GitHub Actions for CI, validation, packaging, security, and deployment orchestration.

### Automated (run on push/PR/schedule)

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **Autonomous Deploy** (`autonomous-deploy.yml`) | push to main, every 6h, dispatch | **Hands-off tiered rollout of every repo in the registry.** See [Autonomous deployment](#autonomous-deployment) below. |
| **CI - Validate Hub** (`ci.yml`) | push, PR, dispatch | YAML lint, shell syntax check, Docker Compose validation, repo structure check |
| **Build - Package Hub Artifacts** (`hub-build.yml`) | push (config paths), PR, dispatch | Validates compose/Makefile/monitoring configs; packages hub archive on main |
| **Self-Heal - Hub Health Check** (`self-heal.yml`) | push, daily 7 AM, dispatch | Validates all YAML, shell scripts, JSON files; checks required files exist |
| **Deploy - All Systems Status** (`auto-deploy-all-systems.yml`) | push, weekdays 9 AM, dispatch | Pre-flight checks, inventory report, repo accessibility, compose validation |
| **CodeQL Advanced** (`codeql.yml`) | push, PR, weekly | Static analysis for Python and GitHub Actions |
| **Security - Org-Wide Scan** (`org-security-scan.yml`) | weekly Monday, dispatch | CodeQL, secret scanning, SBOM generation, permissions audit |
| **Auto-Merge Copilot PRs** (`auto-merge-copilot.yml`) | PR events, check suite | Auto-squash-merges ready PRs |

### Manual Dispatch Only

| Workflow | Purpose |
|----------|---------|
| **Operator - Manual Run** (`operator-dispatch.yml`) | Consolidated operator entrypoint: validate-all, inventory-report, check-external-repos, security-scan, dry-run-deploy |
| **Full Stack Auto-Deploy** (`full-stack-deploy.yml`) | 49-step deployment: Terraform validate/plan/apply, Vercel deploy, notifications. Requires AWS + Vercel + Slack secrets. |
| **Prestige Check** (`prestige-check.yml`) | Weekly quality check via Prestige orchestrator |
| **Reusable CI/CD** (`reusable-ci-cd.yml`) | Callable workflow template for node/python stacks |
| **Pixel 10 Deploy** (`deploy-pixel10.yml`, `pixel10-deploy.yml`) | Deploy Ollama LLM to Pixel 10 device |
| **Zero-Human Deploy** (`zero-human-deploy.yml`) | Autonomous platform execution (3 paths) |
| **Terraform** (`terraform.yml`) | Full Terraform pipeline with security scanning |

> Terraform and other infrastructure-mutating workflows stay behind a manual gate on
> purpose. Automatic rollout is handled by `autonomous-deploy.yml`, which dispatches
> to each repo's own pipeline rather than applying infrastructure directly.

## Autonomous deployment

`autonomous-deploy.yml` removes the manual step from cross-repo rollout. It runs on
every push to `main` that touches deployable content and on a 6-hourly schedule, so
drift is reconciled and previously failed repos are retried without anyone pressing a
button.

**The registry is the only thing you edit.** `registry/repos.json` is the single
source of truth for which repositories exist and in what order they deploy. No
workflow contains a hardcoded repo name.

```
registry/repos.json
        │
        ▼
scripts/resolve_deploy_targets.py     ← builds the deploy matrix
        │
        ▼
tier1  ──►  tier2  ──►  tier3         ← each gated on the previous tier
        │
        ▼
.github/actions/dispatch-deploy       ← repository_dispatch, with retries
```

### Tiers

| Tier | Behaviour on failure | Intent |
|------|----------------------|--------|
| `tier1` | `fail-fast`, halts the rollout | Revenue and core-path systems |
| `tier2` | Continues, blocks `tier3` if the tier fails | Dashboards and platform services |
| `tier3` | Continues, non-blocking | Supporting and experimental systems |

### Adding a repo

Add an entry under the appropriate tier in `registry/repos.json`:

```json
"my-new-service": {
  "repo": "Garrettc123/my-new-service",
  "contract": "contracts/my-new-service.json",
  "role": "what-it-does",
  "platform": "railway",
  "dispatchEvent": "garcar-sweep",
  "requiredSecrets": ["RAILWAY_TOKEN"]
}
```

That is the entire change. The next push or scheduled run picks it up automatically.
Preview what would happen without dispatching:

```bash
python3 scripts/resolve_deploy_targets.py --all      # full matrix
python3 scripts/resolve_deploy_targets.py --tier tier1
```

### Required secrets

Cross-repo dispatch needs a PAT, because `GITHUB_TOKEN` is scoped to this repository
only and cannot trigger workflows elsewhere. The pipeline accepts `GARCAR_PAT`,
`PAT_TOKEN`, or `GHPAT`. If none is configured the run does **not** fail — it
degrades to validate-only mode and annotates the run summary, so a missing secret is
visible rather than silently skipped.


### Secrets Required for Full Deployment

These secrets are only needed for deployment workflows. CI and validation workflows run without any secrets.

| Secret | Used By |
|--------|---------|
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Terraform workflows (per environment: DEV_, STAGING_, PROD_) |
| `AWS_REGION` | Terraform workflows |
| `VERCEL_TOKEN` | Vercel deployment |
| `SLACK_WEBHOOK` | Deployment notifications |
| `INFRACOST_API_KEY` | Cost estimation |
| `PIXEL10_SSH_KEY` / `PIXEL10_IP` / `PIXEL10_SSH_PORT` | Pixel 10 device deployment |

## Maintenance

- **Update all repos**: `git submodule foreach git pull origin main`
- **View logs**: `docker-compose logs -f`
- **Stop everything**: `make stop`
- **Run full validation**: Go to Actions > "Operator - Manual Run" > select `validate-all`
- **Generate inventory**: Go to Actions > "Operator - Manual Run" > select `inventory-report`

---

## 🤖 Automation

- **Daily status refresh**: [`.github/workflows/update-status-dashboard.yml`](.github/workflows/update-status-dashboard.yml) — automatically updates `SYSTEMS_STATUS.md` and `BUILD-STATUS.md` every day at 07:00 UTC.
- **Cross-repo deployments**: [`master-deploy.sh`](./master-deploy.sh) — triggers `workflow_dispatch` on all major repos.
- **Doc sync**: [`scripts/sync-docs.sh`](./scripts/sync-docs.sh) — pushes shared `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `SECURITY.md` to all repos.

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [SYSTEMS_STATUS.md](./SYSTEMS_STATUS.md) | Full repo inventory with badges |
| [BUILD-STATUS.md](./BUILD-STATUS.md) | Detailed build & completion status |
| [OMNI-README.md](./OMNI-README.md) | Omnibus deployment guide |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Deployment procedures |
| [COMPLETION-ROADMAP.md](./COMPLETION-ROADMAP.md) | Roadmap and milestones |
