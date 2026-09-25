"""
Garcar Revenue Ledger (gc_ledger)
================================
Every system that touches money MUST post here within 24h of the transaction.

Usage:
  from ledger.gc_ledger import post_transaction, summary
  post_transaction(system="NEXUS", amount_cents=4700, currency="usd", source="stripe", ref="ch_xxx")
  print(summary())

Storage: local JSONL by default (ledger/data/transactions.jsonl).
Optional Redis stream when UPSTASH / REDIS_URL is set (also publishes bus event).
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)
LEDGER_FILE = DATA / "transactions.jsonl"
_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def post_transaction(
    *,
    system: str,
    amount_cents: int,
    currency: str = "usd",
    source: str = "stripe",
    ref: str = "",
    meta: Optional[dict] = None,
) -> dict:
    """Append one money event. amount_cents can be negative for refunds."""
    entry = {
        "ts": _now(),
        "system": system,
        "amount_cents": int(amount_cents),
        "currency": currency.lower(),
        "source": source,
        "ref": ref,
        "meta": meta or {},
    }
    with _lock:
        with LEDGER_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    # Fire event mesh if available
    try:
        from garcar_bus import bus
        bus.publish(
            "revenue.captured",
            {
                "system": system,
                "amount_cents": amount_cents,
                "currency": currency,
                "source": source,
                "ref": ref,
            },
        )
    except Exception:
        pass

    return entry


def _load_all() -> List[dict]:
    if not LEDGER_FILE.exists():
        return []
    rows = []
    with LEDGER_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def summary(days: Optional[int] = None) -> Dict[str, Any]:
    """Aggregate for ZEUS / command center KPIs."""
    rows = _load_all()
    if days is not None:
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
        filtered = []
        for r in rows:
            try:
                ts = datetime.fromisoformat(r["ts"].replace("Z", "+00:00")).timestamp()
                if ts >= cutoff:
                    filtered.append(r)
            except Exception:
                filtered.append(r)
        rows = filtered

    by_system: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    total = 0
    count = 0
    for r in rows:
        amt = int(r.get("amount_cents") or 0)
        total += amt
        count += 1
        sys = r.get("system") or "unknown"
        src = r.get("source") or "unknown"
        by_system[sys] = by_system.get(sys, 0) + amt
        by_source[src] = by_source.get(src, 0) + amt

    return {
        "generated_at": _now(),
        "transaction_count": count,
        "total_cents": total,
        "total_usd": round(total / 100, 2),
        "by_system": by_system,
        "by_source": by_source,
        "window_days": days,
    }
