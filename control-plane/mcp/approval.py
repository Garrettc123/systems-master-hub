"""Action-bound human approval verification with replay prevention."""
from __future__ import annotations
import base64, hashlib, hmac, json, os, time
from pathlib import Path
from typing import Any

KEY = os.environ.get("MCP_APPROVAL_SIGNING_KEY", "").encode()
REPLAY_FILE = Path(os.environ.get("MCP_APPROVAL_REPLAY_FILE", "/tmp/garcar-mcp-approval-replay.json"))


def canonical_digest(repository: str, server: str, tool: str, arguments: dict[str, Any]) -> str:
    payload = json.dumps({"repository": repository, "server": server, "tool": tool, "arguments": arguments}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _used() -> set[str]:
    try:
        return set(json.loads(REPLAY_FILE.read_text()))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def verify_approval(token: str | None, repository: str, server: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if not KEY or not token:
        raise ValueError("human approval required")
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid approval")
    signed = f"{parts[0]}.{parts[1]}".encode()
    expected = hmac.new(KEY, signed, hashlib.sha256).digest()
    try:
        signature = _decode(parts[2]); claims = json.loads(_decode(parts[1]))
    except Exception as exc:
        raise ValueError("invalid approval") from exc
    if not hmac.compare_digest(signature, expected):
        raise ValueError("invalid approval")
    now = int(time.time())
    if claims.get("exp", 0) <= now or claims.get("iat", now) > now + 30:
        raise ValueError("approval expired")
    if not claims.get("actor") or not claims.get("jti"):
        raise ValueError("approval actor missing")
    if claims.get("digest") != canonical_digest(repository, server, tool, arguments):
        raise ValueError("approval does not match action")
    used = _used()
    if claims["jti"] in used:
        raise ValueError("approval already used")
    used.add(claims["jti"])
    REPLAY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPLAY_FILE.write_text(json.dumps(sorted(used)))
    return claims
