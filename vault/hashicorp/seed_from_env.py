#!/usr/bin/env python3
"""
One-time (or rotation) seeder: local vault/.vault.env → HashiCorp Vault

Usage:
  export VAULT_ADDR=https://vault.example.com:8200
  export VAULT_TOKEN=hvs....
  python vault/hashicorp/seed_from_env.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from client import build_from_env

VAULT_ENV = Path(__file__).resolve().parents[1] / ".vault.env"


def load_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        print(f"Missing {path}. Copy .vault.env.template and fill values.")
        sys.exit(1)
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if value:
            data[key] = value
    return data


def main() -> int:
    env_secrets = load_env_file(VAULT_ENV)
    print(f"Loaded {len(env_secrets)} non-empty keys from {VAULT_ENV}")

    vault = build_from_env()
    for key, value in env_secrets.items():
        vault.write(key, {"value": value})
        print(f"  ✓ wrote secret/garcar/{key}")

    print("\n✅ Seed complete. Run sync_to_github.py to distribute.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
