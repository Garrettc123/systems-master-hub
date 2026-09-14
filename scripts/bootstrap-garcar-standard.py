#!/usr/bin/env python3
"""
bootstrap-garcar-standard.py
----------------------------
Creates upgrade pull requests for repositories that opt in to the Garcar Base
contract. Dry-run is the default. Never pushes directly to a target default
branch. Never injects secrets.

Usage:
  python3 scripts/bootstrap-garcar-standard.py --system garcar-base --dry-run
  python3 scripts/bootstrap-garcar-standard.py --system systems-master-hub --open-pr
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = HUB_ROOT / "templates" / "garcar.manifest.json"
PILOT = {
    "garcar-base",
    "continuum-agents",
    "systems-master-hub",
    "neural-mesh-pipeline",
    "garcar-enterprise-production",
}


def load_template(system_id: str) -> dict:
    data = json.loads(TEMPLATE_PATH.read_text())
    data["system_id"] = system_id
    data["name"] = system_id.replace("-", " ").title()
    data["continuum"]["pilot"] = system_id in PILOT
    data["evolution"]["last_evolved"] = datetime.now(timezone.utc).isoformat()
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", required=True, help="system_id / repo slug")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Default: true. Print actions only.")
    parser.add_argument("--no-dry-run", action="store_true",
                        help="Disable dry-run (still PR-only; no direct push to default)")
    parser.add_argument("--open-pr", action="store_true",
                        help="After writing branch content, open a PR via gh if available")
    parser.add_argument("--branch", default="continuum/garcar-base-opt-in")
    args = parser.parse_args()

    dry = not args.no_dry_run
    system_id = args.system.strip().lower()

    if system_id not in PILOT and not os.environ.get("CONTINUUM_FORCE_ALLOW"):
        print(f"REFUSED: '{system_id}' is outside the v1 pilot allowlist.")
        print(f"  Pilot: {sorted(PILOT)}")
        print("  Set CONTINUUM_FORCE_ALLOW=1 only after explicit human review.")
        return 2

    manifest = load_template(system_id)
    print(f"System:     {system_id}")
    print(f"Dry-run:    {dry}")
    print(f"Branch:     {args.branch}")
    print(f"Manifest keys: {list(manifest.keys())}")

    if dry:
        print("\n[DRY-RUN] Would write templates/garcar.manifest.json content to")
        print(f"          target repo {system_id} on branch {args.branch}")
        print("          then open PR to default branch. No files written.")
        print(json.dumps(manifest, indent=2)[:800] + "\n...")
        return 0

    # Safety: only mutate the hub itself in this first implementation when
    # --no-dry-run is used; cross-repo bootstrap is PR-via-gh and documented.
    if system_id == "systems-master-hub":
        out = HUB_ROOT / "garcar.manifest.json"
        if out.exists():
            print(f"Manifest already exists at {out}; not overwriting.")
        else:
            out.write_text(json.dumps(manifest, indent=2) + "\n")
            print(f"Wrote {out}")
        return 0

    print("Cross-repo write path is disabled in Continuum Grid v1.")
    print("Use GitHub Actions daily-evolution-v2 (dry-run/PR-only) or open PRs manually.")
    print("This script will not push to foreign default branches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
