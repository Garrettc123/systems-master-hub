"""
Garcar Idempotency Framework
Supabase-backed. Atomic claim → process → mark.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from .models import NormalizedEvent


class IdempotencyStore:
    def __init__(self, supabase_client: Any = None):
        self.client = supabase_client
        if self.client is None:
            try:
                from supabase import create_client
                url = os.environ.get("SUPABASE_URL")
                key = os.environ.get("SUPABASE_SERVICE_KEY")
                if url and key:
                    self.client = create_client(url, key)
            except Exception:
                self.client = None

    def claim(self, event: NormalizedEvent) -> Tuple[bool, Optional[Dict[str, Any]]]:
        if self.client is None:
            return True, None

        row = {
            "event_id": event.event_id,
            "source": event.source.value,
            "event_type": event.event_type,
            "idempotency_key": event.idempotency_key,
            "occurred_at": event.occurred_at.isoformat(),
            "received_at": event.received_at.isoformat(),
            "status": "received",
            "payload": event.payload,
            "raw": event.raw,
            "metadata": event.metadata,
            "correlation_id": event.correlation_id,
            "genome_id": event.metadata.get("genome_id"),
            "run_id": event.metadata.get("run_id"),
        }

        try:
            result = (
                self.client.table("webhook_events")
                .upsert(row, on_conflict="idempotency_key", ignore_duplicates=True)
                .execute()
            )
            if result.data and len(result.data) > 0:
                return True, result.data[0]

            existing = (
                self.client.table("webhook_events")
                .select("*")
                .eq("idempotency_key", event.idempotency_key)
                .single()
                .execute()
            )
            return False, existing.data if existing.data else None
        except Exception as exc:
            raise RuntimeError(f"Idempotency claim failed: {exc}") from exc

    def mark_processing(self, idempotency_key: str) -> None:
        if self.client is None:
            return
        self.client.table("webhook_events").update(
            {
                "status": "processing",
                "last_attempt_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("idempotency_key", idempotency_key).execute()

    def mark_processed(
        self,
        idempotency_key: str,
        status: str = "processed",
        error_message: Optional[str] = None,
    ) -> None:
        if self.client is None:
            return
        payload = {
            "status": status,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
        if error_message:
            payload["error_message"] = error_message
        self.client.table("webhook_events").update(payload).eq(
            "idempotency_key", idempotency_key
        ).execute()

    def record_handler_run(
        self,
        webhook_event_id: str,
        handler_name: str,
        status: str,
        result: Optional[Dict] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        if self.client is None:
            return
        self.client.table("webhook_handler_runs").upsert(
            {
                "webhook_event_id": webhook_event_id,
                "handler_name": handler_name,
                "status": status,
                "result": result,
                "error_message": error_message,
                "duration_ms": duration_ms,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="webhook_event_id,handler_name",
        ).execute()
