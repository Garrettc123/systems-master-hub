"""Fail-closed MCP control plane for Garcar Enterprise.

This server intentionally ships with no generic shell, SQL, URL-fetch, or
arbitrary-write tool. External actions require a reviewed adapter implementation.
Run over stdio by default; do not expose an unauthenticated network listener.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Garcar Control Plane")

INTEGRATIONS: dict[str, dict[str, Any]] = {
    "github": {"secret_names": ["GITHUB_TOKEN", "GITHUB_PAT"], "mode": "read_only_until_adapter_reviewed"},
    "notion": {"secret_names": ["NOTION_API_KEY", "NOTION_MCP_TOKEN"], "mode": "read_only_until_adapter_reviewed"},
    "linear": {"secret_names": ["LINEAR_API_KEY"], "mode": "read_only_until_adapter_reviewed"},
    "stripe": {"secret_names": ["STRIPE_SECRET_KEY", "STRIPE_RESTRICTED_KEY"], "mode": "read_only_until_adapter_reviewed"},
    "hubspot": {"secret_names": ["HUBSPOT_ACCESS_TOKEN"], "mode": "read_only_until_adapter_reviewed"},
    "supabase": {"secret_names": ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"], "mode": "read_only_until_adapter_reviewed"},
    "vercel": {"secret_names": ["VERCEL_TOKEN"], "mode": "read_only_until_adapter_reviewed"},
    "sendgrid": {"secret_names": ["SENDGRID_API_KEY"], "mode": "approval_required_adapter_not_registered"},
    "vault": {"secret_names": ["VAULT_ADDR", "VAULT_TOKEN"], "mode": "secret_source_not_read_by_mcp"},
}

ACTION_POLICY: dict[str, dict[str, Any]] = {
    "github.read": {"risk": "low", "approval_required": False, "registered": False},
    "notion.read": {"risk": "low", "approval_required": False, "registered": False},
    "linear.read": {"risk": "low", "approval_required": False, "registered": False},
    "stripe.read": {"risk": "medium", "approval_required": True, "registered": False},
    "crm.email.send": {"risk": "high", "approval_required": True, "registered": False},
    "stripe.payment_link.create": {"risk": "high", "approval_required": True, "registered": False},
    "github.write": {"risk": "high", "approval_required": True, "registered": False},
    "deployment.execute": {"risk": "critical", "approval_required": True, "registered": False},
}

DB_PATH = Path(os.environ.get("GARCAR_MCP_DB", "./data/garcar_mcp.sqlite3")).expanduser()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS approvals (
      request_id TEXT PRIMARY KEY,
      action_id TEXT NOT NULL,
      summary TEXT NOT NULL,
      evidence_refs_json TEXT NOT NULL,
      status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected','executed','blocked')),
      requested_at INTEGER NOT NULL,
      approved_at INTEGER,
      executed_at INTEGER,
      decision_note TEXT
    );
    CREATE TABLE IF NOT EXISTS audit_events (
      event_id TEXT PRIMARY KEY,
      timestamp INTEGER NOT NULL,
      event_type TEXT NOT NULL,
      actor TEXT NOT NULL,
      resource_id TEXT,
      outcome TEXT NOT NULL,
      details_json TEXT NOT NULL,
      previous_hash TEXT,
      event_hash TEXT NOT NULL
    );
    """)
    return conn


