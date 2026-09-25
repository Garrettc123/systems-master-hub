#!/usr/bin/env python3
"""
Garcar Enterprise — Living Registry Sync
========================================
Pulls every repository under the authenticated user via GitHub API,
computes a deterministic health score (0-100), and writes:
  - registry/registry.json   (full living registry)
  - SYSTEM_REGISTRY.json     (compatible meta + systems list for upgrade loop)

Run nightly via .github/workflows/registry-daily-sync.yml
or manually: python registry/sync.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import requests

OWNER = os.environ.get("GITHUB_OWNER", "Garrettc123")
TOKEN = os.environ.get("REGISTRY_GITHUB_TOKEN") or os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
API = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = ROOT / "registry"
REGISTRY_JSON = REGISTRY_DIR / "registry.json"
SYSTEM_REGISTRY = ROOT / "SYSTEM_REGISTRY.json"


def gh_get(url: str, params: dict | None = None) -> Any:
    r = requests.get(url, headers=HEADERS, params=params or {}, timeout=60)
    r.raise_for_status()
    return r.json()


def list_all_repos() -> list[dict]:
    """Paginate through every repo the token can see for this owner."""
    repos: list[dict] = []
    page = 1
    while True:
        # Use /user/repos so private repos appear when token has access.
        data = gh_get(
            f"{API}/user/repos",
            params={
                "affiliation": "owner",
                "per_page": 100,
                "page": page,
                "sort": "updated",
                "direction": "desc",
            },
        )
        if not data:
            break
        # Keep only repos owned by the target user (safety).
        for repo in data:
            if repo.get("owner", {}).get("login") == OWNER:
                repos.append(repo)
        if len(data) < 100:
            break
        page += 1
    return repos


def days_since(iso: str | None) -> float:
    if not iso:
        return 9999.0
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
    except Exception:
        return 9999.0


def health_score(repo: dict) -> dict[str, Any]:
    """Deterministic 0-100 health score + component breakdown."""
    score = 0
    breakdown: dict[str, int] = {}

    # Recency — 40 pts
    d = days_since(repo.get("pushed_at") or repo.get("updated_at"))
    if d <= 7:
        rec = 40
    elif d <= 30:
        rec = 20
    elif d <= 90:
        rec = 8
    else:
        rec = 0
    score += rec
    breakdown["recency"] = rec

    # Activity — 20 pts (open issues + size proxy)
    open_issues = repo.get("open_issues_count") or 0
    size = repo.get("size") or 0
    act = 0
    if open_issues > 0:
        act += min(10, open_issues)  # some activity is good
    if size > 50:
        act += 5
    if size > 500:
        act += 5
    score += act
    breakdown["activity"] = act

    # Completeness — 25 pts
    comp = 0
    if repo.get("has_issues"):
        comp += 3
    if not repo.get("archived") and not repo.get("disabled"):
        comp += 5
    if repo.get("license"):
        comp += 5
    if repo.get("description"):
        comp += 4
    if repo.get("homepage"):
        comp += 3
    topics = repo.get("topics") or []
    if topics:
        comp += min(5, len(topics))
    score += comp
    breakdown["completeness"] = comp

    # Engagement — 15 pts
    stars = repo.get("stargazers_count") or 0
    forks = repo.get("forks_count") or 0
    eng = min(10, stars) + min(5, forks)
    score += eng
    breakdown["engagement"] = eng

    score = max(0, min(100, score))
    return {"score": score, "breakdown": breakdown, "days_since_push": round(d, 1)}


def classify_role(name: str, desc: str | None) -> str:
    n = (name or "").lower()
    d = (desc or "").lower()
    if any(k in n or k in d for k in ("payment", "stripe", "billing", "ledger")):
        return "payments"
    if any(k in n or k in d for k in ("dashboard", "zeus", "atlas", "ui")):
        return "ui_control_plane"
    if any(k in n or k in d for k in ("rhns", "reasoning", "cognitive")):
        return "cognitive_architecture"
    if any(k in n or k in d for k in ("nexus", "apex", "titan", "orchestr")):
        return "orchestration"
    if any(k in n or k in d for k in ("revenue", "wealth", "income", "commerce")):
        return "revenue"
    if any(k in n or k in d for k in ("deploy", "infra", "terraform", "ci")):
        return "deployment_infra"
    if any(k in n or k in d for k in ("nwu", "blockchain", "solidity", "contract")):
        return "blockchain_protocol"
    return "system"


def build_registry(repos: list[dict]) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    systems = []
    health_sum = 0
    public_count = 0
    private_count = 0
    languages: set[str] = set()

    for i, r in enumerate(sorted(repos, key=lambda x: x.get("name", "").lower()), start=1):
        h = health_score(r)
        health_sum += h["score"]
        vis = "private" if r.get("private") else "public"
        if vis == "public":
            public_count += 1
        else:
            private_count += 1
        lang = r.get("language")
        if lang:
            languages.add(lang)

        systems.append(
            {
                "id": i,
                "name": r["name"],
                "full_name": r["full_name"],
                "github_url": r["html_url"],
                "role": classify_role(r["name"], r.get("description")),
                "language": lang,
                "visibility": vis,
                "status": "archived" if r.get("archived") else ("disabled" if r.get("disabled") else "active"),
                "description": r.get("description"),
                "homepage": r.get("homepage"),
                "topics": r.get("topics") or [],
                "stars": r.get("stargazers_count") or 0,
                "forks": r.get("forks_count") or 0,
                "open_issues": r.get("open_issues_count") or 0,
                "size_kb": r.get("size") or 0,
                "default_branch": r.get("default_branch"),
                "created_at": r.get("created_at"),
                "pushed_at": r.get("pushed_at"),
                "updated_at": r.get("updated_at"),
                "license": (r.get("license") or {}).get("spdx_id") if r.get("license") else None,
                "health": h,
                "full_stack_components": {
                    "backend_api": None,
                    "frontend_ui": None,
                    "payment_hook": None,
                    "event_bus_connected": False,
                    "observability_connected": False,
                },
                "tags": r.get("topics") or [],
            }
        )

    total = len(systems)
    avg_health = round(health_sum / total, 1) if total else 0

    return {
        "registry_version": "2.0.0",
        "owner": OWNER,
        "organization": "Garcar Enterprise",
        "generated_at": now,
        "generator": "registry/sync.py",
        "meta": {
            "total_systems": total,
            "target_systems": 332,
            "public_repos": public_count,
            "private_repos": private_count,
            "average_health_score": avg_health,
            "languages": sorted(languages),
            "upgrade_directive": "NEVER_REPEAT_ONLY_UPGRADE",
            "convergence_target": "ONE_MASTERY_LEVEL_ARCHITECTURAL_FEAT",
        },
        "architecture": {
            "event_bus": {
                "host_repo": "systems-master-hub",
                "broker": "Upstash Redis (planned)",
                "status": "to_be_wired",
                "topic_schema": "garcar.{system_name}.{event_type}",
            },
            "master_control_plane": {
                "host_repo": "systems-master-hub",
                "role": "canonical living registry + daily upgrade orchestrator",
                "upgrade_cron": "0 2 * * *",
                "registry_sync_cron": "0 1 * * *",
            },
            "unified_ui": {
                "primary": "zeus-dashboard",
                "secondary": "atlas-dashboard",
                "status": "active",
            },
            "payments_layer": {
                "host_repo": "garcar-payments",
                "provider": "Stripe",
                "status": "active",
            },
            "revenue_ledger": {
                "endpoint": "GET /ledger/summary",
                "status": "to_be_standardized",
            },
        },
        "upgrade_loop": {
            "description": "Nightly 02:00 UTC: read living registry, diff activity, open upgrade PRs for lowest-health Tier-1 systems first. Never repeat — only upgrade.",
            "workflow_file": ".github/workflows/nightly-upgrade-loop.yml",
            "registry_workflow": ".github/workflows/registry-daily-sync.yml",
            "rule": "Each cycle must advance at least one capability tier. Rollback is automatic on failure.",
        },
        "systems": systems,
    }


def write_system_registry_compat(reg: dict) -> None:
    """Keep SYSTEM_REGISTRY.json shape expected by existing upgrade scripts."""
    compat = {
        "registry_version": reg["registry_version"],
        "owner": reg["owner"],
        "organization": reg["organization"],
        "registry_created": "2026-08-03T20:50:00Z",
        "last_updated": reg["generated_at"],
        "description": "Canonical living source of truth for all Garcar Enterprise systems. Generated by registry/sync.py. Every system must emit and consume events via the Event Mesh. This file drives the daily autonomous upgrade loop.",
        "meta": reg["meta"],
        "architecture": reg["architecture"],
        "upgrade_loop": reg["upgrade_loop"],
        "systems": [
            {
                "id": s["id"],
                "name": s["name"],
                "github_url": s["github_url"],
                "role": s["role"],
                "language": s["language"],
                "visibility": s["visibility"],
                "status": s["status"],
                "last_updated": (s.get("pushed_at") or "")[:10],
                "health_score": s["health"]["score"],
                "full_stack_components": s["full_stack_components"],
                "tags": s["tags"],
            }
            for s in reg["systems"]
        ],
    }
    SYSTEM_REGISTRY.write_text(json.dumps(compat, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {SYSTEM_REGISTRY} ({len(compat['systems'])} systems)")


def main() -> int:
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting living registry sync for {OWNER}")
    if not TOKEN:
        print("WARNING: No GITHUB_TOKEN / GH_PAT / REGISTRY_GITHUB_TOKEN — only public data may be incomplete", file=sys.stderr)

    try:
        repos = list_all_repos()
    except requests.HTTPError as e:
        print(f"GitHub API error: {e}", file=sys.stderr)
        if e.response is not None:
            print(e.response.text[:500], file=sys.stderr)
        return 1

    print(f"Fetched {len(repos)} repositories")
    reg = build_registry(repos)

    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_JSON.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {REGISTRY_JSON}")
    print(f"  total={reg['meta']['total_systems']}  avg_health={reg['meta']['average_health_score']}  public={reg['meta']['public_repos']}  private={reg['meta']['private_repos']}")

    write_system_registry_compat(reg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
