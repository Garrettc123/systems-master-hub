#!/usr/bin/env python3
"""
Garcar Enterprise — Autonomous Wealth Loop Agent
Apollo verified leads → Stripe Payment Links → revenue.
Triggered by .github/workflows/wealth-agent.yml every 6 hours.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
import stripe

# ── Secrets (must be present as GitHub Actions secrets) ──────────────────────
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")

PRODUCT_NAME = os.environ.get("GARCAR_PRODUCT_NAME", "Garcar AI Services — Autonomous Revenue Sprint")
PRICE_CENTS = int(os.environ.get("GARCAR_PRICE_CENTS", "99900"))  # $999 default
LEAD_LIMIT = int(os.environ.get("LEAD_LIMIT", "25"))


def require_env() -> None:
    missing = [k for k, v in {
        "STRIPE_SECRET_KEY": STRIPE_SECRET_KEY,
        "APOLLO_API_KEY": APOLLO_API_KEY,
    }.items() if not v]
    if missing:
        print(f"BLOCKED: missing required secrets: {', '.join(missing)}")
        sys.exit(1)
    stripe.api_key = STRIPE_SECRET_KEY


def create_checkout_link(lead_email: str, product_name: str, price_cents: int) -> str:
    """Create a one-time Stripe Payment Link for the lead."""
    price = stripe.Price.create(
        unit_amount=price_cents,
        currency="usd",
        product_data={"name": product_name},
    )
    link = stripe.PaymentLink.create(
        line_items=[{"price": price.id, "quantity": 1}],
        metadata={
            "lead_email": lead_email,
            "source": "apollo_auto",
            "agent": "wealth_loop",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return link.url


def fetch_apollo_leads(limit: int = 25) -> List[Dict[str, Any]]:
    """Pull verified contacts from Apollo."""
    headers = {"X-Api-Key": APOLLO_API_KEY, "Content-Type": "application/json"}
    payload = {
        "page": 1,
        "per_page": min(limit, 100),
        "contact_email_status": ["verified"],
        "person_titles": ["CEO", "Founder", "Owner", "CTO", "VP", "Director"],
    }
    try:
        resp = requests.post(
            "https://api.apollo.io/v1/mixed_people/search",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("people", []) or []
    except Exception as e:
        print(f"Apollo fetch error: {e}")
        return []


def log_to_supabase(event: Dict[str, Any]) -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/agent_runs",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json={
                "agent_name": "wealth_loop",
                "run_id": event.get("run_id", datetime.now(timezone.utc).isoformat()),
                "trigger_type": "cron",
                "status": event.get("status", "success"),
                "output_result": event,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
            timeout=10,
        )
    except Exception as e:
        print(f"Supabase log skipped: {e}")


def process_apollo_leads() -> Dict[str, Any]:
    """Core wealth loop: discover → price → link."""
    require_env()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results: Dict[str, Any] = {
        "run_id": run_id,
        "leads_fetched": 0,
        "links_created": 0,
        "errors": [],
        "links": [],
    }

    leads = fetch_apollo_leads(LEAD_LIMIT)
    results["leads_fetched"] = len(leads)
    print(f"Fetched {len(leads)} verified Apollo leads")

    for lead in leads:
        email = (lead.get("email") or "").strip()
        if not email or "@" not in email:
            continue
        try:
            url = create_checkout_link(email, PRODUCT_NAME, PRICE_CENTS)
            results["links_created"] += 1
            results["links"].append({"email": email, "url": url})
            print(f"Checkout link ready → {email}: {url}")
            # Outreach is intentionally left to the existing email/SMS agent layer
            # so this core loop never blocks on delivery credentials.
        except Exception as e:
            err = {"email": email, "error": str(e)}
            results["errors"].append(err)
            print(f"Link creation failed for {email}: {e}")

    results["status"] = "success" if not results["errors"] else "partial"
    log_to_supabase(results)
    print(f"Wealth loop complete — {results['links_created']} payment links generated")
    return results


if __name__ == "__main__":
    process_apollo_leads()
