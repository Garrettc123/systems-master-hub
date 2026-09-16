from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from threading import Lock
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title="Garcar Core — Lead Response Engine", version="1.0.0")


class Source(str, Enum):
    phone = "phone"
    web_form = "web_form"
    sms = "sms"
    referral = "referral"
    other = "other"


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


class Customer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=320)


class ServiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service: str = Field(min_length=1, max_length=160)
    city: str | None = Field(default=None, max_length=120)
    urgency: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=2000)


class LeadEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=3, max_length=200)
    tenant_id: str = Field(min_length=3, max_length=120)
    source: Source
    occurred_at: datetime
    customer: Customer
    request: ServiceRequest


class StoredLead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lead_id: str
    tenant_id: str
    event_id: str
    source: Source
    status: LeadStatus
    customer: Customer
    request: ServiceRequest
    owner: str | None = None
    next_action: str
    policy: str
    created_at: datetime
    updated_at: datetime


class InMemoryStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self.events: dict[str, str] = {}
        self.leads: dict[str, StoredLead] = {}
        self.audit: list[dict[str, Any]] = []

    def seen_event(self, tenant_id: str, event_id: str) -> str | None:
        with self._lock:
            return self.events.get(f"{tenant_id}:{event_id}")

    def save(self, event_key: str, lead: StoredLead) -> None:
        with self._lock:
            self.events[event_key] = lead.lead_id
            self.leads[lead.lead_id] = lead
            self.audit.append({
                "at": datetime.now(timezone.utc).isoformat(),
                "action": "lead_received",
                "tenant_id": lead.tenant_id,
                "lead_id": lead.lead_id,
                "status": lead.status.value,
            })


store = InMemoryStore()


def _lead_id(event: LeadEvent) -> str:
    material = "|".join(
        [
            event.tenant_id,
            event.customer.phone or "",
            event.customer.email or "",
            event.request.service.lower().strip(),
        ]
    )
    return "lead_" + sha256(material.encode("utf-8")).hexdigest()[:24]


def policy_decision(event: LeadEvent) -> str:
    """Return a deterministic policy class; never perform an external side effect."""
    if not event.customer.phone and not event.customer.email:
        return "ESCALATE_NO_CONTACT_METHOD"
    if event.request.notes and any(
        token in event.request.notes.lower()
        for token in ("password", "ssn", "social security", "card number")
    ):
        return "BLOCK_SENSITIVE_DATA"
    return "ALLOW_DRAFT_ACTIONS"


def build_lead(event: LeadEvent) -> StoredLead:
    now = datetime.now(timezone.utc)
    decision = policy_decision(event)
    if decision == "BLOCK_SENSITIVE_DATA":
        status = LeadStatus.BLOCKED
        next_action = "operator_review_sensitive_input"
    elif decision == "ESCALATE_NO_CONTACT_METHOD":
        status = LeadStatus.ESCALATED
        next_action = "obtain_valid_contact_method"
    else:
        status = LeadStatus.QUALIFYING
        next_action = "send_or_prepare_qualification_prompt"

    return StoredLead(
        lead_id=_lead_id(event),
        tenant_id=event.tenant_id,
        event_id=event.event_id,
        source=event.source,
        status=status,
        customer=event.customer,
        request=event.request,
        owner=None,
        next_action=next_action,
        policy=decision,
        created_at=now,
        updated_at=now,
    )


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "garcar-core"}


@app.post("/v1/events/lead", response_model=StoredLead, status_code=202)
def ingest_lead(
    event: LeadEvent,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> StoredLead:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")
    if len(idempotency_key) > 200:
        raise HTTPException(status_code=400, detail="Idempotency-Key too long")

    event_key = f"{event.tenant_id}:{idempotency_key}"
    with store._lock:
        existing_id = store.events.get(event_key)
        if existing_id:
            return store.leads[existing_id]

    lead = build_lead(event)
    store.save(event_key, lead)
    return lead
