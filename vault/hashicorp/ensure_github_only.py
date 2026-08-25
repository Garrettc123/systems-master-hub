#!/usr/bin/env python3
"""
Fallback when Vault is not configured: generate internal auto-secrets and
write them to GitHub Actions secrets on systems-master-hub (+ optional peers).

External secrets cannot be invented — only rotated internals.
Uses GHPAT / GH_TOKEN + gh CLI or PyNaCl path via sync helpers.
"""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

MANIFEST = Path(__file__).resolve().parent / "manifest.json"
ORG = os.environ.get("GITHUB_ORG", "Garrettc123")
HUB = os.environ.get("HUB_REPO", "systems-master-hub")

GENERATORS = {
    "random_hex_32": lambda: secrets.token_hex(32),
    "random_hex_48": lambda: secrets.token_hex(48),
    "random_hex_64": lambda: secrets.token_hex(64),
}


def gh_set(repo: str, name: str, value: str, token: str) -> bool:
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    r = subprocess.run(
        ["gh", "secret", "set", name, "--repo", f"{ORG}/{repo}"],
        input=value.encode("utf-8"),
        env=env,
        capture_output=True,
    )
    if r.returncode != 0:
        print(f"  ! {name}@{repo}: {r.stderr.decode()[:160]}")
        return False
    print(f"  ✓ {name} → {repo}")
    return True


def main() -> int:
    print("Garcar GitHub-only internal ensure (no Vault)")
    print("============================================")
    token = (
        os.environ.get("GHPAT")
        or os.environ.get("PAT_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
    )
    if not token:
        print("No GitHub token available")
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    generated: dict[str, str] = {}
    for name, meta in manifest.get("secrets", {}).items():
        if not meta.get("internal") or meta.get("rotate") != "auto":
            continue
        gen = GENERATORS.get(meta.get("generator") or "random_hex_32")
        if not gen:
            continue
        generated[name] = gen()

    if not generated:
        print("Nothing to generate")
        return 0

    ok = 0
    for name, value in generated.items():
        if gh_set(HUB, name, value, token):
            ok += 1

    # fan-out internals to repos that list them
    for repo, names in manifest.get("repos", {}).items():
        if repo == HUB:
            continue
        for name in names:
            if name in generated:
                gh_set(repo, name, generated[name], token)

    print(f"\nGenerated/set {ok} internal secrets on {HUB}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
