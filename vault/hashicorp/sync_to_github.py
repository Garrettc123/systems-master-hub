#!/usr/bin/env python3
"""
Garcar Vault → GitHub Secrets propagator (zero-touch distribution plane)

Reads every secret under secret/garcar/* and writes only the mapped keys
to each target repository defined in manifest.json.

Env:
  VAULT_ADDR + (VAULT_TOKEN | VAULT_ROLE_ID+VAULT_SECRET_ID)
  GHPAT or GH_TOKEN — GitHub token with secrets:write on target repos
  DRY_RUN=1 — log only, do not write
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import requests

try:
    from client import GarcarVault, build_from_env
except ImportError:
    from vault.hashicorp.client import GarcarVault, build_from_env  # type: ignore

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "manifest.json"
ORG = os.environ.get("GITHUB_ORG", "Garrettc123")
DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")


def load_manifest() -> dict:
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def resolve_aliases(secrets: Dict[str, str], aliases: Dict[str, str]) -> Dict[str, str]:
    out = dict(secrets)
    for alias, source in aliases.items():
        if alias not in out and source in out:
            out[alias] = out[source]
    return out


def set_github_secret(repo: str, name: str, value: str, token: str) -> bool:
    if DRY_RUN:
        print(f"  [dry-run] would set {name} → {ORG}/{repo}")
        return True
    url = f"https://api.github.com/repos/{ORG}/{repo}/actions/secrets/public-key"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "garcar-vault-sync",
    }
    try:
        pk = requests.get(url, headers=headers, timeout=30)
        if pk.status_code != 200:
            print(f"  ! public-key {repo}: HTTP {pk.status_code} {pk.text[:120]}")
            return False
        data = pk.json()
        key_id = data["key_id"]
        public_key = data["key"]

        # libsodium sealed box via PyNaCl when available; else use gh CLI fallback
        try:
            from base64 import b64encode
            from nacl import encoding, public

            pk_bytes = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
            sealed = public.SealedBox(pk_bytes).encrypt(value.encode("utf-8"))
            encrypted = b64encode(sealed).decode("utf-8")
        except ImportError:
            # Fallback: shell out to gh
            import subprocess

            env = os.environ.copy()
            env["GH_TOKEN"] = token
            r = subprocess.run(
                ["gh", "secret", "set", name, "--repo", f"{ORG}/{repo}"],
                input=value.encode("utf-8"),
                env=env,
                capture_output=True,
            )
            if r.returncode != 0:
                print(f"  ! gh secret set {name}: {r.stderr.decode()[:200]}")
                return False
            return True

        put = requests.put(
            f"https://api.github.com/repos/{ORG}/{repo}/actions/secrets/{name}",
            headers=headers,
            json={"encrypted_value": encrypted, "key_id": key_id},
            timeout=30,
        )
        if put.status_code not in (201, 204):
            print(f"  ! set {name}@{repo}: HTTP {put.status_code} {put.text[:120]}")
            return False
        return True
    except Exception as e:
        print(f"  ! {name}@{repo}: {e}")
        return False


def propagate(
    secrets: Dict[str, str],
    repos: Dict[str, List[str]],
    token: str,
) -> Tuple[int, int, int]:
    ok = skip = err = 0
    for repo, names in repos.items():
        print(f"\n━━ {ORG}/{repo} ━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for name in names:
            value = secrets.get(name)
            if not value:
                print(f"  · skip {name} (empty in Vault)")
                skip += 1
                continue
            if set_github_secret(repo, name, value, token):
                print(f"  ✓ {name}")
                ok += 1
            else:
                err += 1
    return ok, skip, err


def main() -> int:
    print("Garcar Vault → GitHub Sync (zero-touch)")
    print("=======================================")
    if DRY_RUN:
        print("DRY_RUN=1 — no writes")

    manifest = load_manifest()
    vault = build_from_env()
    print("Vault auth OK | keys:", vault.list_keys())

    secrets = vault.read_all()
    secrets = resolve_aliases(secrets, manifest.get("aliases", {}))
    # PAT_TOKEN alias for workflows that expect it
    if "GHPAT" in secrets and "PAT_TOKEN" not in secrets:
        secrets["PAT_TOKEN"] = secrets["GHPAT"]

    if not secrets:
        print("No secrets found under secret/garcar/* — seed Vault first")
        return 1

    gh_token = (
        secrets.get("GHPAT")
        or secrets.get("PAT_TOKEN")
        or os.environ.get("GHPAT")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
    )
    if not gh_token:
        print("GHPAT required in Vault (or env) to write GitHub secrets")
        return 1

    repos = manifest.get("repos", {})
    ok, skip, err = propagate(secrets, repos, gh_token)
    print(f"\nDone. set={ok} skip={skip} err={err}")
    # soft-success if at least some secrets landed; hard-fail only if total failure
    if ok == 0 and err > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
