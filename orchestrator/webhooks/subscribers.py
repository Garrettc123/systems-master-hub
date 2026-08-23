"""
Garcar Production Subscribers — money path, CRM, observability.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .models import NormalizedEvent
from .router import WebhookRouter


def _supabase() -> Optional[tuple]:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if url and key:
        return url, key
    return None


def _sb_insert(table: str, row: Dict[str, Any]) -> bool:
    creds = _supabase()
    if not creds:
        return False
    url, key = creds
    try:
        import requests
        r = requests.post(
            f"{url}/rest/v1/{table}",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=row,
            timeout=8,
        )
        return r.status_code < 300
    except Exception:
        return False


def handle_payment_succeeded(event: NormalizedEvent) -> Dict[str, Any]:
    amount_cents = event.payload.get("amount_total") or event.payload.get("amount_paid") or 0
    amount_usd = round(float(amount_cents) / 100.0, 2) if amount_cents else 0.0
    currency = (event.payload.get("currency") or "usd").lower()
    customer_id = event.payload.get("customer_id")
    meta = event.payload.get("metadata") or {}
    lead_email = meta.get("lead_email") or (event.actor.email if event.actor else None)

    _sb_insert("lead_outcomes", {
        "outcome_type": "payment_succeeded",
        "revenue_usd": amount_usd,
        "hubspot_contact_id": meta.get("hubspot_contact_id"),
        "genome_id": event.metadata.get("genome_id") or meta.get("genome_id"),
        "original_run_id": event.metadata.get("run_id") or meta.get("agent"),
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "raw_payload": {
            "event_id": event.event_id,
            "customer_id": customer_id,
            "lead_email": lead_email,
            "currency": currency,
            "stripe_type": event.payload.get("stripe_type"),
        },
    })

    _sb_insert("wealth_pulse", {
        "pulse_score": min(100.0, 50.0 + (amount_usd / 20.0)),
        "components": {
            "last_payment_usd": amount_usd,
            "source": "stripe",
            "event_id": event.event_id,
        },
        "mrr_protected_usd": amount_usd if "subscription" in (event.payload.get("stripe_type") or "") else 0,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "action": "revenue_recorded",
        "amount_usd": amount_usd,
        "currency": currency,
        "customer_id": customer_id,
        "lead_email": lead_email,
        "persisted": True,
    }


def handle_subscription_created(event: NormalizedEvent) -> Dict[str, Any]:
    return {
        "action": "subscription_activated",
        "subscription_id": event.payload.get("subscription_id"),
        "customer_id": event.payload.get("customer_id"),
    }


def handle_subscription_canceled(event: NormalizedEvent) -> Dict[str, Any]:
    return {
        "action": "subscription_canceled",
        "subscription_id": event.payload.get("subscription_id"),
        "customer_id": event.payload.get("customer_id"),
        "severity": "medium",
    }


def handle_payment_failed(event: NormalizedEvent) -> Dict[str, Any]:
    return {
        "action": "payment_failed_alert",
        "customer_id": event.payload.get("customer_id"),
        "severity": "high",
        "event_id": event.event_id,
    }


def handle_hubspot_revenue(event: NormalizedEvent) -> Dict[str, Any]:
    api_key = os.environ.get("HUBSPOT_API_KEY")
    if not api_key:
        return {"action": "hubspot_skipped", "reason": "HUBSPOT_API_KEY missing"}
    meta = event.payload.get("metadata") or {}
    contact_id = meta.get("hubspot_contact_id")
    amount_cents = event.payload.get("amount_total") or 0
    amount_usd = round(float(amount_cents) / 100.0, 2)
    if not contact_id:
        return {"action": "hubspot_skipped", "reason": "no hubspot_contact_id"}
    try:
        import requests
        r = requests.patch(
            f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"properties": {
                "garcar_last_payment_usd": str(amount_usd),
                "garcar_last_payment_at": datetime.now(timezone.utc).isoformat(),
                "garcar_payment_event_id": event.event_id,
            }},
            timeout=8,
        )
        return {"action": "hubspot_updated", "contact_id": contact_id, "status_code": r.status_code}
    except Exception as exc:
        return {"action": "hubspot_error", "error": str(exc)}


def handle_linear_close(event: NormalizedEvent) -> Dict[str, Any]:
    if not os.environ.get("LINEAR_API_KEY"):
        return {"action": "linear_skipped", "reason": "LINEAR_API_KEY missing"}
    meta = event.payload.get("metadata") or {}
    issue_id = meta.get("linear_issue_id") or meta.get("linear_id")
    if not issue_id:
        return {"action": "linear_skipped", "reason": "no linear_issue_id"}
    return {"action": "linear_close_queued", "issue_id": issue_id}


def handle_observability(event: NormalizedEvent) -> Optional[Dict[str, Any]]:
    _sb_insert("agent_runs", {
        "agent_name": "webhook_router",
        "run_id": f"evt-{event.event_id}",
        "trigger_type": "webhook",
        "status": "success",
        "input_payload": {"source": event.source.value, "event_type": event.event_type},
        "output_result": {"payload_keys": list(event.payload.keys())},
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "environment": "production",
    })
    return {"observed": True, "event_type": event.event_type, "source": event.source.value}


def build_default_router(store=None) -> WebhookRouter:
    router = WebhookRouter(store=store)
    router.register("payment.succeeded", "stripe.revenue", handle_payment_succeeded)
    router.register("subscription.created", "stripe.subscription", handle_subscription_created)
    router.register("subscription.canceled", "stripe.subscription", handle_subscription_canceled)
    router.register("payment.failed", "stripe.alert", handle_payment_failed)
    router.register("payment.succeeded", "hubspot.revenue", handle_hubspot_revenue)
    router.register("payment.succeeded", "linear.close", handle_linear_close)
    router.register("*", "observability.pulse", handle_observability)
    return router
