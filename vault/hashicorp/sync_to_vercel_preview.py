#!/usr/bin/env python3
"""Sync read-only knowledge-provider credentials from Vault to Vercel Preview.

- Vault remains the source of truth.
- Only the dedicated command-center branch receives the variables.
- No value is logged.
- Existing Vercel variables are updated only when a corresponding non-empty
  canonical Vault value exists; absent Vault keys are never used to delete or
  overwrite values.
"""
from __future__ import annotations

import os
import sys
from typing import Any

import requests

try:
    from client import build_from_env
except ImportError:
    from vault.hashicorp.client import build_from_env  # type: ignore

PROJECT_ID = "prj_WBSk2CBk3blDZSFTDAi7bdSICsiG"
TEAM_ID = "team_OwKybag22DYY0loNpSyvndJ4"
GIT_BRANCH = "feat/garcar-phone-command-center"
VERCEL_API = "https://api.vercel.com"
# Vercel environment key -> canonical Vault key.
KEY_MAP = {
    "GITHUB_TOKEN": "GITHUB_READ_TOKEN",
    "SLACK_USER_TOKEN": "SLACK_USER_TOKEN",
    "NOTION_API_KEY": "NOTION_API_KEY",
    "PERPLEXITY_API_KEY": "PERPLEXITY_API_KEY",
}


def main() -> int:
    dry_run = os.getenv("GARCAR_VERCEL_DRY_RUN", "").lower() in {"1", "true", "yes"}
    vault = build_from_env()
    available: dict[str, str] = {}
    missing: list[str] = []

    for vercel_key, vault_key in KEY_MAP.items():
        value = vault.read_value(vault_key)
        if value and str(value).strip():
            available[vercel_key] = str(value).strip()
        else:
            missing.append(vercel_key)

    print(f"Vault authentication succeeded; provider values found: {len(available)}/{len(KEY_MAP)}")
    if missing:
        print("Missing Vault values (names only): " + ", ".join(missing))

    if dry_run:
        print("DRY RUN: no Vercel environment changes requested.")
        for key in available:
            print(f"WOULD_SYNC {key} -> Preview/{GIT_BRANCH}")
        return 0

    token = vault.read_value("VERCEL_TOKEN")
    if not token:
        print("SKIPPED: VERCEL_TOKEN is not present in Vault; no Vercel writes were made.")
        return 0
    if not available:
        print("SKIPPED: no provider credentials were found; no Vercel writes were made.")
        return 0

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    failures = 0
    for key, value in available.items():
        payload: dict[str, Any] = {
            "key": key,
            "value": value,
            "type": "encrypted",
            "target": ["preview"],
            "gitBranch": GIT_BRANCH,
            "comment": "Synced from canonical Garcar Vault; preview branch only.",
        }
        try:
            response = requests.post(
                f"{VERCEL_API}/v10/projects/{PROJECT_ID}/env",
                params={"teamId": TEAM_ID, "upsert": "true"},
                headers=headers,
                json=payload,
                timeout=30,
            )
        except requests.RequestException as exc:
            # Deliberately omit exception details and request metadata.
            print(f"FAIL {key}: network request failed ({type(exc).__name__})")
            failures += 1
            continue

        if response.status_code not in (200, 201):
            # Never print response bodies: keep provider/credential data out of CI logs.
            print(f"FAIL {key}: Vercel API returned HTTP {response.status_code}")
            failures += 1
        else:
            print(f"SYNCED {key} -> Preview/{GIT_BRANCH}")

    if failures:
        print(f"RESULT: {failures} environment variable sync operation(s) failed; redeployment skipped.")
        return 1

    # Vercel environment changes apply to future deployments only. Redeploy the
    # latest READY deployment for this feature branch, never a production target.
    try:
        listing = requests.get(
            f"{VERCEL_API}/v6/deployments",
            params={"projectId": PROJECT_ID, "teamId": TEAM_ID, "limit": 50},
            headers=headers,
            timeout=30,
        )
    except requests.RequestException as exc:
        print(f"FAIL deployment lookup: network request failed ({type(exc).__name__})")
        return 1
    if listing.status_code != 200:
        print(f"FAIL deployment lookup: Vercel API returned HTTP {listing.status_code}")
        return 1

    data = listing.json()
    deployments = data.get("deployments", [])
    if isinstance(deployments, dict):
        deployments = deployments.get("deployments", [])
    candidates = [
        item for item in deployments
        if (item.get("meta") or {}).get("githubCommitRef") == GIT_BRANCH
        and item.get("state") == "READY"
        and item.get("target") != "production"
    ]
    if not candidates:
        print("SKIPPED redeployment: no READY preview deployment found for the target branch.")
        return 0

    previous = max(candidates, key=lambda item: item.get("created", item.get("createdAt", 0)))
    deployment_id = previous.get("uid") or previous.get("id")
    if not deployment_id:
        print("FAIL redeployment: latest preview deployment has no identifier.")
        return 1
    try:
        redeploy = requests.post(
            f"{VERCEL_API}/v13/deployments",
            params={"teamId": TEAM_ID},
            headers=headers,
            json={"deploymentId": deployment_id},
            timeout=30,
        )
    except requests.RequestException as exc:
        print(f"FAIL redeployment: network request failed ({type(exc).__name__})")
        return 1
    if redeploy.status_code not in (200, 201):
        print(f"FAIL redeployment: Vercel API returned HTTP {redeploy.status_code}")
        return 1

    new_deployment = redeploy.json()
    print(f"REDEPLOYED preview: {new_deployment.get('url') or new_deployment.get('id') or 'accepted'}")
    print(f"RESULT: processed {len(available)} configured provider variable(s); production was not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
