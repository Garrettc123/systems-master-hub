from fastapi.testclient import TestClient

from revenue.garcar_core.app import app

client = TestClient(app)


def test_phone_status_never_returns_secret_values(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "not-a-real-token")
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    response = client.get("/api/phone/status")
    assert response.status_code == 200
    body = response.json()
    assert body["providers"]["slack"]["configured"] is True
    assert body["providers"]["notion"]["configured"] is False
    assert "not-a-real-token" not in response.text


def test_knowledge_search_fails_closed_without_provider_credentials(monkeypatch) -> None:
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    response = client.post("/api/knowledge/search", json={"query": "test query"})
    assert response.status_code == 503


def test_phone_ui_is_served_by_same_app() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Garcar Command Center" in response.text
