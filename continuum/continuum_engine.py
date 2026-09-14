#!/usr/bin/env python3
"""
Continuum Grid Engine v1
------------------------
Observe → Plan → Verify → Propose (never silent mutate).

Read-only by default. Discovers repositories, inventories manifests,
scores readiness against the Garcar Base contract, and produces
deterministic upgrade plans. No code is written into target repos
from this module; mutation is delegated to bootstrap / PR tools.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Local imports (hub-relative)
try:
    from continuum.repository_registry import RepositoryRegistry, normalize_registry
    from continuum.upgrade_ledger import UpgradeLedger
except ImportError:
    # Allow running as script from continuum/
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from continuum.repository_registry import RepositoryRegistry, normalize_registry
    from continuum.upgrade_ledger import UpgradeLedger


HUB_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATHS = [
    HUB_ROOT / "registry" / "capability-registry.json",
    HUB_ROOT / "SYSTEM_REGISTRY.json",
    HUB_ROOT / "system-registry.yaml",
]
DEFAULT_LEDGER_PATH = HUB_ROOT / "continuum" / "upgrade_ledger.jsonl"
DEFAULT_PLAN_PATH = HUB_ROOT / "continuum" / "upgrade_plans" / "latest_plan.json"

# Pilot cohort — only these may be proposed against in v1 without explicit --allow
PILOT_ALLOWLIST: Set[str] = {
    "garcar-base",
    "continuum-agents",
    "systems-master-hub",
    "neural-mesh-pipeline",
    "garcar-enterprise-production",
}

# High-risk domains that must never auto-propose without human gate
HIGH_RISK_DOMAINS = {
    "payments",
    "revenue-intelligence",
    "legal-compliance",
    "security",
}

REQUIRED_MANIFEST_KEYS = [
    "system_id",
    "name",
    "domain",
    "role",
    "capabilities",
    "revenue",
    "endpoints",
    "events",
]

BASE_CAPABILITIES = [
    "health_endpoint",
    "metrics_endpoint",
    "webhook_receiver",
    "auth_layer",
    "event_bus_connected",
    "audit_log_emission",
    "self_healing",
    "revenue_signal_emitter",
]


@dataclass
class RepoInventory:
    system_id: str
    repo_url: Optional[str] = None
    domain: Optional[str] = None
    role: Optional[str] = None
    maturity_score: float = 0.0
    has_manifest: bool = False
    manifest_valid: bool = False
    capabilities_complete: List[str] = field(default_factory=list)
    capabilities_missing: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    readiness_score: float = 0.0
    notes: List[str] = field(default_factory=list)


@dataclass
class UpgradeAction:
    system_id: str
    action_type: str  # add_manifest | add_capability | normalize_registry | docs
    target: str
    description: str
    risk: str  # low | medium | high
    fingerprint: str
    allowed_in_pilot: bool = False


@dataclass
class UpgradePlan:
    generated_at: str
    mode: str  # observe | plan | dry-run
    inventories: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    summary: Dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fingerprint(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()[:16]


def score_readiness(inv: RepoInventory) -> float:
    """Deterministic readiness 0–100 from inventory signals."""
    score = 0.0
    if inv.has_manifest:
        score += 25.0
    if inv.manifest_valid:
        score += 15.0
    total_caps = len(BASE_CAPABILITIES)
    if total_caps:
        done = len([c for c in inv.capabilities_complete if c in BASE_CAPABILITIES])
        score += 40.0 * (done / total_caps)
    # maturity from registry if present
    score += min(20.0, inv.maturity_score * 0.2)
    # penalties
    if inv.domain in HIGH_RISK_DOMAINS:
        score *= 0.85
    if "missing_system_id" in inv.risk_flags:
        score -= 10.0
    return max(0.0, min(100.0, round(score, 1)))


def inventory_from_registry_entry(system_id: str, entry: Dict[str, Any]) -> RepoInventory:
    inv = RepoInventory(
        system_id=system_id,
        repo_url=entry.get("repo_url"),
        domain=entry.get("domain"),
        role=entry.get("role"),
        maturity_score=float(entry.get("maturity_score") or 0),
        capabilities_complete=list(entry.get("capabilities_complete") or []),
        capabilities_missing=list(entry.get("capabilities_missing") or []),
    )
    if inv.domain in HIGH_RISK_DOMAINS:
        inv.risk_flags.append("high_risk_domain")
    if not inv.repo_url:
        inv.risk_flags.append("missing_repo_url")
    inv.readiness_score = score_readiness(inv)
    return inv


def plan_actions(inv: RepoInventory, ledger: UpgradeLedger) -> List[UpgradeAction]:
    actions: List[UpgradeAction] = []
    allowed = inv.system_id in PILOT_ALLOWLIST

    if not inv.has_manifest:
        fp = fingerprint("add_manifest", inv.system_id)
        if not ledger.seen(fp):
            actions.append(
                UpgradeAction(
                    system_id=inv.system_id,
                    action_type="add_manifest",
                    target="garcar.manifest.json",
                    description="Add standard Garcar Base manifest from template",
                    risk="low" if allowed else "medium",
                    fingerprint=fp,
                    allowed_in_pilot=allowed,
                )
            )

    for cap in inv.capabilities_missing:
        if cap not in BASE_CAPABILITIES:
            continue
        fp = fingerprint("add_capability", inv.system_id, cap)
        if ledger.seen(fp):
            continue
        risk = "high" if inv.domain in HIGH_RISK_DOMAINS else ("low" if allowed else "medium")
        actions.append(
            UpgradeAction(
                system_id=inv.system_id,
                action_type="add_capability",
                target=cap,
                description=f"Scaffold capability '{cap}' via contract templates",
                risk=risk,
                fingerprint=fp,
                allowed_in_pilot=allowed,
            )
        )

    return actions


def run_observe(registry: RepositoryRegistry, ledger: UpgradeLedger) -> UpgradePlan:
    inventories: List[RepoInventory] = []
    all_actions: List[UpgradeAction] = []

    for system_id, entry in registry.systems.items():
        inv = inventory_from_registry_entry(system_id, entry)
        # Lightweight local check if hub itself
        if system_id == "systems-master-hub":
            manifest_path = HUB_ROOT / "garcar.manifest.json"
            inv.has_manifest = manifest_path.exists()
            if inv.has_manifest:
                try:
                    data = json.loads(manifest_path.read_text())
                    inv.manifest_valid = all(k in data for k in REQUIRED_MANIFEST_KEYS)
                except Exception:
                    inv.manifest_valid = False
                    inv.notes.append("manifest_parse_error")
            inv.readiness_score = score_readiness(inv)

        inventories.append(inv)
        all_actions.extend(plan_actions(inv, ledger))

    # Only surface pilot-allowed or low-risk actions in default plan
    proposeable = [
        a for a in all_actions
        if a.allowed_in_pilot or a.risk == "low"
    ]

    summary = {
        "total_systems": len(inventories),
        "avg_readiness": round(
            sum(i.readiness_score for i in inventories) / max(1, len(inventories)), 1
        ),
        "actions_total": len(all_actions),
        "actions_proposeable": len(proposeable),
        "pilot_allowlist": sorted(PILOT_ALLOWLIST),
        "high_risk_blocked": len([a for a in all_actions if a.risk == "high"]),
    }

    return UpgradePlan(
        generated_at=_utc_now(),
        mode="observe",
        inventories=[asdict(i) for i in inventories],
        actions=[asdict(a) for a in proposeable],
        summary=summary,
    )


def write_plan(plan: UpgradePlan, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(plan), indent=2))
    print(f"Wrote plan → {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Continuum Grid Engine v1")
    parser.add_argument(
        "--mode",
        choices=["observe", "plan", "dry-run"],
        default="observe",
        help="observe=inventory only; plan=write plan; dry-run=plan without side effects",
    )
    parser.add_argument("--registry", type=str, default=None, help="Path to capability-registry.json")
    parser.add_argument("--ledger", type=str, default=str(DEFAULT_LEDGER_PATH))
    parser.add_argument("--out", type=str, default=str(DEFAULT_PLAN_PATH))
    parser.add_argument(
        "--allow",
        nargs="*",
        default=[],
        help="Extra system_ids allowed beyond pilot allowlist (still no auto-merge)",
    )
    args = parser.parse_args()

    if args.allow:
        PILOT_ALLOWLIST.update(args.allow)

    reg_path = Path(args.registry) if args.registry else None
    if reg_path is None:
        for candidate in DEFAULT_REGISTRY_PATHS:
            if candidate.exists():
                reg_path = candidate
                break
    if reg_path is None or not reg_path.exists():
        print("ERROR: No registry found. Expected registry/capability-registry.json", file=sys.stderr)
        return 1

    registry = normalize_registry(reg_path)
    ledger = UpgradeLedger(Path(args.ledger))

    plan = run_observe(registry, ledger)
    plan.mode = args.mode

    if args.mode in ("plan", "dry-run", "observe"):
        write_plan(plan, Path(args.out))

    print("\n══ Continuum Grid v1 — Summary ══")
    for k, v in plan.summary.items():
        print(f"  {k}: {v}")
    print(f"  mode: {plan.mode}")
    print("  (No target repos were modified. Proposals require explicit bootstrap + PR.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
