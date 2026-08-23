"""
Garcar Webhook Router
Single ingress → normalize → claim (idempotent) → fan-out to subscribers.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from .idempotency import IdempotencyStore
from .models import EventSource, HandlerResult, NormalizedEvent, ProcessOutcome

Handler = Callable[[NormalizedEvent], Optional[Dict[str, Any]]]


class WebhookRouter:
    def __init__(self, store: Optional[IdempotencyStore] = None):
        self.store = store or IdempotencyStore()
        self._handlers: Dict[str, List[tuple[str, Handler]]] = {}

    def register(self, event_type: str, handler_name: str, handler: Handler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((handler_name, handler))

    async def process(self, event: NormalizedEvent) -> ProcessOutcome:
        claimed, existing = self.store.claim(event)

        if not claimed:
            status = (existing or {}).get("status", "unknown")
            return ProcessOutcome(
                event_id=event.event_id,
                idempotency_key=event.idempotency_key or "",
                status="already_processed",
                message=f"Event already seen (status={status})",
            )

        self.store.mark_processing(event.idempotency_key or "")

        handlers = self._handlers.get(event.event_type, [])
        handlers += self._handlers.get("*", [])

        results: List[HandlerResult] = []
        any_critical_failure = False

        for handler_name, handler_fn in handlers:
            start = time.perf_counter()
            try:
                result = handler_fn(event)
                duration = int((time.perf_counter() - start) * 1000)
                results.append(
                    HandlerResult(
                        handler_name=handler_name,
                        status="succeeded",
                        result=result,
                        duration_ms=duration,
                    )
                )
                if existing and existing.get("id"):
                    self.store.record_handler_run(
                        existing["id"], handler_name, "succeeded",
                        result=result, duration_ms=duration,
                    )
            except Exception as exc:
                duration = int((time.perf_counter() - start) * 1000)
                err = f"{type(exc).__name__}: {exc}"
                results.append(
                    HandlerResult(
                        handler_name=handler_name,
                        status="failed",
                        error_message=err,
                        duration_ms=duration,
                    )
                )
                if existing and existing.get("id"):
                    self.store.record_handler_run(
                        existing["id"], handler_name, "failed",
                        error_message=err, duration_ms=duration,
                    )
                if handler_name.startswith("stripe.") or handler_name.startswith("revenue."):
                    any_critical_failure = True

        final_status = "failed" if any_critical_failure else "processed"
        error_msg = None
        if any_critical_failure:
            failed = [r for r in results if r.status == "failed"]
            error_msg = "; ".join(f"{r.handler_name}: {r.error_message}" for r in failed)

        self.store.mark_processed(
            event.idempotency_key or "",
            status=final_status,
            error_message=error_msg,
        )

        return ProcessOutcome(
            event_id=event.event_id,
            idempotency_key=event.idempotency_key or "",
            status=final_status,
            handlers=results,
            message=error_msg,
        )


def normalize_stripe(raw: Dict[str, Any]) -> NormalizedEvent:
    from datetime import datetime, timezone

    event_id = raw.get("id") or f"stripe-{uuid4()}"
    stripe_type = raw.get("type", "unknown")
    created = raw.get("created")
    occurred = (
        datetime.fromtimestamp(created, tz=timezone.utc)
        if created
        else datetime.now(timezone.utc)
    )

    type_map = {
        "checkout.session.completed": "payment.succeeded",
        "payment_intent.succeeded": "payment.succeeded",
        "invoice.payment_succeeded": "payment.succeeded",
        "invoice.paid": "payment.succeeded",
        "customer.subscription.created": "subscription.created",
        "customer.subscription.updated": "subscription.updated",
        "customer.subscription.deleted": "subscription.canceled",
        "invoice.payment_failed": "payment.failed",
    }
    normalized_type = type_map.get(
        stripe_type, f"stripe.{stripe_type.replace('.', '_')}"
    )

    data_obj = raw.get("data", {}).get("object", {})
    actor_email = (
        data_obj.get("customer_email")
        or data_obj.get("receipt_email")
        or (data_obj.get("customer_details") or {}).get("email")
    )

    payload = {
        "stripe_type": stripe_type,
        "amount_total": data_obj.get("amount_total") or data_obj.get("amount_paid"),
        "currency": data_obj.get("currency"),
        "customer_id": data_obj.get("customer"),
        "subscription_id": data_obj.get("subscription"),
        "payment_intent": data_obj.get("payment_intent"),
        "metadata": data_obj.get("metadata") or {},
    }

    return NormalizedEvent(
        event_id=event_id,
        source=EventSource.STRIPE,
        event_type=normalized_type,
        occurred_at=occurred,
        actor={"type": "customer", "email": actor_email} if actor_email else None,
        payload=payload,
        raw=raw,
        metadata={"provider_event_type": stripe_type},
    )


def normalize_hubspot(raw: Dict[str, Any]) -> NormalizedEvent:
    from datetime import datetime, timezone

    event_id = str(raw.get("eventId") or raw.get("objectId") or uuid4())
    hs_type = raw.get("subscriptionType") or raw.get("type") or "unknown"
    return NormalizedEvent(
        event_id=event_id,
        source=EventSource.HUBSPOT,
        event_type=f"hubspot.{hs_type.replace('.', '_')}",
        occurred_at=datetime.now(timezone.utc),
        payload=raw,
        raw=raw,
    )
