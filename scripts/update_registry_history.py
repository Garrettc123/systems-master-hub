"""
update_registry_history.py
After proposals are generated (and PRs opened), appends an upgrade_history
entry to each targeted system in SYSTEM_REGISTRY.json, marking the tier
transition as proposed for today. This is what makes the never-repeat rule
enforceable: detect_upgrade_targets.py checks this history before selecting
systems on the next run.
"""

import json
import glob
import os
from datetime import datetime, timezone

REGISTRY_PATH = "SYSTEM_REGISTRY.json"
PROPOSALS_DIR = "upgrade_proposals"


def main():
    if not os.path.exists(REGISTRY_PATH):
        print("SYSTEM_REGISTRY.json not found.")
        return

    with open(REGISTRY_PATH) as f:
        registry = json.load(f)

    by_name = {s["name"]: s for s in registry["systems"]}
    now = datetime.now(timezone.utc).isoformat()
    updated = 0

    for path in glob.glob(f"{PROPOSALS_DIR}/*.json"):
        with open(path) as f:
            proposal = json.load(f)

        system = by_name.get(proposal["system"])
        if not system:
            continue

        system.setdefault("upgrade_history", []).append({
            "date": now,
            "from_tier": proposal["from_tier"],
            "tier": proposal["to_tier"],
            "description": proposal["description"],
            "status": "proposed",
        })
        system["next_upgrade_target"] = proposal["to_tier"]
        updated += 1

    registry["last_updated"] = now

    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)

    print(f"Updated upgrade_history for {updated} systems in registry.")


if __name__ == "__main__":
    main()
