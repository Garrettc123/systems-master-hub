#!/usr/bin/env python3
"""
Seed HashiCorp Vault from vault/.vault.env (one-time load).

  export VAULT_ADDR=...
  export VAULT_TOKEN=...   # or AppRole
  python vault/hashicorp/seed_from_env.py

After this, never touch GitHub secrets by hand — run sync_to_github.py / workflow.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from client import build_from_env
except ImportError:
    from vault.hashicorp.client import build_from_env  # type: ignore

VAULT_ENV = Path(__file__).resolve().parents[1] / ".vault.env"


def load_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        print(f"Missing {path}")
        print("Run: cp vault/.vault.env.template vault/.vault.env && edit values")
        sys.exit(1)
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and v:
            data[k] = v
    return data


def main() -> int:
    print("Garcar Vault seed_from_env")
    print("==========================")
    env = load_env_file(VAULT_ENV)
    print(f"Loaded {len(env)} non-empty keys from {VAULT_ENV}")

    vault = build_from_env()
    written = 0
    for name, value in sorted(env.items()):
        # skip vault bootstrap vars themselves
        if name.startswith("VAULT_"):
            continue
        vault.write_value(name, value)
        print(f"  ✓ secret/garcar/{name}")
        written += 1

    print(f"\nSeeded {written} secrets under secret/garcar/*")
    print("Next: python vault/hashicorp/sync_to_github.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
