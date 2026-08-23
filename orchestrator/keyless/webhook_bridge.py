"""
Bridge: make webhook-core keyless without rewriting it.
"""

from __future__ import annotations

from typing import Any, Dict

from .resolver import get_resolver
from .providers import verify_stripe_webhook, supabase_insert


def keyless_require_valid_stripe(payload: bytes, sig_header: str) -> None:
    verify_stripe_webhook(payload, sig_header)


def keyless_sb_insert(table: str, row: Dict[str, Any]) -> bool:
    return supabase_insert(table, row)


def keyless_hubspot_token() -> str | None:
    return get_resolver().get("HUBSPOT_API_KEY")


def keyless_linear_token() -> str | None:
    return get_resolver().get("LINEAR_API_KEY")
