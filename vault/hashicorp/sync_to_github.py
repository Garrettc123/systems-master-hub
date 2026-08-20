#!/usr/bin/env python3
"""
Garcar AutoKey — HashiCorp Vault → GitHub Secrets Synchronizer
Reads secret/garcar/* and pushes every present key to commercial repos.
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Dict

# Support both package and direct execution
try:
    from client import GarcarVault, build_from_env
except ImportError:
    from vault.hashicorp.client import GarcarVault, build_from_env  # type: ignore

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
        print(f"  ✗ {name} → {repo}: {(e.stderr or str(e)).strip()}")
        return False


def propagate(secrets: Dict[str, str], gh_token: str) -> None:
    print("\nPropagating to GitHub repos…")
    for repo in TARGET_REPOS:
        print(f"\n━━ {repo} ━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for name, value in secrets.items():
            if set_github_secret(repo, name, value, gh_token):
                print(f"  ✓ {name}")


def main() -> int:
    print("Garcar Vault → GitHub Sync")
    print("==========================")

    vault = build_from_env()
    secrets = load_from_vault(vault)

    if not secrets:
        print("No secrets found in Vault under secret/garcar/*")
        return 1

    gh_token = (
        secrets.get("GHPAT")
        or os.environ.get("GHPAT")
        or os.environ.get("GH_TOKEN")
    )
    if not gh_token:
        print("GHPAT required in Vault (or env) to write GitHub secrets")
        return 1

    propagate(secrets, gh_token)
    print("\n✅ Sync complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
