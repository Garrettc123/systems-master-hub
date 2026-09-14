import json
import os
from pathlib import Path

from worker import RepairPlan, load_policy, policy_check, risk_score


def test_policy_blocks_sensitive_patch():
    policy = load_policy(Path(__file__).with_name("policy.json"))
    plan = RepairPlan("owner/repo", "main", ["app.py"], "bug", "api_key = 'secret'", 0, "revert")
    ok, reason = policy_check(plan, policy)
    assert not ok
    assert reason == "blocked_sensitive_or_destructive_change"


def test_policy_accepts_small_normal_patch():
    policy = load_policy(Path(__file__).with_name("policy.json"))
    plan = RepairPlan("owner/repo", "main", ["app.py"], "null guard", "return value or 0", 0, "revert commit")
    ok, reason = policy_check(plan, policy)
    assert ok
    assert reason == "approved_for_draft_pr"
    assert risk_score(plan) < 0.30


def test_worker_fails_closed_without_provider(monkeypatch, capsys):
    monkeypatch.delenv("CRF_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("CRF_REPAIR_ID", "repair-1")
    monkeypatch.setenv("CRF_REPOSITORY", "owner/repo")
    monkeypatch.setenv("CRF_BASE_REF", "main")
    import worker
    assert worker.main() == 3
    assert "LLM_NOT_CONFIGURED" in capsys.readouterr().out