def _audit(event_type: str, actor: str, resource_id: str | None, outcome: str, details: dict[str, Any]) -> None:
    """Append a hash-linked audit event; never store credential values."""
    safe_details = json.dumps(details, sort_keys=True, separators=(",", ":"))
    with _connect() as conn:
        previous = conn.execute("SELECT event_hash FROM audit_events ORDER BY timestamp DESC, rowid DESC LIMIT 1").fetchone()
        previous_hash = previous["event_hash"] if previous else None
        timestamp = int(time.time())
        event_id = str(uuid.uuid4())
        canonical = json.dumps({
            "event_id": event_id, "timestamp": timestamp, "event_type": event_type,
            "actor": actor, "resource_id": resource_id, "outcome": outcome,
            "details_json": safe_details, "previous_hash": previous_hash,
        }, sort_keys=True, separators=(",", ":"))
        event_hash = hashlib.sha256(canonical.encode()).hexdigest()
        conn.execute(
            """INSERT INTO audit_events
            (event_id,timestamp,event_type,actor,resource_id,outcome,details_json,previous_hash,event_hash)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (event_id, timestamp, event_type, actor, resource_id, outcome, safe_details, previous_hash, event_hash),
        )


def _safe_env_presence(names: list[str]) -> dict[str, bool]:
    return {name: bool(os.environ.get(name)) for name in names}


@mcp.tool()
def control_plane_status() -> dict[str, Any]:
    """Return MCP process status, policy posture, and local ledger readiness."""
    with _connect() as conn:
        approvals = conn.execute("SELECT status, COUNT(*) AS count FROM approvals GROUP BY status").fetchall()
        audit_count = conn.execute("SELECT COUNT(*) AS count FROM audit_events").fetchone()["count"]
    return {
        "service": "garcar-control-plane-mcp",
        "status": "ready",
        "transport": "stdio",
        "external_actions_enabled": False,
        "policy": "fail_closed",
        "database_path": str(DB_PATH),
        "approval_counts": {row["status"]: row["count"] for row in approvals},
        "audit_event_count": audit_count,
        "note": "Process readiness is not proof that external integrations or production workflows are connected.",
    }


@mcp.tool()
def list_integrations() -> list[dict[str, Any]]:
    """List allowlisted integrations and report credential presence only, never values."""
    result = []
    for name, config in INTEGRATIONS.items():
        presence = _safe_env_presence(config["secret_names"])
        result.append({
            "name": name,
            "mode": config["mode"],
            "configured": any(presence.values()),
            "credential_presence": presence,
            "connected": False,
            "note": "Credential presence does not prove authentication or API connectivity.",
        })
    return result


@mcp.tool()
def evaluate_action_policy(action_id: str, evidence_refs: list[str] | None = None) -> dict[str, Any]:
    """Evaluate a proposed action without executing it; missing evidence fails closed."""
    policy = ACTION_POLICY.get(action_id)
    evidence = [ref.strip() for ref in (evidence_refs or []) if isinstance(ref, str) and ref.strip()]
    if policy is None:
        return {"allowed": False, "reason": "action_not_allowlisted", "action_id": action_id}
    missing_evidence = not evidence
    registered = bool(policy["registered"])
    allowed = registered and not missing_evidence and not policy["approval_required"]
    return {
        "action_id": action_id,
        "risk": policy["risk"],
        "approval_required": policy["approval_required"],
        "adapter_registered": registered,
        "evidence_count": len(evidence),
        "allowed_to_execute": allowed,
        "reason": "adapter_not_registered" if not registered else ("evidence_required" if missing_evidence else "approval_required"),
    }


@mcp.tool()
def request_action(action_id: str, summary: str, evidence_refs: list[str]) -> dict[str, Any]:
    """Create a durable approval request. This does not execute the proposed action."""
    policy = ACTION_POLICY.get(action_id)
    summary = summary.strip() if isinstance(summary, str) else ""
    evidence = [ref.strip() for ref in evidence_refs if isinstance(ref, str) and ref.strip()]
    if policy is None:
        return {"created": False, "reason": "action_not_allowlisted"}
    if len(summary) < 8 or len(summary) > 1000:
        return {"created": False, "reason": "summary_must_be_8_to_1000_characters"}
    if not evidence:
        _audit("approval_request", "mcp-client", None, "blocked", {"action_id": action_id, "reason": "missing_evidence"})
        return {"created": False, "reason": "evidence_required"}
    request_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            """INSERT INTO approvals
            (request_id,action_id,summary,evidence_refs_json,status,requested_at)
            VALUES (?,?,?,?,?,?)""",
            (request_id, action_id, summary, json.dumps(evidence), "pending", int(time.time())),
        )
    _audit("approval_request", "mcp-client", request_id, "pending", {
        "action_id": action_id, "risk": policy["risk"], "evidence_count": len(evidence)
    })
    return {
        "created": True, "request_id": request_id, "status": "pending",
        "action_id": action_id, "risk": policy["risk"],
        "approval_required": policy["approval_required"],
        "message": "Request recorded only. No external action has been executed.",
    }


@mcp.tool()
def decide_action(request_id: str, decision: str, operator_token: str, note: str = "") -> dict[str, Any]:
    """Approve or reject a pending request using GARCAR_OPERATOR_APPROVAL_TOKEN."""
    expected = os.environ.get("GARCAR_OPERATOR_APPROVAL_TOKEN", "")
    if not expected:
        return {"decided": False, "reason": "operator_approval_token_not_configured"}
    if not hmac.compare_digest(expected, operator_token or ""):
        _audit("approval_decision", "unknown", request_id, "denied", {"reason": "invalid_operator_token"})
        return {"decided": False, "reason": "invalid_operator_token"}
    if decision not in {"approve", "reject"}:
        return {"decided": False, "reason": "decision_must_be_approve_or_reject"}
    with _connect() as conn:
        row = conn.execute("SELECT * FROM approvals WHERE request_id=?", (request_id,)).fetchone()
        if not row:
            return {"decided": False, "reason": "request_not_found"}
        if row["status"] != "pending":
            return {"decided": False, "reason": "request_not_pending", "status": row["status"]}
        new_status = "approved" if decision == "approve" else "rejected"
        conn.execute(
            "UPDATE approvals SET status=?,approved_at=?,decision_note=? WHERE request_id=? AND status='pending'",
            (new_status, int(time.time()), note[:500], request_id),
        )
    _audit("approval_decision", "operator", request_id, new_status, {"note": note[:500]})
    return {
        "decided": True, "request_id": request_id, "status": new_status,
        "message": "Approval authorizes review only; it does not enable an unregistered adapter or execute an action.",
    }


@mcp.tool()
def get_action_request(request_id: str) -> dict[str, Any]:
    """Inspect a request without exposing secrets."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM approvals WHERE request_id=?", (request_id,)).fetchone()
    if not row:
        return {"found": False}
    return {
        "found": True, "request_id": row["request_id"], "action_id": row["action_id"],
        "summary": row["summary"], "evidence_refs": json.loads(row["evidence_refs_json"]),
        "status": row["status"], "requested_at": row["requested_at"],
        "approved_at": row["approved_at"], "executed_at": row["executed_at"],
        "decision_note": row["decision_note"],
    }


