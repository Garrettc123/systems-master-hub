#!/usr/bin/env python3
"""
Garcar Enterprise — Autonomous Wealth Loop Agent
Apollo verified leads → Stripe Payment Links → revenue.
Triggered by .github/workflows/wealth-agent.yml every 6 hours.

Error contract:
  - Missing critical secrets → exit 1 (BLOCKED)
  - Apollo total failure → exit 2 (no leads, no side effects)
  - Partial Stripe failures → exit 0 with status=partial (links that succeeded are valid)
  - Unexpected crash → exit 3 after logging to Supabase if possible
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
import stripe

# ── Secrets (must be present as GitHub Actions secrets) ──────────────────────
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")

PRODUCT_NAME = os.environ.get(
    "GARCAR_PRODUCT_NAME",
    "Garcar AI Services — Autonomous Revenue Sprint",
)
try:
    PRICE_CENTS = int(os.environ.get("GARCAR_PRICE_CENTS", "99900"))
except ValueError:
    print("WARN: invalid GARCAR_PRICE_CENTS — falling back to 99900")
    PRICE_CENTS = 99900

try:
    LEAD_LIMIT = int(os.environ.get("LEAD_LIMIT", "25"))
except ValueError:
    print("WARN: invalid LEAD_LIMIT — falling back to 25")
    LEAD_LIMIT = 25

# Retry policy for transient network / rate-limit failures
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = (1.0, 2.0, 4.0)


class WealthLoopError(Exception):
    """Base for expected, handled failures inside the loop."""


class ConfigError(WealthLoopError):
    """Missing or invalid configuration — do not retry."""


class UpstreamError(WealthLoopError):
    """Apollo / Stripe upstream failure after retries."""


def require_env() -> None:
    missing = [
        k
        for k, v in {
            "STRIPE_SECRET_KEY": STRIPE_SECRET_KEY,
            "APOLLO_API_KEY": APOLLO_API_KEY,
        }.items()
        if not v
    ]
    if missing:
        raise ConfigError(f"missing required secrets: {', '.join(missing)}")
    stripe.api_key = STRIPE_SECRET_KEY


def _is_retryable(exc: BaseException) -> bool:
    """Transient network / rate-limit / 5xx only."""
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return exc.response.status_code in (429, 500, 502, 503, 504)
    if isinstance(exc, stripe.error.RateLimitError):
        return True
    if isinstance(exc, stripe.error.APIConnectionError):
        return True
    if isinstance(exc, stripe.error.APIError):
        # Stripe APIError is often transient
        return True
    return False


def _with_retries(label: str, fn, *args, **kwargs):
    """Execute fn with bounded retries on transient failures."""
    last_exc: Optional[BaseException] = None
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if not _is_retryable(e) or attempt == MAX_RETRIES - 1:
                raise
            delay = RETRY_BACKOFF_SECONDS[min(attempt, len(RETRY_BACKOFF_SECONDS) - 1)]
            print(
                f"RETRY {label} attempt={attempt + 1}/{MAX_RETRIES} "
                f"error={type(e).__name__}: {e} — sleeping {delay}s"
            )
            time.sleep(delay)
    raise UpstreamError(f"{label} failed after {MAX_RETRIES} attempts: {last_exc}")


def create_checkout_link(lead_email: str, product_name: str, price_cents: int) -> str:
    """Create a one-time Stripe Payment Link for the lead. Raises on permanent failure."""
    if not lead_email or "@" not in lead_email:
        raise ValueError(f"invalid email: {lead_email!r}")
    if price_cents <= 0:
        raise ValueError(f"invalid price_cents: {price_cents}")

    def _create() -> str:
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
        if not getattr(link, "url", None):
            raise UpstreamError("Stripe PaymentLink returned no url")
        return link.url

    return _with_retries(f"stripe.create_link[{lead_email}]", _create)


def fetch_apollo_leads(limit: int = 25) -> List[Dict[str, Any]]:
    """Pull verified contacts from Apollo. Raises UpstreamError on total failure."""
    headers = {
        "X-Api-Key": APOLLO_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "page": 1,
        "per_page": min(max(limit, 1), 100),
        "contact_email_status": ["verified"],
        "person_titles": ["CEO", "Founder", "Owner", "CTO", "VP", "Director"],
    }

    def _fetch() -> List[Dict[str, Any]]:
        resp = requests.post(
            "https://api.apollo.io/v1/mixed_people/search",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise UpstreamError(f"Apollo returned non-object: {type(data)}")
        people = data.get("people") or []
        if not isinstance(people, list):
            raise UpstreamError("Apollo 'people' field is not a list")
        return people

    return _with_retries("apollo.fetch", _fetch)


def log_to_supabase(event: Dict[str, Any]) -> bool:
    """Best-effort ledger write. Returns True if persisted. Never raises."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("WARN: Supabase not configured — agent_runs not written")
        return False
    try:
        resp = requests.post(
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
                "error_message": event.get("fatal_error"),
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
            timeout=10,
        )
        if resp.status_code >= 300:
            print(
                f"WARN: Supabase agent_runs write failed "
                f"status={resp.status_code} body={resp.text[:200]}"
            )
            return False
        return True
    except Exception as e:
        print(f"WARN: Supabase log skipped: {type(e).__name__}: {e}")
        return False


