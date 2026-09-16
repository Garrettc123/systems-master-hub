"""GARCAR CRF governed repair executor.

Level-2 worker: claim -> diagnose -> policy -> verify -> draft PR.
This implementation intentionally fails closed when required integrations are absent.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BLOCKED_PATTERNS = [
    re.compile(r"(^|/)(\.env|.*\.pem|.*\.key)$", re.I),
    re.compile(r"(password|secret|api[_-]?key|private[_-]?key)", re.I),
    re.compile(r"drop\s+(table|schema|database)", re.I),
    re.compile(r"truncate\s+table", re.I),
]


@dataclass
class RepairPlan:
    repository: str
    base_ref: str
    files: list[str]
    diagnosis: str
    patch: str
    risk: float
    rollback: str


def load_policy(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def risk_score(plan: RepairPlan) -> float:
    score = 0.10
    if len(plan.files) > 3:
        score += 0.20
    if any("migration" in f.lower() or "schema" in f.lower() for f in plan.files):
        score += 0.35
    if any(p.search(plan.patch) for p in BLOCKED_PATTERNS):
        score = 1.0
    return min(score, 1.0)


def policy_check(plan: RepairPlan, policy: dict[str, Any]) -> tuple[bool, str]:
    if not plan.repository or not plan.base_ref:
        return False, "missing_repository_scope"
    if not plan.files:
        return False, "empty_change_scope"
    if any(p.search(plan.patch) for p in BLOCKED_PATTERNS):
        return False, "blocked_sensitive_or_destructive_change"
    score = risk_score(plan)
    if score >= policy["risk_thresholds"]["critical"]:
        return False, "critical_risk_requires_human_review"
    return True, "approved_for_draft_pr"


def verify_patch(repo_dir: Path) -> tuple[bool, str]:
    commands = []
    if (repo_dir / "pytest.ini").exists() or (repo_dir / "pyproject.toml").exists() or list(repo_dir.glob("tests/**/*.py")):
        commands.append(["python", "-m", "pytest", "-q"])
    if (repo_dir / "package.json").exists():
        commands.append(["npm", "test", "--", "--runInBand"])
    if not commands:
        return False, "no_supported_test_runner_detected"
    for command in commands:
        proc = subprocess.run(command, cwd=repo_dir, text=True, capture_output=True, timeout=600)
        if proc.returncode != 0:
            return False, f"verification_failed: {' '.join(command)}\n{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
    return True, "verification_passed"


def main() -> int:
    policy = load_policy(Path(__file__).with_name("policy.json"))
    required = ["CRF_REPAIR_ID", "CRF_REPOSITORY", "CRF_BASE_REF"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print(json.dumps({"status": "blocked", "reason": "missing_configuration", "missing": missing}))
        return 2

    # Diagnosis/patch generation is intentionally delegated to a configured provider.
    # Never fabricate a repair when no provider is configured.
    if not os.getenv("CRF_LLM_PROVIDER"):
        print(json.dumps({"status": "blocked", "reason": "LLM_NOT_CONFIGURED"}))
        return 3

    print(json.dumps({
        "status": "ready",
        "repair_id": os.environ["CRF_REPAIR_ID"],
        "repository": os.environ["CRF_REPOSITORY"],
        "base_ref": os.environ["CRF_BASE_REF"],
        "autonomy_level": policy["autonomy_level"],
        "next": "provider_adapter_required",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
