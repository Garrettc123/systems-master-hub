#!/usr/bin/env python3
"""
Rotate Vault-managed internal secrets (no human touch).

External secrets (Stripe, Apollo, etc.) stay manual — only generator:auto keys rotate.
After rotation, run sync_to_github.py to push new values to GitHub.
"""
from __future__ import annotations

import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from client import build_from_env
except ImportError:
    from vault.hashicorp.client import build_from_env  # type: ignore

MANIFEST = Path(__file__).resolve().parent / "manifest.json"

GENERATORS = {
    "random_hex_32": lambda: secrets.token_hex(32),
    "random_hex_48": lambda: secrets.token_hex(48),
    "random_hex_64": lambda: secrets.token_hex(64),
    "github_pat_placeholder": lambda: None,  # never auto-generate real PATs
}


def main() -> int:
    print("Garcar internal secret rotation")
    print("==============================")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    vault = build_from_env()
    now = datetime.now(timezone.utc).isoformat()
    rotated = 0

    for name, meta in manifest.get("secrets", {}).items():
        if not meta.get("internal") or meta.get("rotate") != "auto":
            continue
        gen_name = meta.get("generator") or "random_hex_32"
        gen = GENERATORS.get(gen_name)
        if not gen:
            print(f"  · skip {name} (unknown generator {gen_name})")
            continue
        value = gen()
        if value is None:
            print(f"  · skip {name} (generator refused)")
            continue
        vault.write_value(name, value, rotated_at=now, generator=gen_name)
        print(f"  ✓ rotated {name}")
        rotated += 1

    vault.write_value(
        "AUTOKEY_LAST_ROTATION",
        now,
        count=str(rotated),
    )
    print(f"\nRotated {rotated} internal secrets at {now}")
    print("Run sync_to_github.py to distribute.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
