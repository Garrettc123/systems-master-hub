#!/usr/bin/env python3
"""
Garcar Enterprise — Sweep Status Checker
Polls GitHub Actions for all revenue repos and writes SWEEP_LOG.json
Run: python3 orchestrate/sweep-status.py
Requires: GITHUB_TOKEN env var
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

REPOS = [
    "garcar-payments",
    "garcar-payment-loop",
    "TITAN-Autonomous-Business-Empire",
    "enterprise-mlops-platform",
    "atlas-dashboard",
    "zeus-dashboard",
    "mars-api",
    "neural-mesh",
    "ai-business-platform",
    "autonomous-income-deployment",
]

OWNER = "Garrettc123"
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def gh_get(path):
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": str(e)}


def check_repo(repo):
    runs = gh_get(f"/repos/{OWNER}/{repo}/actions/runs?per_page=1")
    if "error" in runs:
        return {"repo": repo, "status": "error", "detail": runs["error"]}
    items = runs.get("workflow_runs", [])
    if not items:
        return {"repo": repo, "status": "no_runs", "updated_at": None}
    r = items[0]
    return {
        "repo": repo,
        "status": r.get("status"),
        "conclusion": r.get("conclusion"),
        "updated_at": r.get("updated_at"),
        "run_id": r.get("id"),
        "url": r.get("html_url"),
    }


def main():
    print("🚀 GARCAR EMPIRE SWEEP STATUS")
    print(f"   {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    results = []
    for repo in REPOS:
        r = check_repo(repo)
        results.append(r)
        status_icon = {
            "completed": "✅",
            "in_progress": "🔄",
            "queued": "⏳",
            "no_runs": "⚠️",
            "error": "❌",
        }.get(r.get("status"), "❓")
        conclusion = r.get("conclusion") or ""
        print(f"  {status_icon} {repo:<45} {r.get('status','?')}/{conclusion}")

    log = {
        "sweep_time": datetime.now(timezone.utc).isoformat(),
        "owner": OWNER,
        "results": results,
    }
    with open("SWEEP_LOG.json", "w") as f:
        json.dump(log, f, indent=2)
    print("\n📝 SWEEP_LOG.json written.")

    failed = [r for r in results if r.get("conclusion") == "failure"]
    if failed:
        print(f"\n⚠️  {len(failed)} repo(s) with failed runs:")
        for r in failed:
            print(f"   ❌ {r['repo']} — {r.get('url', '')}")
    else:
        print("\n✅ All repos checked. No failures detected.")


if __name__ == "__main__":
    main()
