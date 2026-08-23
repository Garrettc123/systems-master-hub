"""
Garcar Normalized Event Models
Canonical shape for every inbound webhook and internal signal.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class EventSource(str, Enum):
    STRIPE = "stripe"
    HUBSPOT = "hubspot"
    APOLLO = "apollo"
    LINEAR = "linear"
    NOTION = "notion"
    GITHUB = "github"
    SLACK = "slack"
    RAILWAY = "railway"
    CLOUDFLARE = "cloudflare"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


class ActorType(str, Enum):
    CUSTOMER = "customer"
    USER = "user"
    SYSTEM = "system"
    AGENT = "agent"
    UNKNOWN = "unknown"


class Actor(BaseModel):
    type: ActorType = ActorType.UNKNOWN
    id: Optional[str] = None
    email: Optional[str] = None


class NormalizedEvent(BaseModel):
    event_id: str = Field(..., min_length=8, max_length=255)
    source: EventSource
    event_type: str = Field(..., pattern=r"^[a-z0-9]+(\.[a-z0-9_]+)+$")
    occurred_at: datetime
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    idempotency_key: Optional[str] = None
    correlation_id: Optional[str] = None
    actor: Optional[Actor] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    raw: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0.0"

    def model_post_init(self, __context: Any) -> None:
        if not self.idempotency_key:
            self.idempotency_key = f"{self.source.value}:{self.event_id}"

    @field_validator("occurred_at", "received_at", mode="before")
    @classmethod
    def ensure_aware(cls, v: Any) -> datetime:
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    def to_storage_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class HandlerResult(BaseModel):
    handler_name: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None


class ProcessOutcome(BaseModel):
    event_id: str
    idempotency_key: str
    status: str
    handlers: list[HandlerResult] = Field(default_factory=list)
    message: Optional[str] = None
