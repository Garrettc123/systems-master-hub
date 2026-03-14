# 🏗️ Systems Master Hub

This repository is the **Master Coordination Hub** for all 89+ systems in the Garrettc123 ecosystem,
organized into a clean, deployable structure worth an estimated **$100M+** in combined value.

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

## 🛠️ Maintenance

| Task | Command |
|------|---------|
| Initialize submodules | `make setup` |
| Build all containers | `make build` |
| Run all containers | `make run` |
| Stop all containers | `make stop` |
| View live status | `./status.sh` |
| Trigger all deployments | `GITHUB_TOKEN=<token> ./master-deploy.sh` |
| Sync shared docs | `GITHUB_TOKEN=<token> ./scripts/sync-docs.sh --apply` |
| Update all submodules | `git submodule foreach git pull origin main` |
| View container logs | `docker compose logs -f` |

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
