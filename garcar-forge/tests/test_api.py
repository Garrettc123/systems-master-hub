import sqlite3

from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path, token="test-operator-token"):
    path = tmp_path / "events.sqlite3"
    app = create_app(ledger_path=str(path), operator_token=token)
    return TestClient(app), path


def headers():
    return {"Authorization": "Bearer test-operator-token"}


def plan_payload(**overrides):
    payload = {
        "target": "staging/web",
        "artifact_digest": "sha256:" + "a" * 64,
        "change_summary": "Canary plan only",
        "dry_run": True,
    }
    payload.update(overrides)
    return payload


def test_health_and_readiness(tmp_path):
    client, _ = make_client(tmp_path)
    assert client.get("/healthz").status_code == 200
    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json()["integrity"] == "valid"


def test_management_requires_auth(tmp_path):
    client, _ = make_client(tmp_path)
    assert client.get("/v1/status").status_code == 401


def test_missing_operator_token_fails_closed(tmp_path):
    client, _ = make_client(tmp_path, token="")
    response = client.get("/v1/status")
    assert response.status_code == 503


def test_dry_run_plan_is_recorded_and_chain_verifies(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.post("/v1/plans", headers=headers(), json=plan_payload())
    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["execution_started"] is False
    verification = client.get("/v1/ledger/verify", headers=headers())
    assert verification.status_code == 200
    assert verification.json()["valid"] is True
    assert verification.json()["checked"] == 1


def test_live_plan_is_rejected(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.post(
        "/v1/plans", headers=headers(), json=plan_payload(dry_run=False)
    )
    assert response.status_code == 409


def test_malformed_artifact_digest_is_rejected(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.post(
        "/v1/plans", headers=headers(), json=plan_payload(artifact_digest="not-a-digest")
    )
    assert response.status_code == 422


def test_execution_is_locked_even_for_operator(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.post(
        "/v1/deployments/execute", headers=headers(), json={"plan_id": "anything"}
    )
    assert response.status_code == 423


def test_ledger_detects_payload_tampering(tmp_path):
    client, path = make_client(tmp_path)
    response = client.post("/v1/plans", headers=headers(), json=plan_payload())
    assert response.status_code == 202
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE events SET payload_json = '{}' WHERE seq = 1")
    verification = client.get("/v1/ledger/verify", headers=headers())
    assert verification.status_code == 200
    assert verification.json()["valid"] is False
    assert client.get("/readyz").status_code == 503
