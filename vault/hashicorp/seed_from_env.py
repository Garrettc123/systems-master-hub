#!/usr/bin/env python3
"""
Seed HashiCorp Vault from vault/.vault.env

  export VAULT_ADDR=...
  export VAULT_TOKEN=...   # or AppRole
  python vault/hashicorp/seed_from_env.py
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
        print("Run: cp vault/.vault.env.template vault/.vault.env")
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

    print("\n✅ Seed complete. Next: python vault/hashicorp/sync_to_github.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
