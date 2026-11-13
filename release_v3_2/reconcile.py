#!/usr/bin/env python3
"""Reconcile v3.2 source claims against read-only provider observations.

The observation file is a point-in-time, unsigned cache, NOT a trusted
attestation, production certificate or proof of customer revenue.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")


def reconcile(manifest: dict, observations: dict) -> dict:
    systems = manifest.get("systems")
    records = observations.get("candidate_deployments")
    if not isinstance(systems, list) or not isinstance(records, list):
        raise ValueError("Expected systems and candidate_deployments arrays")
    if observations.get("provider") != "Railway" or not observations.get("observed_date"):
        raise ValueError("Provider and observation date required")
    if not isinstance(observations.get("scope"), dict):
        raise ValueError("Scope summary required")

    seen = set()
    for d in records:
        if not isinstance(d, dict):
            raise ValueError("Every deployment must be an object")
        required = ("source_repo", "source_commit", "environment", "latest_status")
        if any(k not in d for k in required):
            raise ValueError("Deployment missing required fields")
        if not isinstance(d["source_repo"], str) or not d["source_repo"].startswith("Garrettc123/"):
            raise ValueError("Repository must be a specific Garrettc123 source")
        if d["source_commit"] is not None and not SHA.fullmatch(str(d["source_commit"])):
            raise ValueError("Invalid deployment SHA")
        if d["environment"] not in ("staging", "production"):
            raise ValueError("Unknown environment")
        key = (d["source_repo"].lower(), d["source_commit"], d["environment"])
        if key in seen:
            raise ValueError("Duplicate source/env/commit observation")
        seen.add(key)

    matches = []
    for s in systems:
        repo = s.get("candidate_repository")
        if not repo:
            continue
        pinned_sha = s.get("evidence", {}).get("source_commit")
        sources = [d for d in records if d["source_repo"].lower() == repo.lower()]
        same_sha = [d for d in sources if d["source_commit"] is not None and d["source_commit"] == pinned_sha]
        production_same_sha = [
            d for d in same_sha
            if d["environment"] == "production" and d["latest_status"] == "SUCCESS"
        ]
        matches.append({
            "id": s["id"],
            "candidate_repository": repo,
            "pinned_sha": pinned_sha,
            "repository_observed_on_railway": bool(sources),
            "staging_sources_observed": sum(d["environment"] == "staging" for d in sources),
            "same_commit_deployments": len(same_sha),
            "successful_production_same_commit_deployments": len(production_same_sha),
            "certified": False,
        })
    return {
        "release": manifest.get("release"),
        "observation_date": observations["observed_date"],
        "snapshot_not_attestation": True,
        "provider_scope": observations["scope"],
        "candidate_repositories": len(matches),
        "candidate_repositories_observed_on_railway": sum(m["repository_observed_on_railway"] for m in matches),
        "candidate_repositories_matching_deployed_commit": sum(m["same_commit_deployments"] > 0 for m in matches),
        "candidate_repositories_matching_production_commit": sum(m["successful_production_same_commit_deployments"] > 0 for m in matches),
        "independently_certified": 0,
        "release_ready": False,
        "matches": matches,
        "limitations": [
            "Provider observations were copied from authenticated responses but are not signed or independently re-fetched by this offline script.",
            "A successful deployment, including an exact SHA match, does not prove application health, authorization or financial settlement.",
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=Path(__file__).with_name("manifest.json"))
    p.add_argument("--observations", required=True, type=Path)
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    try:
        result = reconcile(json.loads(args.manifest.read_text()), json.loads(args.observations.read_text()))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 2
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output)
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
