from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

try:
    from .lead_store import IdempotencyConflict, LeadStore
except ImportError:
    from lead_store import IdempotencyConflict, LeadStore

app = FastAPI(title="Garcar Core — Lead Response Engine", version="1.1.0")


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


store = LeadStore(os.getenv("GARCAR_CORE_DB", ":memory:"))


def _lead_id(event: LeadEvent) -> str:
    material = "|".join([
        event.tenant_id,
        event.customer.phone or "",
        event.customer.email or "",
        event.request.service.lower().strip(),
    ])
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
    now = datetime.now(UTC)
    decision = policy_decision(event)
    if decision == "BLOCK_SENSITIVE_DATA":
        status, next_action = LeadStatus.BLOCKED, "operator_review_sensitive_input"
        request = event.request.model_copy(update={"notes": "Sensitive input withheld; operator review required."})
    elif decision == "ESCALATE_NO_CONTACT_METHOD":
        status, next_action = LeadStatus.ESCALATED, "obtain_valid_contact_method"
    else:
        status, next_action = LeadStatus.QUALIFYING, "send_or_prepare_qualification_prompt"
    if decision != "BLOCK_SENSITIVE_DATA":
        request = event.request
    return StoredLead(
        lead_id=_lead_id(event), tenant_id=event.tenant_id, event_id=event.event_id,
        source=event.source, status=status, customer=event.customer, request=request,
        owner=None, next_action=next_action, policy=decision, created_at=now, updated_at=now,
    )


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "garcar-core", "lead_storage": store.mode}


@app.post("/v1/events/lead", response_model=StoredLead, status_code=202)
def ingest_lead(
    event: LeadEvent,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> StoredLead:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")
    if len(idempotency_key) > 200:
        raise HTTPException(status_code=400, detail="Idempotency-Key too long")
    digest = sha256(json.dumps(event.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    try:
        record = store.ingest(event.tenant_id, idempotency_key, digest,
                              lambda: build_lead(event).model_dump(mode="json"))
        return StoredLead.model_validate(record)
    except IdempotencyConflict as error:
        raise HTTPException(status_code=409, detail="idempotency_key_reused_with_different_request") from error
    except sqlite3.Error as error:
        raise HTTPException(status_code=503, detail="lead_storage_unavailable") from error


# Read-only provider adapters; credentials are server-side environment variables.
# Keep Vercel Deployment Protection (SSO) enabled on every hostname serving this app.
try:
    from .phone_integrations import router as phone_integrations_router
    from .stack_status import router as stack_status_router
except ImportError:
    from phone_integrations import router as phone_integrations_router
    from stack_status import router as stack_status_router
app.include_router(phone_integrations_router)
app.include_router(stack_status_router)

# Serve the phone UI from the same protected FastAPI deployment as its API.
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="phone")
