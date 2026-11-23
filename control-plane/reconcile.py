#!/usr/bin/env python3
"""Fail-closed structural reconciliation; this does not probe live services."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REGISTRY = Path(os.environ.get("GARCAR_REGISTRY", "control-plane/systems.json"))
SAFE_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


def load_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate(data):
    errors = []
    if not isinstance(data, dict):
        return ["registry root must be an object"]
    for key in ("version", "systems", "invariants"):
        if key not in data:
            errors.append(f"registry missing required top-level key: {key}")
    if set(data) - {"version", "systems", "invariants"}:
        errors.append("registry contains unsupported top-level properties")

    systems = data.get("systems")
    if not isinstance(systems, list):
        errors.append("registry 'systems' must be a list")
        return errors
    if not isinstance(data.get("version"), str):
        errors.append("registry 'version' must be a string")
    if not isinstance(data.get("invariants"), list) or not all(
        isinstance(value, str) for value in data.get("invariants", [])
    ):
        errors.append("registry 'invariants' must be a list of strings")

    seen = set()
    allowed = {
        "repository", "environment", "production", "healthcheck",
        "artifact_digest_source", "deployment_evidence",
        "desired", "observed", "evidence",
    }
    for index, item in enumerate(systems):
        prefix = f"systems[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing = {"repository", "environment", "desired", "observed"} - set(item)
        for key in sorted(missing):
            errors.append(f"{prefix} missing required key: {key}")
        extra = set(item) - allowed
        if extra:
            errors.append(f"{prefix} unsupported properties: {', '.join(sorted(extra))}")

        repo = item.get("repository")
        if not isinstance(repo, str) or not SAFE_ID.fullmatch(repo):
            errors.append(f"{prefix} has invalid repository identifier")
        elif repo in seen:
            errors.append(f"duplicate repository: {repo}")
        else:
            seen.add(repo)

        if item.get("environment") not in {"dev", "staging", "prod"}:
            errors.append(f"{prefix} has invalid environment")
        for key in ("desired", "observed"):
            if not isinstance(item.get(key), dict):
                errors.append(f"{prefix}.{key} must be an object")
        if "production" in item and not isinstance(item["production"], bool):
            errors.append(f"{prefix}.production must be boolean")
        if item.get("production") is True:
            for key in ("healthcheck", "artifact_digest_source", "deployment_evidence"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    errors.append(f"{repo}: production entry missing valid {key}")
        for key in ("healthcheck", "artifact_digest_source", "deployment_evidence"):
            if key in item and (not isinstance(item[key], str) or not item[key].strip()):
                errors.append(f"{prefix}.{key} must be a non-empty string")
        if "evidence" in item and not isinstance(item["evidence"], dict):
            errors.append(f"{prefix}.evidence must be an object")
    return errors


def main() -> int:
    if not REGISTRY.exists():
        print(f"FAIL: registry missing: {REGISTRY}", file=sys.stderr)
        return 2
    try:
        data = load_json(REGISTRY)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read registry: {exc}", file=sys.stderr)
        return 2

    errors = validate(data)
    if errors:
        print("RECONCILIATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"REGISTRY VALIDATION PASS: {len(data['systems'])} entries; structural checks only")
    print("RUNTIME HEALTH: NOT CHECKED — no live endpoint probes were performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
