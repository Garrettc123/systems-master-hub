#!/usr/bin/env python3
"""Deterministic, fail-closed reconciliation for the Garcar control plane."""
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


def main() -> int:
    if not REGISTRY.exists():
        print(f"FAIL: registry missing: {REGISTRY}", file=sys.stderr)
        return 2
    data = load_json(REGISTRY)
    systems = data.get("systems")
    if not isinstance(systems, list) or not systems:
        print("FAIL: registry contains no systems", file=sys.stderr)
        return 2

    seen = set()
    errors = []
    for item in systems:
        repo = item.get("repository")
        env = item.get("environment")
        if not isinstance(repo, str) or not SAFE_ID.fullmatch(repo):
            errors.append(f"invalid repository: {repo!r}")
            continue
        if repo in seen:
            errors.append(f"duplicate repository: {repo}")
        seen.add(repo)
        if env not in {"dev", "staging", "prod"}:
            errors.append(f"{repo}: invalid environment {env!r}")
        if item.get("production", False):
            for key in ("healthcheck", "artifact_digest_source", "deployment_evidence"):
                if not item.get(key):
                    errors.append(f"{repo}: production system missing {key}")

    if errors:
        print("RECONCILIATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"RECONCILIATION PASS: {len(systems)} registered systems; no schema-level drift")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
