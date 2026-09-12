#!/usr/bin/env python3
"""
Garcar Autonomous Wiring Orchestrator

Runs inside systems-master-hub via GitHub Actions.

- Reads SYSTEM_REGISTRY.json
- Iterates priority_tier_1 systems
- For each: creates a wiring branch + TODO file
- Opens a draft PR labeled `garcar-autonomous-wiring`
"""

import base64
import json
import os
import sys
from typing import Dict, Any, List
from urllib.parse import urlparse

import requests

GITHUB_API = "https://api.github.com"
TOKEN = os.environ.get("GARCAR_ORCHESTRATOR_TOKEN")

if not TOKEN:
    print("[ERROR] GARCAR_ORCHESTRATOR_TOKEN not set; cannot wire autonomously.", file=sys.stderr)
    sys.exit(1)

SESSION = requests.Session()
SESSION.headers.update({
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
})


def load_system_registry() -> Dict[str, Any]:
    with open("SYSTEM_REGISTRY.json", "r", encoding="utf-8") as f:
        return json.load(f)


def extract_repo_name(github_url: str) -> str:
    parsed = urlparse(github_url)
    parts = parsed.path.strip("/").split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    raise ValueError(f"Unexpected GitHub URL format: {github_url}")


def get_repo_default_branch(full_name: str) -> str:
    r = SESSION.get(f"{GITHUB_API}/repos/{full_name}")
    r.raise_for_status()
    data = r.json()
    return data.get("default_branch", "main")


def get_branch_sha(full_name: str, branch: str) -> str:
    r = SESSION.get(f"{GITHUB_API}/repos/{full_name}/git/ref/heads/{branch}")
    r.raise_for_status()
    return r.json()["object"]["sha"]


def create_branch_from_default(full_name: str, new_branch: str) -> str:
    default_branch = get_repo_default_branch(full_name)
    sha = get_branch_sha(full_name, default_branch)

    ref_payload = {"ref": f"refs/heads/{new_branch}", "sha": sha}
    r = SESSION.post(f"{GITHUB_API}/repos/{full_name}/git/refs", json=ref_payload)
    # 201 = created, 422 = already exists
    if r.status_code not in (201, 422):
        r.raise_for_status()
    return new_branch


def create_or_update_file(full_name: str, branch: str, path: str, content: str, message: str) -> None:
    get_url = f"{GITHUB_API}/repos/{full_name}/contents/{path}?ref={branch}"
    r = SESSION.get(get_url)
    sha = None
    if r.status_code == 200:
        sha = r.json()["sha"]

    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    r2 = SESSION.put(f"{GITHUB_API}/repos/{full_name}/contents/{path}", json=payload)
    r2.raise_for_status()
    print(f"[INFO] Wrote {path} in {full_name}@{branch}")


def ensure_label(full_name: str, name: str, color: str = "0E8A16") -> None:
    r = SESSION.post(
        f"{GITHUB_API}/repos/{full_name}/labels",
        json={"name": name, "color": color, "description": "Garcar autonomous wiring draft"},
    )
    if r.status_code not in (201, 422):
        print(f"[WARN] Could not ensure label {name} on {full_name}: {r.status_code}")


def open_draft_pr(full_name: str, head_branch: str, base_branch: str, title: str, body: str, labels: List[str]) -> None:
    payload = {
        "title": title,
        "head": head_branch,
        "base": base_branch,
        "body": body,
        "draft": True,
    }
    r = SESSION.post(f"{GITHUB_API}/repos/{full_name}/pulls", json=payload)
    if r.status_code not in (201, 422):
        r.raise_for_status()

    if r.status_code == 201:
        pr = r.json()
        for label in labels:
            ensure_label(full_name, label)
        issue_url = f"{GITHUB_API}/repos/{full_name}/issues/{pr['number']}"
        SESSION.post(issue_url + "/labels", json={"labels": labels})
        print(f"[INFO] Opened draft PR #{pr['number']} in {full_name}: {pr.get('html_url')}")
    else:
        print(f"[WARN] PR might already exist for {full_name}")


def build_wiring_todo(system: Dict[str, Any]) -> str:
    name = system["name"]
    role = system.get("role")
    components = system.get("full_stack_components", {})

    lines = [
        f"# Garcar Autonomous Wiring TODO for {name}",
        "",
        f"Role: `{role}`",
        "",
        "## Required Garcar Base Contract",
        "- Implement `/health`, `/meta`, `/metrics`, `/events` endpoints.",
        "",
        "## Event Bus Wiring",
        "- Emit required events for this role.",
        "- Consume required arbitrage/control-plane events.",
        "",
        "## Current Full-Stack Components",
        f"- backend_api: {components.get('backend_api')}",
        f"- frontend_ui: {components.get('frontend_ui')}",
        f"- payment_hook: {components.get('payment_hook')}",
        f"- event_bus_connected: {components.get('event_bus_connected')}",
        f"- observability_connected: {components.get('observability_connected')}",
        "",
        "## Wiring Tasks",
        "1. Add or verify Garcar Base Contract endpoints.",
        "2. Add NATS/Redis Streams client and emit/consume required topics.",
        "3. Ensure metrics/events appear in Zeus/Atlas dashboards.",
        "4. Add tests for contract + event wiring.",
        "",
        "## Safety",
        "- Draft PR only. Do not auto-merge.",
        "- Respect CASH_LOCK: no live spend / no silent outbound.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    registry = load_system_registry()
    systems = registry.get("systems", [])
    tier1 = set(registry.get("fullstack_gap_analysis", {}).get("priority_tier_1", []))

    if not tier1:
        print("[ERROR] No priority_tier_1 systems in SYSTEM_REGISTRY.json", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Wiring {len(tier1)} tier-1 systems: {', '.join(sorted(tier1))}")

    for system in systems:
        if system["name"] not in tier1:
            continue

        github_url = system["github_url"]
        full_name = extract_repo_name(github_url)

        try:
            default_branch = get_repo_default_branch(full_name)
        except Exception as e:
            print(f"[WARN] Could not get default branch for {full_name}: {e}")
            continue

        wiring_branch = "garcar-autonomous-wiring"
        try:
            create_branch_from_default(full_name, wiring_branch)
        except Exception as e:
            print(f"[WARN] Could not create wiring branch in {full_name}: {e}")
            continue

        todo_md = build_wiring_todo(system)
        try:
            create_or_update_file(
                full_name,
                wiring_branch,
                "GARCAR_AUTONOMOUS_WIRING_TODO.md",
                todo_md,
                "Add Garcar autonomous wiring TODO",
            )
        except Exception as e:
            print(f"[WARN] Could not write TODO in {full_name}: {e}")
            continue

        try:
            open_draft_pr(
                full_name,
                wiring_branch,
                default_branch,
                "Garcar autonomous wiring: Base contract + event bus",
                todo_md,
                ["garcar-autonomous-wiring"],
            )
        except Exception as e:
            print(f"[WARN] Could not open PR in {full_name}: {e}")
            continue

    print("[INFO] Autonomous wiring orchestration completed.")


if __name__ == "__main__":
    main()
