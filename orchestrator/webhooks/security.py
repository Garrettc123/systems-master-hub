"""
Garcar Webhook Security
Stripe signature verification is non-negotiable.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Optional, Tuple


def verify_stripe_signature(
    payload: bytes,
    sig_header: str,
    secret: Optional[str] = None,
    tolerance: int = 300,
) -> Tuple[bool, str]:
    secret = secret or os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret:
        return False, "STRIPE_WEBHOOK_SECRET not configured"

    if not sig_header:
        return False, "Missing Stripe-Signature header"

    try:
        elements = dict(
            item.split("=", 1) for item in sig_header.split(",") if "=" in item
        )
        timestamp = int(elements.get("t", "0"))
        v1_signatures = [v for k, v in elements.items() if k == "v1"]

        if not v1_signatures:
            return False, "No v1 signature found"

        if abs(time.time() - timestamp) > tolerance:
            return False, f"Timestamp outside tolerance ({tolerance}s)"

        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        for sig in v1_signatures:
            if hmac.compare_digest(expected, sig):
                return True, "ok"

        return False, "Signature mismatch"

    except Exception as exc:
        return False, f"Signature parse error: {exc}"


def require_valid_stripe(
    payload: bytes,
    sig_header: str,
    secret: Optional[str] = None,
) -> None:
    valid, reason = verify_stripe_signature(payload, sig_header, secret)
    if not valid:
        raise PermissionError(f"Stripe webhook rejected: {reason}")
