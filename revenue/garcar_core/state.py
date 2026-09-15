from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LeadStatus(str, Enum):
    RECEIVED = "received"
    QUALIFYING = "qualifying"
    ASSIGNED = "assigned"
    BOOKING_PENDING = "booking_pending"
    FOLLOW_UP = "follow_up"
    WON = "won"
    LOST = "lost"
    STALE = "stale"
    BLOCKED = "blocked"
    ESCALATED = "escalated"


TERMINAL = {LeadStatus.WON, LeadStatus.LOST, LeadStatus.BLOCKED}

ALLOWED: dict[LeadStatus, set[LeadStatus]] = {
    LeadStatus.RECEIVED: {LeadStatus.QUALIFYING, LeadStatus.BLOCKED, LeadStatus.ESCALATED},
    LeadStatus.QUALIFYING: {LeadStatus.ASSIGNED, LeadStatus.ESCALATED, LeadStatus.STALE},
    LeadStatus.ASSIGNED: {LeadStatus.BOOKING_PENDING, LeadStatus.FOLLOW_UP, LeadStatus.ESCALATED, LeadStatus.STALE},
    LeadStatus.BOOKING_PENDING: {LeadStatus.FOLLOW_UP, LeadStatus.WON, LeadStatus.LOST, LeadStatus.STALE},
    LeadStatus.FOLLOW_UP: {LeadStatus.BOOKING_PENDING, LeadStatus.WON, LeadStatus.LOST, LeadStatus.STALE},
    LeadStatus.STALE: {LeadStatus.FOLLOW_UP, LeadStatus.LOST, LeadStatus.ESCALATED},
    LeadStatus.ESCALATED: {LeadStatus.QUALIFYING, LeadStatus.ASSIGNED, LeadStatus.LOST},
    LeadStatus.WON: set(),
    LeadStatus.LOST: set(),
    LeadStatus.BLOCKED: set(),
}


@dataclass(frozen=True)
class Transition:
    lead_id: str
    tenant_id: str
    before: LeadStatus
    after: LeadStatus
    reason: str


def transition(lead_id: str, tenant_id: str, before: LeadStatus, after: LeadStatus, reason: str) -> Transition:
    if after not in ALLOWED.get(before, set()):
        raise ValueError(f"illegal lead transition: {before.value} -> {after.value}")
    if not reason.strip():
        raise ValueError("transition reason required")
    return Transition(lead_id, tenant_id, before, after, reason.strip())