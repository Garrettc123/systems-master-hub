from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LeadMetrics:
    tenant_id: str
    lead_id: str
    received_at: datetime
    first_response_at: datetime | None = None
    qualified_at: datetime | None = None
    booked_at: datetime | None = None
    estimated_at: datetime | None = None
    won_at: datetime | None = None
    lost_at: datetime | None = None
    recovered_at: datetime | None = None
    attributed_revenue_cents: int = 0


def elapsed_seconds(start: datetime, end: datetime | None) -> float | None:
    if end is None:
        return None
    return max(0.0, (end - start).total_seconds())


def metric_snapshot(m: LeadMetrics) -> dict[str, float | int | None | str]:
    return {
        "tenant_id": m.tenant_id,
        "lead_id": m.lead_id,
        "first_response_seconds": elapsed_seconds(m.received_at, m.first_response_at),
        "qualification_seconds": elapsed_seconds(m.received_at, m.qualified_at),
        "booking_seconds": elapsed_seconds(m.received_at, m.booked_at),
        "estimate_seconds": elapsed_seconds(m.received_at, m.estimated_at),
        "won_seconds": elapsed_seconds(m.received_at, m.won_at),
        "recovered": int(m.recovered_at is not None),
        "attributed_revenue_cents": m.attributed_revenue_cents,
    }