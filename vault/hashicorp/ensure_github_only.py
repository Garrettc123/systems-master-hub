#!/usr/bin/env python3
"""
Fallback when Vault is not configured: generate internal auto-secrets and
write them to GitHub Actions secrets.

Requires GHPAT / PAT_TOKEN with secrets:write. Default GITHUB_TOKEN cannot
write Actions secrets (HTTP 403) — that is a GitHub platform limit.

Exit codes:
  0 — success, or soft-skip (no PAT / only 403s) so CI stays green
  1 — unexpected failure after PAT was available
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


def gh_set(repo: str, name: str, value: str, token: str) -> str:
    """Return 'ok' | 'forbidden' | 'missing' | 'error'."""
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    r = subprocess.run(
        ["gh", "secret", "set", name, "--repo", f"{ORG}/{repo}"],
        input=value.encode("utf-8"),
        env=env,
        capture_output=True,
    )
    err = (r.stderr or b"").decode(errors="ignore")
    if r.returncode == 0:
        print(f"  ✓ {name} → {repo}")
        return "ok"
    if "403" in err or "Resource not accessible" in err:
        print(f"  · forbidden {name}@{repo} (need GHPAT with secrets:write)")
        return "forbidden"
    if "404" in err or "Not Found" in err:
        print(f"  · missing repo {repo}")
        return "missing"
    print(f"  ! {name}@{repo}: {err[:160]}")
    return "error"


def main() -> int:
    print("Garcar GitHub-only internal ensure (no Vault)")
    print("============================================")

    has_pat = bool(os.environ.get("GHPAT") or os.environ.get("PAT_TOKEN"))
    token = (
        os.environ.get("GHPAT")
        or os.environ.get("PAT_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
    )
    if not token:
        print("No GitHub token in env — soft-skip")
        return 0

    if not has_pat:
        print(
            "WARN: GHPAT/PAT_TOKEN not set. Default GITHUB_TOKEN cannot write "
            "Actions secrets (GitHub platform). Soft-skip internal fan-out."
        )
        print(
            "One-time: add secret GHPAT (classic or fine-grained: "
            "Actions secrets read/write on target repos), then re-run."
        )
        return 0

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

    ok = forbidden = missing = errors = 0
    for name, value in generated.items():
        status = gh_set(HUB, name, value, token)
        if status == "ok":
            ok += 1
        elif status == "forbidden":
            forbidden += 1
        elif status == "missing":
            missing += 1
        else:
            errors += 1

    for repo, names in manifest.get("repos", {}).items():
        if repo == HUB:
            continue
        for name in names:
            if name not in generated:
                continue
            status = gh_set(repo, name, generated[name], token)
            if status == "ok":
                ok += 1
            elif status == "forbidden":
                forbidden += 1
            elif status == "missing":
                missing += 1
            else:
                errors += 1

    print(f"\nset={ok} forbidden={forbidden} missing_repo={missing} error={errors}")
    if ok == 0 and forbidden > 0 and errors == 0:
        print("Soft-skip: token cannot write secrets. Add GHPAT once.")
        return 0
    if ok == 0 and errors > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
