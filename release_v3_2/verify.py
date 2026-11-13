#!/usr/bin/env python3
"""Fail-closed, offline structure gate for the Garcar v3.2 release inventory.

This script validates claims and produces a deterministic evidence-coverage report.
It NEVER certifies runtime health, Stripe revenue, or production deployment based
on text in a repository. Those checks require independent authenticated sources.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

EXPECTED_COUNT = 23
DOMAINS = {"governance", "data", "agents", "commercial", "unresolved"}
REPOSITORY = re.compile(r"^Garrettc123/[A-Za-z0-9_.-]+$")
SHA = re.compile(r"^[0-9a-f]{40}$")
SAFE_PATH = re.compile(r"^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$")
MAPPING_EVIDENCE_LEVEL = "source_code_candidate_not_component_certification"
EVIDENCE_KEYS = (
    "repository_url",
    "source_commit",
    "ci_run_url",
    "ci_conclusion",
    "production_deployment_id",
    "production_environment",
    "health_probe",
    "customer_transaction",
)
MANIFEST = Path(__file__).with_name("manifest.json")


def evaluate(manifest: dict) -> dict:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return {"valid": False, "errors": ["manifest must be an object"]}
    if manifest.get("release") != "v3.2":
        errors.append("release must be v3.2")
    if manifest.get("required_system_count") != EXPECTED_COUNT:
        errors.append("required_system_count must equal 23")
    if manifest.get("production_verified") is not False:
        errors.append("production_verified cannot be self-declared")
    if manifest.get("verification_policy") != "fail_closed_remote_evidence_required":
        errors.append("verification policy must remain fail-closed")
    systems = manifest.get("systems")
    if not isinstance(systems, list):
        return {"valid": False, "errors": errors + ["systems must be an array"]}
    if len(systems) != EXPECTED_COUNT:
        errors.append(f"exactly {EXPECTED_COUNT} systems required; found {len(systems)}")
    seen_ids: set[str] = set()
    mapped: list[str] = []
    unmapped: list[str] = []
    submitted_evidence: list[str] = []

    for i, item in enumerate(systems, start=1):
        if not isinstance(item, dict):
            errors.append(f"systems[{i}] must be an object")
            continue
        sys_id = item.get("id")
        expected_id = f"GCE-{i:03d}"
        if sys_id != expected_id:
            errors.append(f"systems[{i}] id must be {expected_id}")
        if isinstance(sys_id, str):
            if sys_id in seen_ids:
                errors.append(f"duplicate id: {sys_id}")
            seen_ids.add(sys_id)
        else:
            errors.append(f"{expected_id}: id must be a string")
        if not isinstance(item.get("name"), str) or not item["name"].strip():
            errors.append(f"{expected_id}: name missing")
        if item.get("domain") not in DOMAINS:
            errors.append(f"{expected_id}: invalid domain")
        if item.get("production_status") != "not_independently_verified":
            errors.append(f"{expected_id}: production status cannot be promoted by editing JSON")
        repo = item.get("candidate_repository")
        if repo is None:
            unmapped.append(expected_id)
            if item.get("mapping_status") != "unmapped":
                errors.append(f"{expected_id}: missing repository must be unmapped")
        elif (isinstance(repo, str) and REPOSITORY.fullmatch(repo)
              and repo.split("/", 1)[1] not in (".", "..")):
            mapped.append(expected_id)
            if item.get("mapping_status") != "repository_located":
                errors.append(f"{expected_id}: candidate mapping must be repository_located")
        else:
            errors.append(f"{expected_id}: invalid repository; only Garrettc123 is permitted")
        evidence = item.get("evidence")
        if not isinstance(evidence, dict) or any(k not in evidence for k in EVIDENCE_KEYS):
            errors.append(f"{expected_id}: missing evidence schema")
            continue
        expected_url = f"https://github.com/{repo}" if repo else None
        if evidence.get("repository_url") != expected_url:
            errors.append(f"{expected_id}: repository_url inconsistent with mapping")
        mapping_evidence = item.get("mapping_evidence")
        if mapping_evidence is not None:
            if repo is None or not isinstance(mapping_evidence, dict):
                errors.append(f"{expected_id}: mapping_evidence requires a mapped repository and object")
            else:
                paths = mapping_evidence.get("paths")
                note = mapping_evidence.get("note")
                if mapping_evidence.get("level") != MAPPING_EVIDENCE_LEVEL:
                    errors.append(f"{expected_id}: source mapping cannot declare production authority")
                if not isinstance(paths, list) or not paths or not all(
                    isinstance(path, str) and SAFE_PATH.fullmatch(path) and
                    all(part not in (".", "..") for part in path.split("/"))
                    for path in paths
                ):
                    errors.append(f"{expected_id}: mapping_evidence.paths must be safe repository-relative paths")
                if not isinstance(note, str) or not note.strip():
                    errors.append(f"{expected_id}: mapping_evidence note missing")
        commit = evidence.get("source_commit")
        if commit is not None and (not isinstance(commit, str) or not SHA.fullmatch(commit)):
            errors.append(f"{expected_id}: source_commit must be a 40-character lowercase SHA")
        if any(evidence.get(k) is not None for k in EVIDENCE_KEYS if k != "repository_url"):
            submitted_evidence.append(expected_id)

    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return {
        "valid": not errors,
        "release": "v3.2",
        "manifest_sha256": hashlib.sha256(canonical).hexdigest(),
        "claims": len(systems),
        "repository_candidates_located": len(mapped),
        "repository_unmapped": len(unmapped),
        "unmapped_ids": unmapped,
        "systems_with_unverified_submitted_evidence": submitted_evidence,
        "independently_production_certified": 0,
        "release_ready": False,
        "next_gate": "Independent GitHub CI, Railway runtime/health, authorization, and fulfillment evidence must be verified at matching commits before promotion.",
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--report", type=Path, help="Save JSON output for an audit artifact")
    parser.add_argument("--release-gate", action="store_true", help="Fail closed unless every target is independently certified")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}))
        return 2
    report = evaluate(payload)
    result = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(result, encoding="utf-8")
    print(result, end="")
    if not report["valid"]:
        return 2
    if args.release_gate and not report["release_ready"]:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
