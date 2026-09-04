from __future__ import annotations

import json
import os
import urllib.request
from datetime import UTC, datetime

token = os.environ["GH_TOKEN"]


def request(url: str):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


repos = []
for page in range(1, 11):
    batch = request(f"https://api.github.com/user/repos?affiliation=owner&per_page=100&page={page}&sort=updated")
    repos.extend(batch)
    if len(batch) < 100:
        break

active = [r for r in repos if not r["archived"]]
archived = [r for r in repos if r["archived"]]
without_description = [r for r in active if not r.get("description")]
without_topics = [r for r in active if not r.get("topics")]
without_license = [r for r in active if not r.get("license")]

print("<!-- garcar-daily-repository-readiness -->")
print("# Daily repository readiness audit")
print()
print(f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
print()
print("## Scope")
print(f"- Owned repositories inspected: {len(repos)}")
print(f"- Active repositories: {len(active)}")
print(f"- Archived repositories: {len(archived)}")
print()
print("## Governance signals")
print(f"- Active repos without descriptions: {len(without_description)}")
print(f"- Active repos without topics: {len(without_topics)}")
print(f"- Active repos without licenses: {len(without_license)}")
print()
print("## Recommended human-reviewed work")
for label, records in [
    ("Descriptions", without_description),
    ("Topics", without_topics),
    ("Licenses", without_license),
]:
    sample = ", ".join(f"`{r['name']}`" for r in records[:20]) or "None"
    print(f"- **{label}:** {sample}")
print()
print("## Safety boundary")
print("This audit only reads repository metadata and maintains this single issue. It does not modify application repositories, secrets, deployments, billing systems, pull requests, or financial accounts. Review any proposed implementation work before assigning it to an agent.")
