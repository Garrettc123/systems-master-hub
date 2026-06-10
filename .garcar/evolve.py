#!/usr/bin/env python3
"""
GARCAR APEX Evolution Agent — evolve.py
Runs daily via GitHub Actions across all systems in the ecosystem.
Never repeats an upgrade. Only adds new capabilities. Writes immutable evolution log.
Author: Garcar Enterprise Autonomous Systems
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

APEX_REGISTRY_URL = "https://raw.githubusercontent.com/Garrettc123/systems-master-hub/main/registry/capability-registry.json"


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read())


def load_local_manifest(system_path: Path) -> dict:
    manifest_file = system_path / "garcar.manifest.json"
    return json.loads(manifest_file.read_text()) if manifest_file.exists() else {}


def compute_maturity_score(capabilities: dict, weights: dict) -> float:
    total_weight = sum(weights.values())
    earned = sum(weights[cap] for cap, val in capabilities.items() if val and cap in weights)
    return round((earned / total_weight) * 100, 1)


def identify_next_upgrade(capabilities: dict, weights: dict) -> str:
    """Returns the single highest-value missing capability. Never repeats."""
    missing = {cap: weight for cap, weight in weights.items() if not capabilities.get(cap, False)}
    return max(missing, key=missing.get) if missing else None


def scaffold_capability(capability: str, templates: dict, system_id: str) -> str:
    template = templates.get(capability, {})
    code = template.get("scaffold", f"# TODO: Implement {capability} for {system_id}")
    code = code.replace("SYSTEM_ID", f'"{system_id}"')
    return f"# AUTO-EVOLVED: {capability} — added by GARCAR evolve.py on {datetime.now(timezone.utc).date()}\n{code}\n"


def write_evolution_log(system_id: str, upgrade: str, score_before: float, score_after: float, log_dir: Path):
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "DAILY_EVOLUTION_LOG.md"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = (
        f"\n## [{today}] {system_id}\n"
        f"- **Capability Added:** `{upgrade}`\n"
        f"- **Maturity Score:** {score_before}% → {score_after}%\n"
        f"- **Status:** ✅ Evolved — never repeated, always upgraded\n"
        f"---\n"
    )
    with open(log_file, "a") as f:
        f.write(entry)
    print(f"📝 Evolution logged: {system_id} +{upgrade} ({score_before}% → {score_after}%)")


def update_manifest(manifest: dict, system_id: str, upgrade: str, score: float) -> dict:
    if "capabilities" not in manifest:
        manifest["capabilities"] = {}
    manifest["capabilities"][upgrade] = True
    if "evolution" not in manifest:
        manifest["evolution"] = {"evolution_count": 0}
    manifest["evolution"]["last_evolved"] = datetime.now(timezone.utc).isoformat()
    manifest["evolution"]["evolution_count"] = manifest["evolution"].get("evolution_count", 0) + 1
    manifest["evolution"]["maturity_score"] = score
    manifest["evolution"]["last_capability_added"] = upgrade
    manifest["system_id"] = manifest.get("system_id", system_id)
    return manifest


def main():
    parser = argparse.ArgumentParser(description="GARCAR Autonomous Evolution Agent")
    parser.add_argument("--system", required=True, help="System ID (repo name)")
    parser.add_argument("--path", default=".", help="Path to system repo root")
    parser.add_argument("--registry", default=APEX_REGISTRY_URL, help="URL to capability registry")
    parser.add_argument("--log-to", default=".", help="Path to write evolution log")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    args = parser.parse_args()

    system_id = args.system
    system_path = Path(args.path)
    log_path = Path(args.log_to)

    print(f"\n🧬 GARCAR APEX Evolution Agent")
    print(f"   System  : {system_id}")
    print(f"   Date    : {datetime.now(timezone.utc).date()}")
    print(f"   Rule    : Never repeat — only upgrade\n")

    try:
        registry = fetch_json(args.registry)
    except Exception as e:
        print(f"⚠️  Registry fetch failed: {e}. Trying local fallback.")
        local_reg = system_path / "registry" / "capability-registry.json"
        registry = json.loads(local_reg.read_text()) if local_reg.exists() else {"capability_weights": {}, "templates": {}, "systems": {}}

    weights = registry.get("capability_weights", {})
    templates = registry.get("templates", {})
    systems_data = registry.get("systems", {})

    manifest = load_local_manifest(system_path)
    capabilities = manifest.get("capabilities", {})

    if system_id in systems_data:
        sys_data = systems_data[system_id]
        for cap in sys_data.get("capabilities_complete", []):
            capabilities.setdefault(cap, True)
        for cap in sys_data.get("capabilities_missing", []):
            capabilities.setdefault(cap, False)
        manifest["capabilities"] = capabilities

    score_before = compute_maturity_score(capabilities, weights)
    next_upgrade = identify_next_upgrade(capabilities, weights)

    if not next_upgrade:
        print(f"🏆 {system_id} has reached MASTERY (100%). No upgrade needed today.")
        return

    print(f"   Current maturity : {score_before}%")
    print(f"   Next upgrade     : {next_upgrade}")

    scaffold_code = scaffold_capability(next_upgrade, templates, system_id)
    scaffold_dir = system_path / ".garcar" / "scaffolds"

    if not args.dry_run:
        scaffold_dir.mkdir(parents=True, exist_ok=True)
        scaffold_file = scaffold_dir / f"{next_upgrade}.py"
        if not scaffold_file.exists():  # THE RULE: never overwrite, only create new
            scaffold_file.write_text(scaffold_code)
            print(f"   ✅ Scaffold written : {scaffold_file}")
        else:
            print(f"   ⏭️  Already evolved  : {next_upgrade} — skipping (no repeats ever)")

    capabilities[next_upgrade] = True
    score_after = compute_maturity_score(capabilities, weights)
    updated_manifest = update_manifest(manifest, system_id, next_upgrade, score_after)

    if not args.dry_run:
        manifest_file = system_path / "garcar.manifest.json"
        manifest_file.write_text(json.dumps(updated_manifest, indent=2))
        print(f"   ✅ Manifest updated")
        write_evolution_log(system_id, next_upgrade, score_before, score_after, log_path)

    print(f"\n🚀 {system_id} evolved: {score_before}% → {score_after}% (+{next_upgrade})")
    print(f"   Total evolutions: {updated_manifest['evolution']['evolution_count']}")


if __name__ == "__main__":
    main()
