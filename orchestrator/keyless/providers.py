"""
Keyless Providers
=================
Thin facades that materialize secrets only for the exact call that needs them.
Never hold long-lived clients that embed secrets in their constructor if avoidable.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from resolver import KeylessError, get_resolver


def stripe_client():
    """Returns a configured stripe module for the duration of the call."""
    import stripe
    resolver = get_resolver()
    key = resolver.get("STRIPE_SECRET_KEY", required=True)
    stripe.api_key = key
    return stripe


def verify_stripe_webhook(payload: bytes, sig_header: str) -> None:
    """Signature check using keyless secret. Raises on failure."""
    resolver = get_resolver()
    secret = resolver.get("STRIPE_WEBHOOK_SECRET", required=True)
    import hashlib
    import hmac
    import time

    if not sig_header:
        raise PermissionError("Missing Stripe-Signature header")

    elements = dict(item.split("=", 1) for item in sig_header.split(",") if "=" in item)
    timestamp = int(elements.get("t", "0"))
    v1_sigs = [v for k, v in elements.items() if k == "v1"]
    if not v1_sigs:
        raise PermissionError("No v1 signature found")

    if abs(time.time() - timestamp) > 300:
        raise PermissionError("Timestamp outside tolerance")

    signed = f"{timestamp}.{payload.decode('utf-8')}"
    expected = hmac.new(
        secret.encode("utf-8"),
        signed.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not any(hmac.compare_digest(expected, s) for s in v1_sigs):
        raise PermissionError("Signature mismatch")


def supabase_headers() -> Dict[str, str]:
    """Short-lived headers for a single REST call."""
    r = get_resolver()
    url = r.get("SUPABASE_URL", required=True)
    key = r.get("SUPABASE_SERVICE_KEY", required=True)
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
        "_base_url": url,
    }


def supabase_insert(table: str, row: Dict[str, Any]) -> bool:
    headers = supabase_headers()
    base = headers.pop("_base_url")
    try:
        import requests
        resp = requests.post(
            f"{base}/rest/v1/{table}",
            headers=headers,
            json=row,
            timeout=8,
        )
        return resp.status_code < 300
    except Exception:
        return False


def hubspot_token() -> Optional[str]:
    return get_resolver().get("HUBSPOT_API_KEY")


def linear_token() -> Optional[str]:
    return get_resolver().get("LINEAR_API_KEY")


def apollo_key() -> Optional[str]:
    return get_resolver().get("APOLLO_API_KEY")


def health() -> Dict[str, Any]:
    """Key presence without values — safe for status endpoints."""
    r = get_resolver()
    return {
        "revenue_ready": all(
            r.get(k) is not None for k in r.REQUIRED_FOR_REVENUE
        ),
        "optional": r.available(*r.OPTIONAL),
        "keyless": True,
    }
