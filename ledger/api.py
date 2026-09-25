"""
FastAPI surface for the Revenue Ledger.

  GET  /ledger/summary          — ZEUS KPI endpoint
  GET  /ledger/summary?days=7
  POST /ledger/tx               — post a transaction (systems must call within 24h)

Run:
  uvicorn ledger.api:app --host 0.0.0.0 --port 8088
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .gc_ledger import post_transaction, summary

app = FastAPI(title="Garcar Revenue Ledger", version="1.0.0")


class TxIn(BaseModel):
    system: str
    amount_cents: int
    currency: str = "usd"
    source: str = "stripe"
    ref: str = ""
    meta: Dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "gc_ledger"}


@app.get("/ledger/summary")
def ledger_summary(days: Optional[int] = None) -> dict:
    return summary(days=days)


@app.post("/ledger/tx")
def ledger_tx(body: TxIn) -> dict:
    if not body.system:
        raise HTTPException(400, "system required")
    return post_transaction(
        system=body.system,
        amount_cents=body.amount_cents,
        currency=body.currency,
        source=body.source,
        ref=body.ref,
        meta=body.meta,
    )
