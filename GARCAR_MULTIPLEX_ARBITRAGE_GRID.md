# GARCAR Multiplex Arbitrage Grid

This document defines the first full multiplex arbitrage architecture across Garcar Enterprise tier‑1 systems.

It is driven by `SYSTEM_REGISTRY.json` and the Universal Event Bus hosted in `autonomous-butler-core`, and designed to converge toward the registry's convergence target:

> ONE_MASTERY_LEVEL_ARCHITECTURAL_FEAT

with the upgrade directive:

> NEVER_REPEAT_ONLY_UPGRADE

## 1. Event Bus Contract

**Host repo:** `autonomous-butler-core`

**Broker:** `NATS` or `Redis Streams` (as defined in `SYSTEM_REGISTRY.json`)

**Topic schema:**

```text
garcar.{system_name}.{event_type}
```

Examples:

- `garcar.TITAN-Autonomous-Business-Empire.revenue_delta`
- `garcar.autonomous-income-deployment.deployment_status`
- `garcar.autonomous-butler-core.agent_decision`
- `garcar.garcar-payments.payment_settled`
- `garcar.unprecedented-autonomous-revenue-os.subscription_upgraded`
- `garcar.nwu-protocol.onchain_event`

Each participating system MUST:

1. **Emit events** for key changes (revenue, deployment, payments, protocol state, arbitrage actions).
2. **Consume events** relevant to its role (e.g., revenue OS listens to `revenue_delta` and `payment_settled`, orchestrators listen to `agent_decision` and `onchain_event`).

## 2. Tier‑1 Systems (Arbitrage Core)

From `SYSTEM_REGISTRY.json`:

**Priority Tier 1 systems (full‑stack arbitrage targets):**

- `autonomous-butler-core` — AI orchestration & event bus host
- `garcar-payments` — Stripe payments layer
- `systems-master-hub` — master registry & upgrade orchestrator
- `zeus-dashboard` — primary unified UI
- `garcar-apex-nexus` — unified control plane
- `autonomous-orchestrator-core` — 332‑systems master orchestrator
- `garcar-singularity-grid` — master orchestrator / singularity grid
- `APEX-AI-ENGINE` — commerce engine
- `nwu-protocol` — blockchain protocol
- `unprecedented-autonomous-revenue-os` — revenue OS

Each Tier‑1 system is assigned:

- **Role** (from `SYSTEM_REGISTRY.json`)
- **Required event types**
- **Required Garcar Base Contract endpoints** (`/health`, `/meta`, `/metrics`, `/events`)

### Role → Event mapping

- `autonomous-butler-core` (`ai_orchestration`)
  - Emits: `agent_decision`, `workflow_started`, `workflow_completed`
  - Consumes: `revenue_delta`, `payment_settled`, `onchain_event`

- `garcar-payments` (`payments`)
  - Emits: `payment_initiated`, `payment_settled`, `refund_processed`
  - Consumes: `arbitrage_execution_request`, `subscription_upgraded`

- `unprecedented-autonomous-revenue-os` (`revenue_os`)
  - Emits: `subscription_upgraded`, `tier_migration`, `pricing_changed`
  - Consumes: `revenue_intelligence_signal`, `payment_settled`

- `APEX-AI-ENGINE` (`commerce_engine`)
  - Emits: `offer_generated`, `route_selected`, `channel_priority_changed`
  - Consumes: `revenue_delta`, `acquisition_signal`, `wealth_rebalance_signal`

- `nwu-protocol` (`blockchain_protocol`)
  - Emits: `onchain_event`, `yield_changed`, `liquidity_moved`
  - Consumes: `arbitrage_execution_request`, `risk_signal`

- `systems-master-hub` (`master_registry`)
  - Emits: `upgrade_cycle_started`, `upgrade_pr_opened`, `system_compliance_changed`
  - Consumes: `health_degraded`, `metrics_anomaly`, `arbitrage_opportunity`

- `garcar-apex-nexus` (`unified_control_plane`)
  - Emits: `control_command`, `dashboard_refresh`
  - Consumes: all Tier‑1 events for visualization.

