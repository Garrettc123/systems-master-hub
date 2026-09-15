# Garcar Core — Lead Response Engine v1

A narrow, revenue-first control plane for home-service lead handling.

## Scope

The v1 engine accepts inbound lead events, normalizes and deduplicates them, applies policy, assigns an owner, records the required next action, and emits **draft actions** for external messaging and booking.

Outbound side effects are adapter responsibilities and remain disabled by default. The core records what should happen before anything is sent.

## State machine

`RECEIVED -> QUALIFYING -> ASSIGNED -> BOOKING_PENDING -> FOLLOW_UP -> WON|LOST|STALE`

`BLOCKED` and `ESCALATED` are terminal safety states until an operator resolves them.

## Security invariants

- Every request has a tenant identifier.
- Every event has an idempotency key.
- External side effects require an explicit policy decision.
- Sensitive/high-risk operations are represented as drafts and never sent by the core.
- State transitions are append-only in the audit log.
- No secrets are stored in application state.

## Run

```bash
python -m pip install -r requirements.txt
uvicorn revenue.garcar_core.app:app --host 0.0.0.0 --port 8080
```

Health: `GET /healthz`

Ingest: `POST /v1/events/lead`

## Example event

```json
{
  "event_id": "evt_123",
  "tenant_id": "tenant_demo",
  "source": "web_form",
  "occurred_at": "2026-09-15T19:00:00Z",
  "customer": {
    "name": "Jane Doe",
    "phone": "+1-817-555-0100"
  },
  "request": {
    "service": "AC repair",
    "city": "Cleburne",
    "urgency": "today"
  }
}
```

This repository component is intentionally smaller than the wider Garcar Enterprise architecture. The commercial objective is to prove one measurable revenue loop before adding more agentic behavior.
