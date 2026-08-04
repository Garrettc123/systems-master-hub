"""
detect_upgrade_targets.py
Scans SYSTEM_REGISTRY.json, compares each system's current tier against
its upgrade_history, and writes upgrade_targets.json listing which systems
are eligible for their next tier this cycle. Never re-selects a system that
already advanced today (idempotent, never-repeat guarantee).
"""

import json
import sys
from datetime import datetime, timezone

REGISTRY_PATH = "SYSTEM_REGISTRY.json"
OUTPUT_PATH = "upgrade_targets.json"

TIER_ORDER = [
    "scaffolded", "connected", "autonomous",
    "predictive", "self_improving", "cross_system_emergent",
    "mastery_convergence",
]


def current_tier(system: dict) -> str:
    history = system.get("upgrade_history", [])
    if not history:
        return "scaffolded"
    return history[-1].get("tier", "scaffolded")


def already_advanced_today(system: dict) -> bool:
    today = datetime.now(timezone.utc).date().isoformat()
    for h in system.get("upgrade_history", []):
        if h.get("date", "").startswith(today):
            return True
    return False


def main():
    with open(REGISTRY_PATH) as f:
        registry = json.load(f)

    priority = set(registry.get("fullstack_gap_analysis", {}).get("priority_tier_1", []))
    targets = []

    for system in registry["systems"]:
        if already_advanced_today(system):
            continue
        tier = current_tier(system)
        idx = TIER_ORDER.index(tier) if tier in TIER_ORDER else 0
        if idx >= len(TIER_ORDER) - 1:
            continue  # already at Mastery Convergence
        next_tier = TIER_ORDER[idx + 1]
        targets.append({
            "name": system["name"],
            "current_tier": tier,
            "next_tier": next_tier,
            "priority": system["name"] in priority,
            "full_stack_gaps": system.get("full_stack_components", {}),
        })

    targets.sort(key=lambda t: (not t["priority"], t["name"]))
    selected = targets[:10]

    with open(OUTPUT_PATH, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_eligible": len(targets),
            "selected_for_this_cycle": selected,
        }, f, indent=2)

    print(f"Selected {len(selected)} of {len(targets)} eligible systems for upgrade this cycle")


if __name__ == "__main__":
    sys.exit(main())
