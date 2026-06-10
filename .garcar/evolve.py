#!/usr/bin/env python3
"""
GARCAR APEX Evolution Agent — evolve.py v3.0
Runs daily via GitHub Actions on every system in the 332-system ecosystem.
Never repeats an upgrade. Only adds new capabilities. Writes immutable evolution log.
Philosophy: Never repeat. Only upgrade. Converge to mastery.
Author: Garrett Carrol — Garcar Enterprise
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
    if manifest_file.exists():
        return json.loads(manifest_file.read_text())
    return {}


def compute_maturity_score(capabilities: dict, weights: dict) -> float:
    total_weight = sum(weights.values())
    earned = sum(weights[cap] for cap, val in capabilities.items() if val and cap in weights)
    return round((earned / total_weight) * 100, 1)


def identify_next_upgrade(capabilities: dict, weights: dict) -> str:
    """Returns the single highest-value missing capability. Never repeats."""
    missing = {cap: weight for cap, weight in weights.items()
               if not capabilities.get(cap, False)}
    if not missing:
        return None
    return max(missing, key=missing.get)


def scaffold_capability(capability: str, templates: dict, system_id: str) -> str:
    template = templates.get(capability, {})
    code = template.get("scaffold", f"# TODO: Implement {capability}\n")
    code = code.replace("SYSTEM_ID", f'"{system_id}"')
    date_str = datetime.now(timezone.utc).date()
    header = f"# ═══════════════════════════════════════════════════\n"
    header += f"# AUTO-EVOLVED by GARCAR evolve.py — {date_str}\n"
    header += f"# Capability: {capability}\n"
    header += f"# System: {system_id}\n"
    header += f"# This file was generated once and will never be overwritten.\n"
    header += f"# ═══════════════════════════════════════════════════\n\n"
    return header + code + "\n"


def write_evolution_log(system_id: str, upgrade: str, score_before: float,
                        score_after: float, count: int, log_path: Path):
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / "DAILY_EVOLUTION_LOG.md"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    gain = round(score_after - score_before, 1)
    entry = (
        f"\n## [{today}] `{system_id}` — Evolution #{count}\n"
        f"- **Capability Added:** `{upgrade}`\n"
        f"- **Maturity Score:** `{score_before}%` → `{score_after}%` (+{gain}%)\n"
        f"- **Status:** ✅ Evolved — never repeated, always upgraded\n"
        f"---\n"
    )
    with open(log_file, "a") as f:
        f.write(entry)
    print(f"📝 Evolution logged: [{system_id}] +{upgrade} ({score_before}% → {score_after}%)")


def update_manifest(manifest: dict, system_id: str, upgrade: str,
                    score: float, sys_data: dict) -> dict:
    # Seed known fields from registry if this is a new manifest
    if not manifest.get("system_id"):
        manifest["system_id"] = system_id
        manifest["name"] = sys_data.get("name", system_id)
        manifest["domain"] = sys_data.get("domain", "infrastructure")
        manifest["role"] = sys_data.get("role", "processor")
        manifest["revenue"] = {
            "model": sys_data.get("revenue_model", "none"),
            "monthly_target_usd": sys_data.get("monthly_target_usd", 0),
            "attribution_code": f"GARCAR-{system_id.upper()}"
        }
        manifest["events"] = {
            "emits": sys_data.get("events_emits", []),
            "consumes": sys_data.get("events_consumes", [])
        }
        manifest["deployment"] = {"platform": sys_data.get("deployment", "railway")}

    if "capabilities" not in manifest:
        manifest["capabilities"] = {}
    manifest["capabilities"][upgrade] = True

    if "evolution" not in manifest:
        manifest["evolution"] = {"evolution_count": 0}
    manifest["evolution"]["last_evolved"] = datetime.now(timezone.utc).isoformat()
    manifest["evolution"]["evolution_count"] = manifest["evolution"].get("evolution_count", 0) + 1
    manifest["evolution"]["maturity_score"] = score
    manifest["evolution"]["last_capability_added"] = upgrade
    return manifest


def main():
    parser = argparse.ArgumentParser(description="GARCAR Autonomous Evolution Agent")
    parser.add_argument("--system",   required=True,  help="System ID (repo name)")
    parser.add_argument("--path",     default=".",    help="Path to system repo root")
    parser.add_argument("--registry", default=APEX_REGISTRY_URL)
    parser.add_argument("--log-to",   default=".",    help="Path to write evolution log")
    parser.add_argument("--dry-run",  action="store_true")
    args = parser.parse_args()

    system_id  = args.system
    system_path = Path(args.path)
    log_path    = Path(args.log_to)

    print(f"\n🧬 GARCAR APEX Evolution Agent v3.0")
    print(f"   System  : {system_id}")
    print(f"   Date    : {datetime.now(timezone.utc).date()}")
    print(f"   Rule    : Never repeat — only upgrade\n")

    # Load registry
    try:
        registry = fetch_json(args.registry)
    except Exception as e:
        print(f"⚠️  Registry fetch failed: {e}. Attempting local fallback.")
        local = system_path / "registry" / "capability-registry.json"
        if local.exists():
            registry = json.loads(local.read_text())
        else:
            print("❌ No registry available. Exiting.")
            sys.exit(1)

    weights      = registry.get("capability_weights", {})
    templates    = registry.get("templates", {})
    systems_data = registry.get("systems", {})

    if system_id not in systems_data:
        print(f"ℹ️  {system_id} not in registry yet. Add it to registry/capability-registry.json to enable evolution.")
        sys.exit(0)

    sys_data     = systems_data[system_id]
    manifest     = load_local_manifest(system_path)
    capabilities = manifest.get("capabilities", {})

    # Seed capabilities from registry
    for cap in sys_data.get("capabilities_complete", []):
        capabilities.setdefault(cap, True)
    for cap in sys_data.get("capabilities_missing", []):
        capabilities.setdefault(cap, False)
    manifest["capabilities"] = capabilities

    score_before  = compute_maturity_score(capabilities, weights)
    next_upgrade  = identify_next_upgrade(capabilities, weights)

    if not next_upgrade:
        print(f"🏆 {system_id} has reached MASTERY (100%). No upgrade needed today.")
        sys.exit(0)

    print(f"   Current maturity : {score_before}%")
    print(f"   Today's upgrade  : {next_upgrade}")

    scaffold_code = scaffold_capability(next_upgrade, templates, system_id)
    scaffold_dir  = system_path / ".garcar" / "scaffolds"

    if not args.dry_run:
        scaffold_dir.mkdir(parents=True, exist_ok=True)
        scaffold_file = scaffold_dir / f"{next_upgrade}.py"
        if not scaffold_file.exists():  # IMMUTABLE — never overwrite
            scaffold_file.write_text(scaffold_code)
            print(f"   ✅ Scaffold written : {scaffold_file}")
        else:
            print(f"   ⏭️  Already exists  : {next_upgrade} (no repeats — skipped)")

    capabilities[next_upgrade] = True
    score_after      = compute_maturity_score(capabilities, weights)
    updated_manifest = update_manifest(manifest, system_id, next_upgrade, score_after, sys_data)

    if not args.dry_run:
        manifest_file = system_path / "garcar.manifest.json"
        manifest_file.write_text(json.dumps(updated_manifest, indent=2))
        print(f"   ✅ Manifest updated")
        write_evolution_log(
            system_id, next_upgrade, score_before, score_after,
            updated_manifest["evolution"]["evolution_count"], log_path
        )

    print(f"\n🚀 Evolution complete: {system_id}")
    print(f"   Maturity : {score_before}% → {score_after}%  (+{round(score_after-score_before,1)}%)")
    print(f"   Added    : {next_upgrade}")
    print(f"   Count    : #{updated_manifest['evolution']['evolution_count']}")
    print(f"   Remaining gaps: {len([c for c,v in capabilities.items() if not v])} capabilities\n")


if __name__ == "__main__":
    main()
