# Revenue Ledger contract (gc_ledger)

**Rule:** Any system that touches money (Stripe, crypto bounty, real-estate deal scored, etc.) MUST post to `gc_ledger` within 24 hours of the transaction.

## Endpoints (hub)

- `GET  /ledger/summary` — ZEUS command-center KPIs  
- `GET  /ledger/summary?days=7`  
- `POST /ledger/tx` body: `{ "system", "amount_cents", "currency", "source", "ref", "meta" }`

## Python helper

```python
from ledger.gc_ledger import post_transaction, summary

post_transaction(
    system="NEXUS-AI-CORE",
    amount_cents=4700,
    currency="usd",
    source="stripe",
    ref="ch_1ABC",
)
print(summary())
```

## Event Mesh coupling

`post_transaction` automatically publishes `revenue.captured` on the Event Mesh when `garcar_bus` is importable.

## RHNS-Edge

garcar-rhns-edge already has an evidence ledger (`src/rhns_edge/ledger.py`). Bridge it:

```python
# after local ledger write
from garcar_bus import bus
bus.publish("revenue.captured", {...})
# or call hub POST /ledger/tx
```
