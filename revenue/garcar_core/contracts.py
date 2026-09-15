from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class ActionKind(str, Enum):
    QUALIFY = "qualify"
    MESSAGE = "message"
    ASSIGN = "assign"
    BOOK = "book"
    FOLLOW_UP = "follow_up"
    NOTIFY = "notify"
    RECONCILE = "reconcile"


class Decision(str, Enum):
    DRAFT = "draft"
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class Action:
    action_id: str
    tenant_id: str
    lead_id: str
    kind: ActionKind
    payload: dict[str, Any]
    decision: Decision = Decision.DRAFT


class MessagingAdapter(Protocol):
    def send(self, action: Action) -> str: ...


class CRMAdapter(Protocol):
    def upsert_lead(self, action: Action) -> str: ...


class CalendarAdapter(Protocol):
    def create_booking(self, action: Action) -> str: ...


class PolicyGate(Protocol):
    def evaluate(self, action: Action) -> Decision: ...


def governed_action(action: Action, decision: Decision) -> Action:
    """Return a new action with an explicit decision; adapters must enforce it."""
    return Action(
        action_id=action.action_id,
        tenant_id=action.tenant_id,
        lead_id=action.lead_id,
        kind=action.kind,
        payload=dict(action.payload),
        decision=decision,
    )