# 🚀 GARCAR ENTERPRISE — ALL-IN-ONE SWEEP MANIFEST

> **Single source of truth.** Every revenue system in the Garcar Enterprise stack  
> is registered here. The sweep workflow triggers all systems in parallel,  
> verifies health, and writes a ledger issue back to this repo automatically.

---

## ⚡ Run the Sweep

```bash
# Option 1 — GitHub Actions (zero local dependencies)
# Go to: https://github.com/Garrettc123/systems-master-hub/actions/workflows/garcar-all-in-one-sweep.yml
# Click "Run workflow" → select mode → Run

# Option 2 — Single command from terminal / Termux
export GITHUB_TOKEN=your_token_here
./orchestrate/garcar-sweep.sh full

# Option 3 — Local status check only (no deploy)
export GITHUB_TOKEN=your_token_here
python3 orchestrate/sweep-status.py
```

---

## 🗺️ System Registry

| # | System | Repo | Role | Sweep Event |
|---|--------|------|------|-------------|
| 1 | Payments Core | [garcar-payments](https://github.com/Garrettc123/garcar-payments) | Billing logic, Stripe API | `garcar-sweep` |
| 2 | Payment Loop | [garcar-payment-loop](https://github.com/Garrettc123/garcar-payment-loop) | Stripe webhook → gc_ledger | `garcar-sweep` |
| 3 | TITAN | [TITAN-Autonomous-Business-Empire](https://github.com/Garrettc123/TITAN-Autonomous-Business-Empire) | Top-level orchestration | `garcar-sweep` |
| 4 | MLOps | [enterprise-mlops-platform](https://github.com/Garrettc123/enterprise-mlops-platform) | ML lifecycle, drift detection | `garcar-sweep` |
| 5 | Atlas | [atlas-dashboard](https://github.com/Garrettc123/atlas-dashboard) | Revenue + lead analytics | `garcar-sweep` |
| 6 | Zeus | [zeus-dashboard](https://github.com/Garrettc123/zeus-dashboard) | RHNS cognitive control plane | `garcar-sweep` |
| 7 | MARS API | [mars-api](https://github.com/Garrettc123/mars-api) | Billable metacognitive API | `garcar-sweep` |
| 8 | Neural Mesh | [neural-mesh](https://github.com/Garrettc123/neural-mesh) | Self-healing CI/CD backbone | `garcar-sweep` |

---

## 🔁 Revenue Flow

```
Stripe Checkout
     │
     ▼
garcar-payment-loop  ──────────────────────────────┐
(webhook → gc_ledger)                               │
     │                                              │
     ▼                                              ▼
garcar-payments                              atlas-dashboard
(billing logic)                          (revenue analytics)
     │
     ▼
  MARS API ◄──── enterprise-mlops-platform
(API product)        (model lifecycle)
     │
     ▼
   TITAN
(orchestration engine)
     │
     ▼
zeus-dashboard / garcar-rhns-core
(cognitive control plane)
     │
     ▼
neural-mesh
(self-healing CI/CD)
```

---

## 🕐 Autonomous Schedule

| Trigger | Frequency | What fires |
|---------|-----------|------------|
| Schedule | Every 6 hours | Full sweep — all 8 systems |
| `push` to `SWEEP-MANIFEST.md` | On change | Full sweep |
| Manual `workflow_dispatch` | On demand | Configurable mode |
| Downstream `repository_dispatch` | Per-repo | Individual system deploy |

---

## ✅ Secrets Required

Set these once in **GitHub → Settings → Secrets → Actions** for each revenue repo:

| Secret | Where Used |
|--------|------------|
| `STRIPE_SECRET_KEY` | garcar-payments, garcar-payment-loop |
| `STRIPE_WEBHOOK_SECRET` | garcar-payment-loop |
| `RAILWAY_TOKEN` | All deploy targets on Railway |
| `RAILWAY_DEPLOY_URL` | Each service's Railway URL |
| `NOTION_TOKEN` | CRM logging |
| `LINEAR_API_KEY` | Issue ledger |
| `GITHUB_TOKEN` | Auto-provided by Actions |

---

## 📒 Sweep Ledger

Every sweep auto-creates a GitHub Issue in this repo as a timestamped record.  
View all sweep logs: [Issues → garcar-sweep label](https://github.com/Garrettc123/systems-master-hub/issues)

---

*Last updated: 2026-06-09 by systems-master-hub auto-sweep*  
*Garcar Enterprise | Grandview, Texas | garrettc123*
