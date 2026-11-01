from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path):
    app = create_app(
        ledger_path=str(tmp_path / "events.sqlite3"),
        operator_token="test-operator-token",
    )
    return TestClient(app)


def headers():
    return {"Authorization": "Bearer test-operator-token"}


def test_health_and_readiness(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/healthz").status_code == 200
    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json()["ledger"] == "reachable"


def test_management_requires_auth(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/v1/status").status_code == 401


def test_dry_run_plan_is_recorded_and_chain_verifies(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/v1/plans",
        headers=headers(),
        json={
            "target": "staging/web",
            "artifact_digest": "sha256:" + "a" * 64,
            "change_summary": "Canary plan only",
            "dry_run": True,
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["execution_started"] is False
    verification = client.get("/v1/ledger/verify", headers=headers())
    assert verification.status_code == 200
    assert verification.json()["valid"] is True
    assert verification.json()["checked"] == 1


def test_live_plan_is_rejected(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/v1/plans",
        headers=headers(),
        json={
            "target": "production/web",
            "artifact_digest": "sha256:" + "b" * 64,
            "change_summary": "Must not execute",
            "dry_run": False,
        },
    )
    assert response.status_code == 409


def test_execution_is_locked_even_for_operator(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/v1/deployments/execute",
        headers=headers(),
        json={"plan_id": "anything"},
    )
    assert response.status_code == 423
