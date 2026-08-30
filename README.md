# Garcar Enterprise — Autonomous AI Business Infrastructure

> Revenue automation, agent orchestration, and cloud deployment — all running without human intervention.

🌐 **[Live Site](https://garrettc123.github.io/systems-master-hub)** &nbsp;|&nbsp; 📊 **[Investor Data Room](https://app.notion.com/p/338024e8799b811cbd26d2019831ccab)** &nbsp;|&nbsp; 🐙 **[GitHub](https://github.com/Garrettc123)**

---

## Stack Overview

| Repository | Purpose | Tech | Status |
|---|---|---|---|
| [autonomous-butler-core](https://github.com/Garrettc123/autonomous-butler-core) | Managed AI Ops — $2,500/mo | Python, LLM agents | 🟢 Active |
| [NEXUS-AI-CORE](https://github.com/Garrettc123/NEXUS-AI-CORE) | Real Estate Intelligence Engine — $1,000/report | Python, ML, APIs | 🟢 Active |
| [garcar-product-factory](https://github.com/Garrettc123/garcar-product-factory) | Digital Product Catalog — from $49 | Node.js, Stripe | 🟢 Active |
| [systems-master-hub](https://github.com/Garrettc123/systems-master-hub) | Architecture & cross-repo orchestration | Shell, Python | 🟢 Active |
| [control-plane](https://github.com/Garrettc123/control-plane) | Infrastructure control plane | Terraform, Docker | 🟢 Active |
| [zero-human](https://github.com/Garrettc123/zero-human) | Zero-human-intervention automation | Python, GitHub Actions | 🟢 Active |

---

## Key Metrics

- **263** repositories across the Garcar Enterprise ecosystem
- **172** public systems live and operational
- **Active since 2020**

---

## 🧠 Adaptive ICP Swarm

The master hub now includes an outcome-driven ICP learning component at `swarm/adaptive_icp_engine.py`. It converts prospect, sales, retention, revenue, and acquisition-cost observations into continuously ranked market segments.

**Documentation:** `swarm/ADAPTIVE_ICP_SWARM.md`

The intended operating loop is:

```text
Discovery → Enrichment → Qualification → Offer → Outreach → Deal
    ↑                                                     ↓
    └──────────── ICP learning ← Outcomes ← Retention ────┘
```

The engine is framework-independent and designed to plug into the existing orchestration layer. It does not independently authorize consequential external actions; host-level permissions, compliance controls, rate limits, and approval gates remain authoritative.

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
GITHUB_TOKEN=<token> ./master-deploy.sh --dry-run

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
├── 🧠 swarm/                    # Adaptive commercial intelligence
│   ├── adaptive_icp_engine.py
│   └── ADAPTIVE_ICP_SWARM.md
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

## GitHub Actions Workflows

This hub uses GitHub Actions for CI, validation, packaging, security, and deployment orchestration.

### Automated (run on push/PR/schedule)

| Workflow | Trigger | Purpose |
|----------|---------|---------|
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
| [swarm/ADAPTIVE_ICP_SWARM.md](./swarm/ADAPTIVE_ICP_SWARM.md) | Adaptive ICP swarm architecture |
