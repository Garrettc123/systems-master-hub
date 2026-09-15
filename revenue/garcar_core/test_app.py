from fastapi.testclient import TestClient

from revenue.garcar_core.app import app

client = TestClient(app)

BASE_EVENT = {
    "event_id": "evt_123",
    "tenant_id": "tenant_demo",
    "source": "web_form",
    "occurred_at": "2026-09-15T19:00:00Z",
    "customer": {"name": "Jane Doe", "phone": "+1-817-555-0100"},
    "request": {"service": "AC repair", "city": "Cleburne", "urgency": "today"},
}


def test_health() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_idempotent_ingestion() -> None:
    first = client.post(
        "/v1/events/lead",
        headers={"Idempotency-Key": "same-key"},
        json=BASE_EVENT,
    )
    second = client.post(
        "/v1/events/lead",
        headers={"Idempotency-Key": "same-key"},
        json=BASE_EVENT,
    )
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["lead_id"] == second.json()["lead_id"]


def test_missing_idempotency_key_rejected() -> None:
    response = client.post("/v1/events/lead", json=BASE_EVENT)
    assert response.status_code == 400


def test_sensitive_notes_are_blocked() -> None:
    payload = {**BASE_EVENT, "event_id": "evt_124"}
    payload["request"] = {
        **BASE_EVENT["request"],
        "notes": "Customer included SSN 123-45-6789",
    }
    response = client.post(
        "/v1/events/lead",
        headers={"Idempotency-Key": "sensitive"},
        json=payload,
    )
    assert response.status_code == 202
    assert response.json()["status"] == "blocked"
    assert response.json()["policy"] == "BLOCK_SENSITIVE_DATA"


def test_no_contact_method_escalates() -> None:
    payload = {**BASE_EVENT, "event_id": "evt_125"}
    payload["customer"] = {"name": "No Contact"}
    response = client.post(
        "/v1/events/lead",
        headers={"Idempotency-Key": "no-contact"},
        json=payload,
    )
    assert response.status_code == 202
    assert response.json()["status"] == "escalated"
