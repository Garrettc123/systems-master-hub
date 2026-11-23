# Garcar QIL — Query Intelligence Layer v1

**Implementation:** `scripts/qil.py`, using the safe read-only snapshot produced by `scripts/sync_to_master_hub.py`.

This is a local diagnostic query interpreter, **not** a language model, arbitrary SQL interface, wallet operator, or vulnerability scanner.

## Contract

A QIL question is an exact member of the bounded catalog:

| Query | Returned values | What it does not establish |
|---|---|---|
| `overview` | coverage of expected tables, available question types | production correctness, revenue |
| `integrity` | SQLite quick-check status, snapshot age, schema match | application invariants or trusted attestation |
| `queue` | allowlisted task-status counts, aggregate total | real autonomous agent execution |
| `audit` | status counts for up to ten latest audit events | full history, chain authenticity |
| `quarantine` | dead-letter aggregate count, or unknown | safety or cleanliness when absent |
| `priorities` | bounded operator-review suggestions | permission to perform external actions |

All responses are JSON objects containing `qil_version`, `query_id`, `answer_status`, `limitations`, provenance flags, aggregated `data`, and explicit false flags for external execution, verified bounty payouts, and verified revenue.

Every question first checks the source snapshot schema, SQLite integrity, coverage, and current UTC date. An absent or malformed table remains **blocked**; an unknown count is represented by `null`, never zero. Supported aggregate values still do not authenticate their underlying source.

The interpreter does not accept user SQL strings. Arbitrary values, identifiers, private events, credentials, paths, token balances or wallet addresses are not included in result fields. No network calls, SQL mutation, Git commit/push, alerts, message sends or bounty claims occur.

## Termux / Lenovo

From a checkout containing the QIL script:

```sh
# Inspect known QIL capabilities without opening any database
python scripts/qil.py --list-queries

# Resolve exactly one known local DB; query without exporting
python scripts/qil.py --db auto --query overview
python scripts/qil.py --db auto --query priorities

# If multiple DBs exist, use the actual absolute file path
python scripts/qil.py --db /absolute/path/garcar_forge_operational.db --query queue
```

If no database is discovered, use:

```sh
python scripts/sync_to_master_hub.py --locate-db
```

This is a bounded search of a small set of operator workspaces; it does not inspect external hosts. The local SQLite file must already exist. Creating synthetic/empty state to make the query succeed is prohibited.

## Operational interpretation

- `answer_status=ready` means that the limited snapshot checks passed. It does **not** mean the business, agents, bounty pipeline or payments are ready.
- `answer_status=blocked` means do not automate any action from that response.
- `priorities` is advisory only: quarantine review, failures, pending approvals, or missing evidence. It does not automatically execute tasks.
- A successful query cannot prove a paid bounty, investor valuation, ARR, or contract acceptance.

## Verification and release boundary

CI compiles QIL and runs `tests/test_qil.py` and the existing SQLite sync safety tests across Python 3.11, 3.12, and 3.13.

QIL is currently committed to a **draft feature branch**, not yet merged to `main` or installed on any physical Termux/Lenovo machine. No DB data or sample "success metrics" from those devices have been published.

Next production-grade extensions would require an authenticated private agent runtime, durable database connections, schema migrations, signed evidence, rate limits, and application-level authorization. Those are explicitly **not** implied by QIL v1.