- `zeus-dashboard` / `atlas-dashboard` (`ui_control_plane`, `ui_analytics`)
  - Emit: `ui_action`
  - Consume: all arbitrage and revenue events for display.

## 3. Garcar Base Contract Alignment

For each Tier‑1 system, the following HTTP/JSON endpoints MUST exist, mirroring the implementation in `nexusai-platform`:

- `GET /health` — base health + role + version
- `GET /meta` — system name, ID, role, owner, capabilities, deployment info
- `GET /metrics` — revenue, monetization, uptime, latency, resources, agent stats
- `GET /events` — recent event stream (local view or bus proxy)

This provides:

- A unified control-plane contract (NexusAI / `garcar-apex-nexus` / dashboards).
- Consistent metadata and metrics for arbitrage agents and upgrade loops.

## 4. Arbitrage Agent Loop

**Location:** `autonomous-orchestrator-core` + `garcar-singularity-grid`

**Inputs:**

- Bus topics: `revenue_delta`, `payment_settled`, `yield_changed`, `occupancy_changed`, `protocol_state`, `agent_decision`
- Metrics: `{system}/metrics` from all Tier‑1 systems

**Core loop:**

1. **Ingest** arbitrage‑relevant metrics:
   - Price, yield, CAC, LTV, MRR, churn, funnel conversion, latency, risk scores.

2. **Detect spreads:**
   - Between channels, tiers, protocols, and capital pools.

3. **Compute decisions:**
   - `arbitrage_execution_request` events (what to change: price, tier, campaign, allocation).

4. **Route to execution systems:**
   - `garcar-payments`, `unprecedented-autonomous-revenue-os`, `APEX-AI-ENGINE`, `nwu-protocol`, `garcar-autonomous-wealth-system`.

5. **Observe results:**
   - New `revenue_delta`, `yield_changed`, `subscription_upgraded` events.

6. **Write back intelligence:**
   - Emit `revenue_intelligence_signal` and `wealth_rebalance_signal`.

## 5. Nightly Upgrade Loop (Arbitrage‑Aware)

Existing directive from `SYSTEM_REGISTRY.json`:

> Every night at 02:00 UTC, the master-control-plane reads the last commit per repo, diffs against the previous state, and opens a PR with the next evolutionary upgrade. No system is repeated — only improved.

This now includes:

- Contract compliance checks: `/health`, `/meta`, `/metrics`, `/events` present.
- Event bus compliance checks: emits/consumes required Tier‑1 topics.
- Arbitrage performance checks: spreads found vs. spreads executed, net benefit.

## 6. Activation Runbook (First Arbitrage Sweep)

1. **Harmonization:**
   - Run `python3 harmonize_system.py` to clone/build core domains into `GARRETT_ENTERPRISE_SYSTEM` and generate `system_manifest.json`.

2. **Contract stubs:**
   - For each Tier‑1 system, add or verify `/health`, `/meta`, `/metrics`, `/events` endpoints matching NexusAI's implementation.

3. **Event bus wiring:**
   - Configure `autonomous-butler-core` with NATS or Redis Streams.
   - Add basic emit/consume hooks for required topics in Tier‑1 systems.

4. **Control-plane wiring:**
   - Point `zeus-dashboard` and `atlas-dashboard` at the Tier‑1 metrics and events.

5. **Arbitrage loop:**
   - Enable the first arbitrage agent loop in `autonomous-orchestrator-core` / `garcar-singularity-grid` with a small subset of signals (e.g., MRR vs. CAC vs. on‑chain yield).

6. **Nightly evolutionary upgrade:**
   - Confirm `.github/workflows/nightly-upgrade-loop.yml` integrates contract and bus checks as part of its PR logic.

This grid definition is the "max power" arbitrage architecture that sits on top of your existing systems and registries. It is intentionally written to be executed incrementally but is designed from day one for unprecedented multiplex autonomous arbitrage across revenue, protocols, deployments, and wealth systems.
