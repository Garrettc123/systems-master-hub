"""Read-only local service status for the phone console; never proxy actions."""
import asyncio
import os
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Response

router = APIRouter(prefix="/api/stack", tags=["local-stack"])


def local_url(value):
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or
                parsed.username or parsed.password or parsed.path not in ("", "/") or
                parsed.query or parsed.fragment or parsed.port is None):
            raise ValueError("Local status requires a literal loopback HTTP service URL")
        return value.rstrip("/")
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid local service URL") from exc


async def read_status(client, name, url_name, token_name):
    value, token = os.getenv(url_name, ""), os.getenv(token_name, "")
    if not value or len(token) < 32:
        return name, {"state": "not_configured", "ready": False}
    try:
        url = local_url(value)
    except ValueError:
        return name, {"state": "invalid_local_url", "ready": False}
    try:
        response = await client.get(url + "/v1/status", headers={"Authorization": "Bearer " + token})
        if response.status_code in (401, 403):
            return name, {"state": "authentication_failed", "ready": False}
        if response.status_code != 200:
            return name, {"state": "unavailable", "ready": False}
        body = response.json()
        if not isinstance(body, dict):
            raise TypeError("Invalid service status")
        audit = body.get("ledger" if name == "forge" else "audit")
        valid = isinstance(audit, dict) and audit.get("valid") is True
        # Whitelist fields; neither upstream errors nor environment values cross this boundary.
        result = {"state": "ready" if valid else "integrity_failed", "ready": valid,
                  "audit_valid": valid, "version": str(body.get("version", ""))[:40]}
        if name == "forge":
            result["execution_enabled"] = body.get("execution_enabled") is True
        else:
            queue = body.get("queue", {})
            result["queue"] = {key: queue.get(key, 0) if isinstance(queue.get(key, 0), int) else 0
                               for key in ("queued", "running", "succeeded", "failed")} if isinstance(queue, dict) else {}
        return name, result
    except (httpx.HTTPError, ValueError, TypeError):
        return name, {"state": "unreachable", "ready": False}


@router.get("/status")
async def stack_status(response: Response):
    response.headers["Cache-Control"] = "no-store"
    async with httpx.AsyncClient(timeout=2, follow_redirects=False, trust_env=False) as client:
        results = await asyncio.gather(
            read_status(client, "forge", "GARCAR_FORGE_URL", "GARCAR_OPERATOR_TOKEN"),
            read_status(client, "actions", "GARCAR_ACTIONS_URL", "GARCAR_ACTIONS_TOKEN"))
    services = dict(results)
    return {"mode": "local_read_only", "ready": all(row["ready"] for row in services.values()),
            "services": services}
