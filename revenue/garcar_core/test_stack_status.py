import httpx
from fastapi.testclient import TestClient

from revenue.garcar_core import stack_status
from revenue.garcar_core.app import app

client = TestClient(app)


def configure(monkeypatch, handler):
    for name in ("GARCAR_OPERATOR_TOKEN", "GARCAR_ACTIONS_TOKEN"):
        monkeypatch.setenv(name, "local-test-credential-" + "a" * 40)
    monkeypatch.setenv("GARCAR_FORGE_URL", "http://127.0.0.1:18789")
    monkeypatch.setenv("GARCAR_ACTIONS_URL", "http://127.0.0.1:18788")
    original = httpx.AsyncClient
    monkeypatch.setattr(stack_status.httpx, "AsyncClient",
                        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))


def test_status_whitelists_fields_and_preserves_server_credentials(monkeypatch):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"version": "0.2.0", "ledger": {"valid": True},
                                        "audit": {"valid": True}, "execution_enabled": False,
                                        "queue": {"queued": 1, "running": 0},
                                        "debug_token": "local-test-credential-" + "a" * 40})
    configure(monkeypatch, handler)
    response = client.get("/api/stack/status")
    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["services"]["actions"]["queue"]["queued"] == 1
    assert "local-test-credential" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert len(requests) == 2
    assert all(request.headers["Authorization"].startswith("Bearer ") for request in requests)


def test_status_rejects_non_loopback_urls_without_network_access(monkeypatch):
    configure(monkeypatch, lambda request: (_ for _ in ()).throw(AssertionError("unexpected request")))
    monkeypatch.setenv("GARCAR_FORGE_URL", "http://169.254.169.254:80")
    monkeypatch.setenv("GARCAR_ACTIONS_URL", "https://example.com:443")
    body = client.get("/api/stack/status").json()
    assert body["ready"] is False
    assert all(row["state"] == "invalid_local_url" for row in body["services"].values())


def test_status_fails_closed_when_credentials_are_missing(monkeypatch):
    configure(monkeypatch, lambda request: (_ for _ in ()).throw(AssertionError("unexpected request")))
    monkeypatch.delenv("GARCAR_OPERATOR_TOKEN")
    monkeypatch.delenv("GARCAR_ACTIONS_TOKEN")
    body = client.get("/api/stack/status").json()
    assert body["ready"] is False
    assert all(row["state"] == "not_configured" for row in body["services"].values())


def test_status_does_not_follow_redirects(monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={"location": "https://example.com"})
    configure(monkeypatch, handler)
    body = client.get("/api/stack/status").json()
    assert body["ready"] is False
    assert len(calls) == 2
    assert all(row["state"] == "unavailable" for row in body["services"].values())


def test_status_reports_audit_failure_and_authentication_failure(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"ledger": {"valid": False}}) if request.url.port == 18789 else httpx.Response(401)
    configure(monkeypatch, handler)
    body = client.get("/api/stack/status").json()
    assert body["ready"] is False
    assert body["services"]["forge"]["state"] == "integrity_failed"
    assert body["services"]["actions"]["state"] == "authentication_failed"


def test_status_handles_unavailable_services_without_returning_errors(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("private upstream detail", request=request)
    configure(monkeypatch, handler)
    response = client.get("/api/stack/status")
    assert "private upstream detail" not in response.text
    assert response.json()["ready"] is False
    assert all(row["state"] == "unreachable" for row in response.json()["services"].values())
