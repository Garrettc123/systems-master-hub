from fastapi.testclient import TestClient

from revenue.garcar_core.app import app

client = TestClient(app)


def test_phone_status_never_returns_secret_values(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_USER_TOKEN", "example-value")
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    response = client.get("/api/phone/status")
    assert response.status_code == 200
    body = response.json()
    assert body["providers"]["slack"]["configured"] is True
    assert body["providers"]["github"]["configured"] is False
    assert "example-value" not in response.text


def test_bot_token_does_not_configure_slack_search(monkeypatch) -> None:
    monkeypatch.delenv("SLACK_USER_TOKEN", raising=False)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "example-value")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    response = client.get("/api/phone/status")
    assert response.status_code == 200
    assert response.json()["providers"]["slack"]["configured"] is False


def test_knowledge_search_fails_closed_without_provider_credentials(monkeypatch) -> None:
    for key in ("SLACK_USER_TOKEN", "SLACK_BOT_TOKEN", "GITHUB_TOKEN", "NOTION_API_KEY", "PERPLEXITY_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    response = client.post("/api/knowledge/search", json={"query": "test query"})
    assert response.status_code == 503


def test_phone_ui_is_served_by_same_app() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Garcar Command Center" in response.text
