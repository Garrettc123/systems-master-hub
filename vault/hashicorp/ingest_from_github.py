#!/usr/bin/env python3
"""
Ingest secrets that are already present as environment variables (typically
GitHub Actions secrets injected into the job) into HashiCorp Vault.

This is the "never touch a secret file" path:
  1. Secrets already live in systems-master-hub Actions secrets (or another CI).
  2. This script copies non-empty values into secret/garcar/*.
  3. Existing Vault values are preserved unless FORCE_OVERWRITE=1.

Does not print secret values.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    from client import build_from_env
except ImportError:
    from vault.hashicorp.client import build_from_env  # type: ignore

MANIFEST = Path(__file__).resolve().parent / "manifest.json"
# Never pull these from env into Vault (CI runtime noise)
SKIP_ENV = {
    "PATH",
    "HOME",
    "GITHUB_TOKEN",  # ephemeral runner token — not a long-lived secret
    "CI",
    "RUNNER_TEMP",
    "RUNNER_TOOL_CACHE",
    "VAULT_ADDR",
    "VAULT_TOKEN",
    "VAULT_ROLE_ID",
    "VAULT_SECRET_ID",
}
FORCE = os.environ.get("FORCE_OVERWRITE", "").lower() in ("1", "true", "yes")


def candidate_names(manifest: dict) -> list[str]:
    names = set(manifest.get("secrets", {}).keys())
    names.update(manifest.get("aliases", {}).keys())
    names.update(manifest.get("aliases", {}).values())
    # common PAT alias used in workflows
    names.add("PAT_TOKEN")
    names.add("GHPAT")
    return sorted(n for n in names if n and n not in SKIP_ENV)


def main() -> int:
    print("Garcar ingest: GitHub/CI env → Vault")
    print("====================================")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    vault = build_from_env()
    names = candidate_names(manifest)

    written = skipped_empty = skipped_exists = 0
    for name in names:
        val = os.environ.get(name)
        if val is None or str(val).strip() == "":
            skipped_empty += 1
            continue
        if not FORCE:
            existing = vault.read_value(name)
            if existing:
                skipped_exists += 1
                continue
        vault.write_value(name, str(val), source="github_actions_ingest")
        print(f"  ✓ ingested {name}")
        written += 1

    # Resolve aliases into Vault so both names exist
    aliases = manifest.get("aliases", {})
    for alias, source in aliases.items():
        if vault.read_value(alias):
            continue
        src_val = vault.read_value(source) or os.environ.get(source) or os.environ.get(alias)
        if src_val:
            vault.write_value(alias, str(src_val), source="alias", alias_of=source)
            print(f"  ✓ alias {alias} ← {source}")
            written += 1

    print(
        f"\nIngest complete: written={written} "
        f"already_in_vault={skipped_exists} empty_env={skipped_empty}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
