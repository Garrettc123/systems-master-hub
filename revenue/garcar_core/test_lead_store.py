import importlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from revenue.garcar_core.lead_store import IdempotencyConflict, LeadStore
from revenue.garcar_core.test_app import BASE_EVENT


def test_persistent_lead_is_reused_after_reopening(tmp_path):
    target = tmp_path / "private/leads.sqlite3"
    first = LeadStore(str(target))
    record = first.ingest("garcar-canary", "durable-request", "digest", lambda: {"lead_id": "durable-lead"})
    second = LeadStore(str(target))
    def unexpected():
        raise AssertionError("Persisted event was recreated")
    assert second.ingest("garcar-canary", "durable-request", "digest", unexpected) == record
    assert second.mode == "sqlite_wal"
    assert target.stat().st_mode & 0o777 == 0o600


def test_concurrent_lead_retries_create_one_persisted_record(tmp_path):
    stores = [LeadStore(str(tmp_path / "leads.sqlite3")) for _ in range(8)]
    def submit(store):
        return store.ingest("garcar-canary", "concurrent", "digest", lambda: {"lead_id": "concurrent-lead"})
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(submit, stores))
    assert all(result == {"lead_id": "concurrent-lead"} for result in results)
    with sqlite3.connect(tmp_path / "leads.sqlite3") as db:
        assert db.execute("SELECT count(*) FROM lead_events").fetchone()[0] == 1


def test_reused_key_cannot_change_payload_and_is_tenant_scoped(tmp_path):
    store = LeadStore(str(tmp_path / "leads.sqlite3"))
    store.ingest("first-tenant", "same-key", "digest-one", lambda: {"lead_id": "first"})
    with pytest.raises(IdempotencyConflict):
        store.ingest("first-tenant", "same-key", "digest-two", lambda: {"lead_id": "replaced"})
    assert store.ingest("second-tenant", "same-key", "digest-two", lambda: {"lead_id": "second"})["lead_id"] == "second"


def test_failed_creation_does_not_leave_an_idempotency_record(tmp_path):
    store = LeadStore(str(tmp_path / "leads.sqlite3"))
    def failed():
        raise ValueError("expected failed creation")
    with pytest.raises(ValueError):
        store.ingest("garcar-canary", "rollback", "digest", failed)
    assert store.ingest("garcar-canary", "rollback", "digest", lambda: {"lead_id": "retried"})["lead_id"] == "retried"


def test_api_returns_conflict_when_key_is_reused_for_another_lead(monkeypatch, tmp_path):
    module = importlib.import_module("revenue.garcar_core.app")
    monkeypatch.setattr(module, "store", LeadStore(str(tmp_path / "leads.sqlite3")))
    client = TestClient(module.app)
    headers = {"Idempotency-Key": "api-conflict-check"}
    assert client.post("/v1/events/lead", json=BASE_EVENT, headers=headers).status_code == 202
    changed = {**BASE_EVENT, "request": {**BASE_EVENT["request"], "service": "Different service"}}
    assert client.post("/v1/events/lead", json=changed, headers=headers).status_code == 409


def test_sensitive_notes_are_not_persisted_or_returned(monkeypatch, tmp_path):
    module = importlib.import_module("revenue.garcar_core.app")
    target = tmp_path / "leads.sqlite3"
    monkeypatch.setattr(module, "store", LeadStore(str(target)))
    client = TestClient(module.app)
    event = {**BASE_EVENT, "request": {**BASE_EVENT["request"], "notes": "ssn 123-45-6789"}}
    response = client.post("/v1/events/lead", json=event, headers={"Idempotency-Key": "sensitive-store-check"})
    assert response.status_code == 202
    assert response.json()["status"] == "blocked"
    assert "123-45-6789" not in response.text
    with sqlite3.connect(target) as db:
        assert "123-45-6789" not in db.execute("SELECT lead_json FROM lead_events").fetchone()[0]
