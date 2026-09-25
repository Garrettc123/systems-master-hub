# Event Mesh drop-in — NEXUS / TITAN / APEX / RHNS-Edge

## 1. Install

```bash
pip install "git+https://github.com/Garrettc123/systems-master-hub.git#subdirectory=packages/garcar_bus"
# or copy packages/garcar_bus into the target repo
```

## 2. Env (Upstash free tier)

1. Create database at https://console.upstash.com  
2. Copy REST URL + TOKEN into secrets / .env:

```
UPSTASH_REDIS_REST_URL=https://....upstash.io
UPSTASH_REDIS_REST_TOKEN=...
```

## 3. Publish (any money or state change)

```python
from garcar_bus import bus

bus.publish("revenue.captured", {
    "system": "NEXUS-AI-CORE",
    "amount_cents": 4700,
    "currency": "usd",
    "source": "stripe",
    "ref": "ch_xxx",
})

bus.publish("system.health", {"system": "TITAN", "score": 82})
```

## 4. Subscribe (long-running process / worker)

```python
from garcar_bus import bus

def on_revenue(evt):
    print("money event", evt)
    # optional: also post to gc_ledger

bus.subscribe("revenue.captured", on_revenue)
bus.start_polling()
```

## 5. Wire checklist (do this in each of the four)

| System | Repo | Action |
|--------|------|--------|
| NEXUS | NEXUS-AI-CORE | add `garcar_bus` dep + publish on Stripe webhook |
| TITAN | TITAN-Autonomous-Business-Empire | publish on deal close |
| APEX | APEX-AI-ENGINE / garcar-apex-nexus | publish on agent cycle complete |
| RHNS-Edge | garcar-rhns-edge | already has ledger — publish Economic Delta Events onto bus |

After drop-in, every system converses through the mesh. ZEUS reads `/ledger/summary` for KPIs.
