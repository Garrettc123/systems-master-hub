"""
Bridge: make the existing webhook-core keyless without rewriting it.
Import this instead of webhooks.security / direct env access.
"""

from __future__ import annotations

from typing import Any, Dict

from resolver import get_resolver
from providers import verify_stripe_webhook, supabase_insert


def keyless_require_valid_stripe(payload: bytes, sig_header: str) -> None:
    """Drop-in replacement for require_valid_stripe that never reads os.environ."""
    verify_stripe_webhook(payload, sig_header)


def keyless_sb_insert(table: str, row: Dict[str, Any]) -> bool:
    """Drop-in for the _sb_insert helpers in subscribers."""
    return supabase_insert(table, row)


def keyless_hubspot_token() -> str | None:
    return get_resolver().get("HUBSPOT_API_KEY")


def keyless_linear_token() -> str | None:
    return get_resolver().get("LINEAR_API_KEY")
