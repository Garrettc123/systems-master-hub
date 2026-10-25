import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))


@pytest.fixture()
def server_module(tmp_path, monkeypatch):
    monkeypatch.setenv("GARCAR_MCP_DB", str(tmp_path / "ledger.sqlite3"))
    monkeypatch.delenv("GARCAR_OPERATOR_APPROVAL_TOKEN", raising=False)
    import garcar_mcp.server as server
    server.DB_PATH = Path(os.environ["GARCAR_MCP_DB"])
    return server


def test_unknown_action_fails_closed(server_module):
    result = server_module.evaluate_action_policy("shell.exec", ["evidence://ticket/1"])
    assert result["allowed"] is False
    assert result["reason"] == "action_not_allowlisted"


def test_registered_state_defaults_to_no_external_execution(server_module):
    result = server_module.evaluate_action_policy("github.write", ["evidence://pr/123"])
    assert result["allowed_to_execute"] is False
    assert result["adapter_registered"] is False


def test_request_requires_evidence(server_module):
    result = server_module.request_action("crm.email.send", "Send approved prospect message", [])
    assert result["created"] is False
    assert result["reason"] == "evidence_required"


def test_request_and_approval_never_claim_execution(server_module, monkeypatch):
    monkeypatch.setenv("GARCAR_OPERATOR_APPROVAL_TOKEN", "test-operator-token")
    created = server_module.request_action(
        "github.write", "Create a reviewed issue", ["evidence://ticket/123"]
    )
    assert created["created"] is True
    assert created["status"] == "pending"
    decision = server_module.decide_action(
        created["request_id"], "approve", "test-operator-token", "Approved for review"
    )
    assert decision["status"] == "approved"
    assert "does not enable" in decision["message"]
    executed = server_module.execute_action(created["request_id"])
    assert executed["executed"] is False
    assert executed["reason"] == "adapter_not_registered"


def test_invalid_operator_token_is_denied(server_module, monkeypatch):
    monkeypatch.setenv("GARCAR_OPERATOR_APPROVAL_TOKEN", "correct-token")
    result = server_module.decide_action("missing-id", "approve", "wrong-token")
    assert result["decided"] is False
    assert result["reason"] == "invalid_operator_token"


def test_integrations_do_not_claim_connected(server_module):
    integrations = server_module.list_integrations()
    assert integrations
    assert all(item["connected"] is False for item in integrations)
    assert all("credential_presence" in item for item in integrations)


def test_audit_chain_is_written(server_module):
    server_module._audit("test", "pytest", "resource-1", "ok", {"safe": True})
    events = server_module.recent_audit_events(5)
    assert len(events) == 1
    assert events[0]["event_hash"]
    assert events[0]["details"] == {"safe": True}
