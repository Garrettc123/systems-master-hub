import sqlite3

from fastapi.testclient import TestClient

from app.backup import create_backup, restore_backup, verify_backup
from app.ledger import EventLedger
from app.main import create_app
from app.worker import process_one

TOKEN = "t" * 64


def make_client(tmp_path, token=TOKEN):
    path = tmp_path / "events.sqlite3"
    app = create_app(ledger_path=str(path), operator_token=token)
    return TestClient(app), path, app.state.ledger


def headers():
    return {"Authorization": f"Bearer {TOKEN}"}


def plan_payload(**overrides):
    payload = {"target": "staging/web", "artifact_digest": "sha256:" + "a" * 64,
               "change_summary": "Canary plan only", "dry_run": True}
    payload.update(overrides)
    return payload


def test_health_and_readiness(tmp_path):
    client, _, _ = make_client(tmp_path)
    assert client.get("/healthz").status_code == 200
    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json()["integrity"] == "valid"


def test_management_requires_auth(tmp_path):
    client, _, _ = make_client(tmp_path)
    assert client.get("/v1/status").status_code == 401


def test_missing_or_weak_operator_token_fails_closed(tmp_path):
    client, _, _ = make_client(tmp_path, token="too-short")
    assert client.get("/v1/status").status_code == 503


def test_non_ascii_bearer_token_is_rejected_without_server_error(tmp_path):
    client, _, _ = make_client(tmp_path)
    assert client.get("/v1/status", headers={b"authorization": b"Bearer \xff"}).status_code == 403


def test_dry_run_plan_is_recorded_and_chain_verifies(tmp_path):
    client, _, _ = make_client(tmp_path)
    response = client.post("/v1/plans", headers=headers(), json=plan_payload())
    assert response.status_code == 202
    assert response.json()["execution_started"] is False
    verification = client.get("/v1/ledger/verify", headers=headers())
    assert verification.status_code == 200
    assert verification.json()["valid"] is True
    assert verification.json()["checked"] == 1


def test_live_plan_and_execution_are_blocked(tmp_path):
    client, _, _ = make_client(tmp_path)
    assert client.post("/v1/plans", headers=headers(), json=plan_payload(dry_run=False)).status_code == 409
    assert client.post("/v1/deployments/execute", headers=headers(), json={}).status_code == 423


def test_invalid_digest_is_rejected(tmp_path):
    client, _, _ = make_client(tmp_path)
    response = client.post("/v1/plans", headers=headers(), json=plan_payload(artifact_digest="not-a-digest"))
    assert response.status_code == 422


def test_job_idempotency_and_worker_completion(tmp_path):
    client, _, ledger = make_client(tmp_path)
    body = {"task_name": "ledger.verify", "idempotency_key": "safe-test-job-000001", "dry_run": True}
    first = client.post("/v1/jobs", headers=headers(), json=body)
    second = client.post("/v1/jobs", headers=headers(), json=body)
    assert first.status_code == second.status_code == 202
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert first.json()["job"]["job_id"] == second.json()["job"]["job_id"]
    assert process_one(ledger, "test-worker") is True
    current = client.get(f"/v1/jobs/{first.json()['job']['job_id']}", headers=headers()).json()["job"]
    assert current["status"] == "succeeded"
    assert ledger.verify()["checked"] == 3


def test_idempotency_key_cannot_change_request(tmp_path):
    client, _, _ = make_client(tmp_path)
    body = {"task_name": "ledger.verify", "idempotency_key": "safe-test-job-000002", "dry_run": True}
    assert client.post("/v1/jobs", headers=headers(), json=body).status_code == 202
    changed = {**body, "payload": {"untrusted": "different"}}
    assert client.post("/v1/jobs", headers=headers(), json=changed).status_code in (409, 422)


def test_unsupported_task_is_rejected(tmp_path):
    client, _, _ = make_client(tmp_path)
    body = {"task_name": "shell.exec", "idempotency_key": "safe-test-job-000003", "dry_run": True}
    assert client.post("/v1/jobs", headers=headers(), json=body).status_code == 422


def test_ledger_detects_payload_tampering(tmp_path):
    client, path, _ = make_client(tmp_path)
    assert client.post("/v1/plans", headers=headers(), json=plan_payload()).status_code == 202
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE events SET payload_json = '{}' WHERE seq = 1")
    assert client.get("/v1/ledger/verify", headers=headers()).json()["valid"] is False
    assert client.get("/readyz").status_code == 503


def test_ledger_can_be_reopened(tmp_path):
    path = str(tmp_path / "persistent.sqlite3")
    first = EventLedger(path)
    first.append("test.event", "test", {"ok": True})
    second = EventLedger(path)
    assert second.verify()["checked"] == 1


def test_backup_verify_and_restore(tmp_path):
    source = tmp_path / "source.sqlite3"
    ledger = EventLedger(str(source))
    ledger.append("test.event", "test", {"durable": True})
    backup, manifest = create_backup(source, tmp_path / "backups")
    assert verify_backup(backup, manifest)["valid"] is True
    restored = tmp_path / "restored.sqlite3"
    restore_backup(backup, restored, confirmed=True)
    assert EventLedger(str(restored)).verify()["checked"] == 1


def test_restore_requires_explicit_confirmation(tmp_path):
    source = tmp_path / "source.sqlite3"
    ledger = EventLedger(str(source))
    ledger.append("test.event", "test", {"durable": True})
    backup, _ = create_backup(source, tmp_path / "backups")
    try:
        restore_backup(backup, tmp_path / "restored.sqlite3", confirmed=False)
    except PermissionError:
        pass
    else:
        raise AssertionError("restore must require explicit confirmation")


def test_stale_worker_lease_is_reclaimed(tmp_path):
    ledger = EventLedger(str(tmp_path / "lease.sqlite3"))
    job, created, _ = ledger.enqueue("ledger.verify", "lease-test-job-000001", {})
    assert created is True
    first = ledger.claim_job("worker-crashed", lease_seconds=300)
    assert first is not None and first["attempt_count"] == 1
    conn = ledger.connect()
    try:
        conn.execute(
            "UPDATE jobs SET started_at='2000-01-01T00:00:00+00:00' WHERE job_id=?",
            (job["job_id"],),
        )
    finally:
        conn.close()
    recovered = ledger.claim_job("worker-recovery", lease_seconds=300)
    assert recovered is not None
    assert recovered["worker_id"] == "worker-recovery"
    assert recovered["attempt_count"] == 2
