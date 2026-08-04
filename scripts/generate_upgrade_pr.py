"""
generate_upgrade_pr.py
Reads upgrade_targets.json, and for each selected system produces a
concrete upgrade patch proposal (files to add/modify) advancing it exactly
one capability tier. Writes proposals to upgrade_proposals/ as structured
JSON for open_upgrade_pr.py to consume. This does NOT call an LLM directly;
it is deterministic scaffolding per tier so the loop is auditable.
"""

import argparse
import json
import os
from datetime import datetime, timezone

TARGETS_PATH = "upgrade_targets.json"
PROPOSALS_DIR = "upgrade_proposals"

TIER_ACTIONS = {
    "connected": {
        "description": "Add FastAPI health endpoint, register on Universal Event Bus, wire observability ping.",
        "files": ["app/main.py", "event_bus_client.py", "observability_hook.py"],
    },
    "autonomous": {
        "description": "Add auto-retry, auto-scale, and self-healing guardrails using autonomous-self-healing patterns.",
        "files": ["ops/auto_recovery.py", "ops/guardrails.yaml"],
    },
    "predictive": {
        "description": "Add ML/RHNS forecasting module for failure and revenue-impact prediction.",
        "files": ["ml/forecast_model.py", "ml/train_predictor.py"],
    },
    "self_improving": {
        "description": "Enable nightly self-PR generation with automatic rollback on regression.",
        "files": [".github/workflows/self_upgrade.yml"],
    },
    "cross_system_emergent": {
        "description": "Compose with 2+ other registered systems via the event bus to unlock a new joint capability.",
        "files": ["integrations/cross_system_composer.py"],
    },
    "mastery_convergence": {
        "description": "Final convergence into the unified Garcar Apex Nexus control plane.",
        "files": ["convergence/apex_link.py"],
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", type=int, default=1)
    args = parser.parse_args()

    if not os.path.exists(TARGETS_PATH):
        print("No upgrade_targets.json found — nothing to propose.")
        return

    with open(TARGETS_PATH) as f:
        targets = json.load(f)

    os.makedirs(PROPOSALS_DIR, exist_ok=True)
    written = 0

    for t in targets.get("selected_for_this_cycle", []):
        action = TIER_ACTIONS.get(t["next_tier"])
        if not action:
            continue
        proposal = {
            "system": t["name"],
            "from_tier": t["current_tier"],
            "to_tier": t["next_tier"],
            "description": action["description"],
            "files_to_add_or_modify": action["files"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        out_path = os.path.join(PROPOSALS_DIR, f"{t['name']}.json")
        with open(out_path, "w") as f:
            json.dump(proposal, f, indent=2)
        written += 1

    print(f"Wrote {written} upgrade proposals to {PROPOSALS_DIR}/")


if __name__ == "__main__":
    main()