def process_apollo_leads() -> Tuple[Dict[str, Any], int]:
    """
    Core wealth loop: discover → price → link.
    Returns (results_dict, exit_code).
    """
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results: Dict[str, Any] = {
        "run_id": run_id,
        "leads_fetched": 0,
        "links_created": 0,
        "links_skipped": 0,
        "errors": [],
        "links": [],
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        require_env()
    except ConfigError as e:
        results["status"] = "blocked"
        results["fatal_error"] = str(e)
        print(f"BLOCKED: {e}")
        log_to_supabase(results)
        return results, 1

    try:
        leads = fetch_apollo_leads(LEAD_LIMIT)
    except Exception as e:
        results["status"] = "upstream_failure"
        results["fatal_error"] = f"Apollo: {type(e).__name__}: {e}"
        print(f"FATAL Apollo: {e}")
        traceback.print_exc()
        log_to_supabase(results)
        return results, 2

    results["leads_fetched"] = len(leads)
    print(f"Fetched {len(leads)} verified Apollo leads")

    if not leads:
        results["status"] = "empty"
        results["fatal_error"] = "Apollo returned zero verified leads"
        print("WARN: zero leads — nothing to price")
        log_to_supabase(results)
        return results, 0  # not a hard failure; just nothing to do

    for lead in leads:
        email = (lead.get("email") or "").strip().lower()
        if not email or "@" not in email:
            results["links_skipped"] += 1
            results["errors"].append(
                {"email": email or None, "error": "invalid_or_missing_email", "fatal": False}
            )
            continue

        try:
            url = create_checkout_link(email, PRODUCT_NAME, PRICE_CENTS)
            results["links_created"] += 1
            results["links"].append({"email": email, "url": url})
            print(f"Checkout link ready → {email}: {url}")
        except stripe.error.CardError as e:
            # Should not happen on PaymentLink create, but be explicit
            err = {"email": email, "error": f"CardError: {e}", "fatal": False}
            results["errors"].append(err)
            print(f"Link creation failed for {email}: CardError: {e}")
        except stripe.error.InvalidRequestError as e:
            err = {"email": email, "error": f"InvalidRequest: {e}", "fatal": False}
            results["errors"].append(err)
            print(f"Link creation failed for {email}: InvalidRequest: {e}")
        except stripe.error.AuthenticationError as e:
            # Bad key — stop the whole run; further calls will fail the same way
            results["status"] = "auth_failure"
            results["fatal_error"] = f"Stripe auth: {e}"
            results["errors"].append({"email": email, "error": str(e), "fatal": True})
            print(f"FATAL Stripe auth: {e}")
            log_to_supabase(results)
            return results, 1
        except Exception as e:
            err = {
                "email": email,
                "error": f"{type(e).__name__}: {e}",
                "fatal": False,
            }
            results["errors"].append(err)
            print(f"Link creation failed for {email}: {type(e).__name__}: {e}")

    if results["links_created"] == 0 and results["errors"]:
        results["status"] = "failed"
        exit_code = 2
    elif results["errors"]:
        results["status"] = "partial"
        exit_code = 0
    else:
        results["status"] = "success"
        exit_code = 0

    results["finished_at"] = datetime.now(timezone.utc).isoformat()
    log_to_supabase(results)
    print(
        f"Wealth loop complete — status={results['status']} "
        f"links={results['links_created']} errors={len(results['errors'])}"
    )
    return results, exit_code


def main() -> int:
    try:
        results, code = process_apollo_leads()
        return code
    except Exception as e:
        # Absolute last-resort guard so the process never dies silently
        fatal = {
            "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "status": "crash",
            "fatal_error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
        }
        print(f"CRASH: {fatal['fatal_error']}")
        traceback.print_exc()
        log_to_supabase(fatal)
        return 3


if __name__ == "__main__":
    sys.exit(main())
