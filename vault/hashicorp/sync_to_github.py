#!/usr/bin/env python3
"""
Garcar AutoKey — HashiCorp Vault → GitHub Secrets Synchronizer

Reads every key under secret/garcar/* from Vault and pushes them
into systems-master-hub + commercial repos via `gh secret set`.

This is the only sanctioned path that can *read* secrets and distribute them.
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Dict, List

from client import GarcarVault, build_from_env

# Canonical secret names (must match vault/.vault.env.template + Autokey)
CANONICAL_KEYS = [
    "GHPAT",
    "RAILWAY_TOKEN",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_PUBLISHABLE_KEY",
    "STRIPE_PRICE_STARTER",
    "STRIPE_PRICE_PRO",
    "STRIPE_PRICE_AGENCY",
    "APOLLO_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "PERPLEXITY_API_KEY",
    "HUBSPOT_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_KEY",
    "LINEAR_API_KEY",
    "SLACK_WEBHOOK_URL",
    "DATABASE_URL",
    "REDIS_URL",
    "VERCEL_TOKEN",
    "NEXT_PUBLIC_APP_URL",
    "APP_URL",
    "APP_BASE_URL_PAYMENTS",
    "APP_BASE_URL_RHNS",
    "APP_BASE_URL_ATLAS",
    "APP_BASE_URL_ZEUS",
]

TARGET_REPOS = [
    "systems-master-hub",
    "garcar-payments",
    "garcar-rhns-core",
    "atlas-dashboard",
    "zeus-dashboard",
    "garcar-payment-loop",
    "mars-api",
    "enterprise-mlops-platform",
    "neural-mesh",
]

ORG = "Garrettc123"


def load_from_vault(vault: GarcarVault) -> Dict[str, str]:
    """Pull every canonical key that exists in Vault."""
    secrets: Dict[str, str] = {}
    for key in CANONICAL_KEYS:
        val = vault.read_value(key)
        if val:
            secrets[key] = val
            print(f"  ✓ loaded {key}")
        else:
            print(f"  ○ missing {key}")
    return secrets


def set_github_secret(repo: str, name: str, value: str, gh_token: str) -> bool:
    env = os.environ.copy()
    env["GH_TOKEN"] = gh_token
    try:
        subprocess.run(
            ["gh", "secret", "set", name, "--body", value, "--repo", f"{ORG}/{repo}"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ {name} → {repo}: {e.stderr.strip()}")
        return False


def propagate(secrets: Dict[str, str], gh_token: str) -> None:
    print("\nPropagating to GitHub repos…")
    for repo in TARGET_REPOS:
        print(f"\n━━ {repo} ━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for name, value in secrets.items():
            ok = set_github_secret(repo, name, value, gh_token)
            if ok:
                print(f"  ✓ {name}")


def main() -> int:
    print("Garcar Vault → GitHub Sync")
    print("==========================")

    vault = build_from_env()
    secrets = load_from_vault(vault)

    if not secrets:
        print("No secrets found in Vault under secret/garcar/*")
        return 1

    gh_token = secrets.get("GHPAT") or os.environ.get("GHPAT") or os.environ.get("GH_TOKEN")
    if not gh_token:
        print("GHPAT required in Vault (or env) to write GitHub secrets")
        return 1

    propagate(secrets, gh_token)
    print("\n✅ Sync complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
