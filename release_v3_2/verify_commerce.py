#!/usr/bin/env python3
"""Offline commerce truth gate: link readiness is not revenue or fulfillment.

All observations are unsigned, point-in-time, provider-reported facts copied
from authenticated read-only connector responses. This program does NOT make
remote requests and cannot certify that a checkout converted into a sale.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

EXPECTED_REVIEW_AMOUNT_CENTS = 49700
EXPECTED_INSTALL_AMOUNT_CENTS = 250000
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def valid_stripe_link(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
    except (ValueError, TypeError):
        return False
    return (
        parsed.scheme == "https"
        and parsed.netloc == "buy.stripe.com"
        and not parsed.username and not parsed.password
        and parsed.path.startswith("/") and len(parsed.path) > 1
        and not parsed.query and not parsed.fragment
    )


def evaluate(snapshot: dict) -> dict:
    errors: list[str] = []
    if not isinstance(snapshot, dict):
        return {"valid": False, "errors": ["snapshot must be an object"]}
    if snapshot.get("schema_version") != 1:
        errors.append("unsupported schema version")
    website = snapshot.get("website")
    stripe = snapshot.get("stripe")
    fulfillment = snapshot.get("fulfillment")
    if not all(isinstance(x, dict) for x in (website, stripe, fulfillment)):
        return {"valid": False, "errors": errors + ["website, stripe, fulfillment must be objects"]}

    if website.get("source_repository") != "Garrettc123/garcar-enterprise-os-ui":
        errors.append("website source repository is not the observed canonical repo")
    if not isinstance(website.get("source_commit"), str) or not SHA_RE.fullmatch(website["source_commit"]):
        errors.append("website source commit must be a pinned 40-character SHA")
    if website.get("source_path") != "checkout-validation.mjs":
        errors.append("canonical checkout source file is unknown")
    site_url = website.get("checkout_base_url")
    if not valid_stripe_link(site_url):
        errors.append("invalid canonical website checkout URL")
    if website.get("deployed_source_commit_proven") is not False:
        errors.append("cannot assert deployed source commit in unsigned snapshot")
    if website.get("current_live_http_probe_verified") is not False:
        errors.append("cannot assert direct live HTTP verification in unsigned snapshot")

    if stripe.get("livemode") is not True:
        errors.append("a test-mode Stripe account cannot establish a live purchase path")

    for name, expected in [("primary", EXPECTED_REVIEW_AMOUNT_CENTS), ("secondary", EXPECTED_INSTALL_AMOUNT_CENTS)]:
        item = stripe.get(name)
        if not isinstance(item, dict):
            errors.append(f"{name} link missing")
            continue
        if item.get("livemode") is not True or item.get("active") is not True:
            errors.append(f"{name} checkout is not active and live")
        if item.get("currency") != "usd" or type(item.get("unit_amount")) is not int or item.get("unit_amount") != expected:
            errors.append(f"{name} price/currency mismatch")
        if item.get("quantity") != 1:
            errors.append(f"{name} quantity mismatch")
        if not isinstance(item.get("payment_link_id"), str) or not item["payment_link_id"].startswith("plink_"):
            errors.append(f"{name} Stripe payment link ID missing")
    primary = stripe.get("primary")
    if isinstance(primary, dict) and (primary.get("url") != site_url or not valid_stripe_link(primary.get("url"))):
        errors.append("Stripe primary link mismatches website's canonical checkout")

    charges = stripe.get("charges")
    complete = False
    if not isinstance(charges, dict):
        errors.append("live charge list missing")
    else:
        counts = [charges.get("observed_count"), charges.get("failed_count"), charges.get("successful_paid_count")]
        if any(type(x) is not int or x < 0 for x in counts):
            errors.append("charge counts must be nonnegative integers")
        elif charges["failed_count"] + charges["successful_paid_count"] > charges["observed_count"]:
            errors.append("charge categories cannot exceed returned rows")
        if charges.get("source_operation") != "GET /v1/charges":
            errors.append("charge evidence source not specified")
        complete = charges.get("has_more") is False
        if charges.get("has_more") not in (True, False):
            errors.append("has_more must be a boolean")
    if not all(fulfillment.get(x) is False for x in (
        "authenticated_order_to_fulfillment_trace_verified",
        "actual_customer_deliverable_receipt_verified",
        "payment_to_ledger_reconciliation_verified",
    )):
        errors.append("unsigned observations cannot self-certify fulfillment")
    purchase_path_configured = not errors
    return {
        "valid": not errors,
        "snapshot_not_provider_attestation": True,
        "purchase_link_configuration_valid": purchase_path_configured,
        "checkout_to_live_site_verified": False,
        "complete_charge_list_observed": complete and not errors,
        "observed_paid_charge_count": charges.get("successful_paid_count") if isinstance(charges, dict) and not errors else None,
        "revenue_collected_verified": False,
        "fulfilled_sale_verified": False,
        "release_ready": False,
        "next_gate": "Independently confirm live HTTP checkout routing, real paid Stripe event, authenticated fulfillment receipt, and ledger reconciliation at pinned revisions.",
        "errors": errors,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--release-gate", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = evaluate(json.loads(args.observations.read_text(encoding="utf-8")))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}))
        return 2
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    if not report["valid"]:
        return 2
    return 3 if args.release_gate else 0


if __name__ == "__main__":
    raise SystemExit(main())