@mcp.tool()
def recent_audit_events(limit: int = 20) -> list[dict[str, Any]]:
    """Read recent append-only audit events; limit is clamped to 1..100."""
    limit = max(1, min(int(limit), 100))
    with _connect() as conn:
        rows = conn.execute(
            "SELECT event_id,timestamp,event_type,actor,resource_id,outcome,details_json,previous_hash,event_hash "
            "FROM audit_events ORDER BY timestamp DESC,rowid DESC LIMIT ?", (limit,)
        ).fetchall()
    return [{
        "event_id": row["event_id"], "timestamp": row["timestamp"],
        "event_type": row["event_type"], "actor": row["actor"],
        "resource_id": row["resource_id"], "outcome": row["outcome"],
        "details": json.loads(row["details_json"]), "previous_hash": row["previous_hash"],
        "event_hash": row["event_hash"],
    } for row in rows]


@mcp.tool()
def execute_action(request_id: str) -> dict[str, Any]:
    """Fail-closed execution entrypoint; no external adapter is enabled in this release."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM approvals WHERE request_id=?", (request_id,)).fetchone()
        if not row:
            return {"executed": False, "reason": "request_not_found"}
        policy = ACTION_POLICY.get(row["action_id"], {})
        if row["status"] != "approved":
            return {"executed": False, "reason": "explicit_approval_required", "status": row["status"]}
        if not policy.get("registered", False):
            _audit("action_execution", "mcp-client", request_id, "blocked", {
                "action_id": row["action_id"], "reason": "adapter_not_registered"
            })
            conn.execute("UPDATE approvals SET status='blocked' WHERE request_id=? AND status='approved'", (request_id,))
            return {"executed": False, "reason": "adapter_not_registered", "status": "blocked"}
    return {"executed": False, "reason": "no_execution_handler_registered"}


def main() -> None:
    """Start the MCP server over stdio, the safe local default."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
