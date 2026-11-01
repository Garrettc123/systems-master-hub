from __future__ import annotations

import hmac
import os
import sqlite3
import uuid
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.ledger import EventLedger


class DeploymentPlan(BaseModel):
    target: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9._/-]+$")
    artifact_digest: str = Field(pattern=r"^sha256:[a-fA-F0-9]{64}$")
    change_summary: str = Field(min_length=1, max_length=2000)
    dry_run: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


def create_app(ledger_path: str | None = None, operator_token: str | None = None) -> FastAPI:
    path = ledger_path or os.getenv("GARCAR_LEDGER_PATH", "./data/garcar-forge.sqlite3")
    token = operator_token if operator_token is not None else os.getenv("GARCAR_OPERATOR_TOKEN", "")
    ledger = EventLedger(path)

    app = FastAPI(
        title="Garcar Forge Control Plane",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.ledger = ledger

    def require_operator(authorization: str | None = Header(default=None)) -> str:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="operator_auth_not_configured",
            )
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="operator_auth_required")
        supplied = authorization.removeprefix("Bearer ").strip()
        if not hmac.compare_digest(supplied, token):
            raise HTTPException(status_code=403, detail="operator_auth_rejected")
        return "operator"

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "alive", "service": "garcar-forge-control-plane"}

    @app.get("/readyz")
    def ready() -> dict[str, str]:
        try:
            verification = ledger.verify()
            if not verification["valid"]:
                raise HTTPException(status_code=503, detail="ledger_integrity_check_failed")
            with sqlite3.connect(path, timeout=2) as conn:
                conn.execute("SELECT 1").fetchone()
            return {"status": "ready", "ledger": "reachable", "integrity": "valid"}
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=503, detail="ledger_unavailable") from exc

    @app.get("/v1/status")
    def status_view(_: str = Depends(require_operator)) -> dict[str, Any]:
        return {
            "service": "garcar-forge-control-plane",
            "version": app.version,
            "ledger": ledger.verify(),
            "execution_enabled": False,
            "deployment_mode": "dry_run_only",
        }

    @app.post("/v1/plans", status_code=202)
    def create_plan(
        plan: DeploymentPlan,
        request: Request,
        actor: str = Depends(require_operator),
    ) -> dict[str, Any]:
        if not plan.dry_run:
            raise HTTPException(status_code=409, detail="live_plans_are_disabled")
        plan_id = str(uuid.uuid4())
        event = ledger.append(
            "deployment.plan.created",
            actor,
            {
                "plan_id": plan_id,
                "target": plan.target,
                "artifact_digest": plan.artifact_digest,
                "change_summary": plan.change_summary,
                "dry_run": True,
                "metadata": plan.metadata,
                "request_id": request.headers.get("x-request-id"),
            },
        )
        return {
            "accepted": True,
            "plan_id": plan_id,
            "dry_run": True,
            "event_sequence": event["seq"],
            "event_hash": event["event_hash"],
            "execution_started": False,
        }

    @app.post("/v1/deployments/execute")
    def execute_deployment(
        _: dict[str, Any],
        actor: str = Depends(require_operator),
    ) -> None:
        raise HTTPException(status_code=423, detail="execution_locked_by_platform_policy")

    @app.get("/v1/ledger/verify")
    def verify_ledger(_: str = Depends(require_operator)) -> dict[str, Any]:
        return ledger.verify()

    @app.get("/v1/ledger/events")
    def ledger_events(limit: int = 50, _: str = Depends(require_operator)) -> dict[str, Any]:
        return {"events": ledger.recent(limit)}

    return app


app = create_app()
