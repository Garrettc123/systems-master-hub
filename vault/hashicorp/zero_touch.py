#!/usr/bin/env python3
"""
Garcar zero-touch secret plane orchestrator.

Modes:
  ensure   — rotate missing internal keys only, then sync
  ingest   — copy CI env secrets into Vault (no overwrite), rotate internals, sync
  sync     — Vault → GitHub only
  rotate   — rotate all auto internals, then sync
  dry_run  — sync with DRY_RUN=1

Environment: same as client/sync (VAULT_* + GHPAT/GH_TOKEN).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(script: str, extra_env: dict | None = None) -> int:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    print(f"\n>>> {script}")
    r = subprocess.run([sys.executable, str(HERE / script)], env=env)
    return r.returncode


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ZERO_TOUCH_MODE", "ensure")).lower()
    print(f"Garcar zero-touch mode={mode}")

    if mode in ("ingest", "ensure", "full"):
        # ingest is best-effort when CI injects secrets as env
        if mode in ("ingest", "full"):
            rc = run("ingest_from_github.py")
            if rc != 0:
                print("ingest failed", rc)
                return rc
        # always ensure internal keys exist / rotate on full
        if mode == "full":
            rc = run("rotate_internal.py")
        else:
            # ensure: only create missing internals (FORCE not set; rotate writes all autos)
            rc = run("rotate_internal.py")
        if rc != 0:
            return rc
        return run("sync_to_github.py")

    if mode == "rotate":
        rc = run("rotate_internal.py")
        if rc != 0:
            return rc
        return run("sync_to_github.py")

    if mode == "sync":
        return run("sync_to_github.py")

    if mode == "dry_run":
        return run("sync_to_github.py", {"DRY_RUN": "1"})

    print(f"Unknown mode: {mode}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
