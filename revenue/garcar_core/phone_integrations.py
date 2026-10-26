"""Read-only server-side adapters for the Garcar phone command center.

The app must remain behind Vercel Deployment Protection (SSO) on every hostname.
Provider credentials are read only from server environment variables. No write
operations are exposed by this module.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api", tags=["phone-integrations"])
TIMEOUT = httpx.Timeout(12.0, connect=4.0)


class KnowledgeQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=800)


def integration_status() -> dict[str, Any]:
    """Report configuration presence only, never token values."""
    # Slack's search.messages API requires a user token with search:read.
    # A bot token is not sufficient for this endpoint.
    configured = {
        "slack": bool(os.getenv("SLACK_USER_TOKEN")),
        "notion": bool(os.getenv("NOTION_API_KEY")),
        "perplexity": bool(os.getenv("PERPLEXITY_API_KEY")),
    }
    return {
        "providers": {
            name: {"configured": ready, "state": "configured" if ready else "needs_credentials"}
            for name, ready in configured.items()
        },
        "configured_count": sum(configured.values()),
        "provider_count": len(configured),
        "mode": "read_only",
    }


@router.get("/phone/status")
async def phone_status() -> dict[str, Any]:
    return integration_status()


async def _slack_search(client: httpx.AsyncClient, query: str) -> dict[str, Any]:
    token = os.getenv("SLACK_USER_TOKEN")
    if not token:
        return {"provider": "slack", "state": "not_configured", "results": []}
    response = await client.get(
        "https://slack.com/api/search.messages",
        headers={"Authorization": f"Bearer {token}"},
        params={"query": query, "count": 5, "highlight": False},
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        return {"provider": "slack", "state": "provider_error", "results": []}
    results = []
    for item in (data.get("messages") or {}).get("matches", [])[:5]:
        results.append({
            "title": f"Slack · #{(item.get('channel') or {}).get('name', 'channel')}",
            "text": str(item.get("text", ""))[:1600],
            "url": item.get("permalink"),
        })
    return {"provider": "slack", "state": "connected", "results": results}


async def _notion_search(client: httpx.AsyncClient, query: str) -> dict[str, Any]:
    token = os.getenv("NOTION_API_KEY")
    if not token:
        return {"provider": "notion", "state": "not_configured", "results": []}
    response = await client.post(
        "https://api.notion.com/v1/search",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        json={"query": query, "page_size": 5},
    )
    response.raise_for_status()
    data = response.json()
    results = []
    for item in data.get("results", [])[:5]:
        props = item.get("properties") or {}
        title = ""
        for value in props.values():
            if isinstance(value, dict) and value.get("type") == "title":
                title = "".join(part.get("plain_text", "") for part in value.get("title", []))
                break
        # Database/data-source search responses may expose title at top level.
        if not title:
            top_level_title = item.get("title")
            if isinstance(top_level_title, list):
                title = "".join(part.get("plain_text", "") for part in top_level_title)
        results.append({
            "title": title or "Notion page",
            "text": "Notion page match",
            "url": item.get("url"),
        })
    return {"provider": "notion", "state": "connected", "results": results}


async def _perplexity_search(client: httpx.AsyncClient, query: str) -> dict[str, Any]:
    token = os.getenv("PERPLEXITY_API_KEY")
    if not token:
        return {"provider": "perplexity", "state": "not_configured", "results": []}
    response = await client.post(
        "https://api.perplexity.ai/chat/completions",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "model": os.getenv("PERPLEXITY_MODEL", "sonar"),
            "messages": [
                {"role": "system", "content": "Answer using current, relevant web evidence. Be concise, distinguish evidence from inference, and include source URLs when available."},
                {"role": "user", "content": query},
            ],
            "max_tokens": 700,
        },
    )
    response.raise_for_status()
    data = response.json()
    message = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
    citations = data.get("citations") or []
    results = [{"title": "Perplexity research", "text": str(message)[:6000], "url": None}]
    results.extend({"title": "Research source", "text": url, "url": url} for url in citations[:8])
    return {"provider": "perplexity", "state": "connected", "results": results}


@router.post("/knowledge/search")
async def knowledge_search(request: KnowledgeQuery) -> dict[str, Any]:
    """Search configured providers in read-only mode; partial results are allowed."""
    query = request.query.strip()
    if len(query) < 2:
        raise HTTPException(status_code=422, detail="Query must contain at least two characters")
    status = integration_status()
    if status["configured_count"] == 0:
        raise HTTPException(
            status_code=503,
            detail="No knowledge providers are configured on the server. Add authorized provider credentials to the server secret store.",
        )

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
        tasks = [
            _slack_search(client, query),
            _notion_search(client, query),
            _perplexity_search(client, query),
        ]
        raw = await asyncio.gather(*tasks, return_exceptions=True)

    providers: list[dict[str, Any]] = []
    for name, item in zip(("slack", "notion", "perplexity"), raw):
        if isinstance(item, BaseException):
            # Do not expose provider response bodies, headers, or credentials.
            providers.append({"provider": name, "state": "request_failed", "results": []})
        else:
            providers.append(item)

    return {
        "query": query,
        "mode": "read_only",
        "providers": providers,
        "results": [result for provider in providers for result in provider["results"]],
        "partial": any(provider["state"] not in ("connected", "not_configured") for provider in providers),
    }
