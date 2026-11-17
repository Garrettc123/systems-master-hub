# Garcar Swarm State — Redacted SQLite Sync and Investor Evidence

**Status:** source implementation prepared for local operator use. This document does not assert that a Termux or Lenovo database was inspected or synchronized.

**Destination:** [Garrettc123/systems-master-hub](https://github.com/Garrettc123/systems-master-hub) is a PUBLIC GitHub repository. Local DB files, raw events, hostnames, wallet/account identifiers, API credentials, customer contact information and private bounty findings must never be published.

## 1. Local diagnostics (Termux or Lenovo)

With Python 3 available, the entrypoint can be invoked from any working directory, including `~/apex-revenue-system`. First locate the real database (bounded local search):

```sh
python scripts/sync_to_master_hub.py --locate-db
python scripts/sync_to_master_hub.py --db auto --diagnose
```

The `--locate-db` option prints matching absolute paths without opening or uploading their content. `--db auto` selects a source only when exactly one match is found; otherwise specify the correct absolute `--db` path. A missing database is never silently created. The `--diagnose` operation requires no hub clone and does not create or push a telemetry report. It opens SQLite in read-only mode; a concurrent application's WAL/checkpoint lifecycle may still change auxiliary files independently of the exporter.

## 2. Export aggregate state locally

```sh
python scripts/sync_to_master_hub.py --repo . --db auto
```

The output file is `telemetry/public_swarm_snapshot.json`. **It has not been generated or uploaded from the operator's actual machine in this change.** The payload includes:

- Date in UTC and schema version;
- SQLite quick-check result;
- allowlisted task-status counts, collapsing unrecognized labels into `other`;
- allowlisted statuses of the latest ten ledger events (never their IDs or bodies);
- quarantine count where its table exists;
- separate `missing` and `schema_mismatch` states, explicit warnings;
- content digest (not a cryptographic signature);
- explicit false/unknown revenue, payout, valuation claims.

The payload must NOT include raw event IDs, types, messages, precise timestamps, customer information, node names, wallets or keys. A missing table is **not** a clean quarantine or a healthy queue.

### Snapshot semantics

The exporter uses `mode=ro`, `PRAGMA query_only`, and one read transaction. The underlying SQLite WAL may still be modified by the application that owns it; this script does not launch agents or write state. A successful integrity check establishes only the check's limited result, not system correctness. Full availability depends on the local SQLite schema, permissions and workload.

The export creates a local report even if the schema is incomplete, returns exit code 2 for incomplete coverage, and blocks publishing incomplete or integrity-failed snapshots.

## 3. Optional publication to PUBLIC GitHub

**No automatic public publication is enabled by default.** Even aggregate counts may reveal operational characteristics. Publication is an intentional opt-in:

```sh
git switch -c telemetry/swarm-2026-11-17
python scripts/sync_to_master_hub.py --repo . --db auto --push --allow-public
```

The tool checks the exact GitHub remote even for local export (an Apex checkout is rejected), refuses to push `main`, refuses unrelated dirty files, stages only `telemetry/public_swarm_snapshot.json`, and pushes to a `telemetry/swarm-YYYY-MM-DD` review branch. It does not open or merge a pull request. Review the resulting diff before public exposure; using a private repository or approved private storage is preferable for sensitive or operationally detailed telemetry.

For noninteractive scheduling, invoke the **local export-only** command from an existing approved Termux supervisor or system scheduler. Enable public push only when expressly approved for that environment. No automation was installed on the operator's devices by this GitHub change.

## 4. Investor due-diligence boundaries

An investor-facing narrative should distinguish:

| Evidence category | Source needed | What this export does NOT prove |
|---|---|---|
| Working software | CI, reproducible build, deployed endpoint, tested acceptance contract | Commercial use or profitability |
| Operating reliability | Time-series uptime, incident records, backups and recovery tests | End-to-end production readiness |
| Pipeline | Verified interested buyers, current stages and consent records | Revenue, paid customers or booked ARR |
| Revenue | Completed invoices, settled payments and contracts reconciled | Revenue from GitHub bounty labels |
| Bounty earnings | Accepted report/work and independently reconciled payout | Rewards from candidate counts |
| Intellectual property | Ownership, license review, third-party code obligations | Market value from repository count |
| Cash flow | Reconciled costs, receipts and financial statements | Forecast accuracy |
| Valuation | Explicit assumptions and triangulated valuation methods | A justified market price from activity metrics |

The supplied StartupFundraising.com article lists venture-capital, cost-to-duplicate, Berkus, DCF, comparables, scorecard, risk-factor and stage-based approaches. These are possible **frameworks**, not valuations of Garcar Enterprise. Its illustration of a $200,000 investment for 10% implies a $2 million **post-money** and $1.8 million **pre-money** valuation (assuming newly issued equity and no complicating terms). The claimed rule of thumb that 100,000 customers supports $1 million in financing is not a dependable underwriting benchmark.

For Garcar, use verified paying customers, realized revenue, retained ARR, gross margin, defensible IP ownership, product reliability, distribution, costs and comparable transactions. Label absent items `unverified`, not `zero`. Never treat 55 discovered crypto bounty candidates or a green CI build as cash receipts.

## 5. Security and governance

This implementation follows the existing `SECURITY_PUBLIC_RELEASE.md` public-release contract: minimum necessary telemetry, no secrets, evidence-based gates, and fail-closed handling. No database content, real telemetry samples, investor financials, local device access or unsanctioned outreach are committed by this change.

**Testing:** `python -m unittest discover -s tests -p "test_swarm_state_sync.py" -v`, also run through GitHub Actions on Python 3.11/3.12/3.13.
