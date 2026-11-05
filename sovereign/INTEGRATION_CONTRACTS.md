# Garcar Shared Integration Contracts

Version: 1.0.0 (initial draft)

## Service contract

Every integrated service must publish:

- `GET /health`: process liveness only.
- `GET /ready`: readiness, including required dependencies.
- `GET /metrics`: optional local metrics endpoint; must not expose secrets.
- `/api/v1/*`: versioned application API.
- A service identity and owner in the system registry.
- Structured logs with a correlation ID.
- Audit records for authorization, deployment, payment, and administrative changes.

A 200 from `/health` does not prove database readiness, payment functionality, customer availability, or production status.

## Event envelope

Every event uses this envelope:

```json
{
  "event_id": "unique-id",
  "event_type": "deployment.completed",
  "schema_version": "1.0.0",
  "occurred_at": "UTC RFC3339 timestamp",
  "producer": "service-name",
  "correlation_id": "request-or-workflow-id",
  "subject_id": "business-entity-id",
  "data": {}
}
```

Consumers must deduplicate by `event_id`. Producers must not put credentials, access tokens, card data, or raw personal secrets in event payloads.

## Initial event taxonomy

- `user.created`
- `subscription.started`
- `payment.succeeded`
- `payment.failed`
- `content.generated`
- `product.purchased`
- `usage.reported`
- `deployment.started`
- `deployment.completed`
- `deployment.failed`
- `deployment.rolled_back`
- `alert.triggered`

## Financial event rules

A `payment.succeeded` event is accepted only after verification of the provider signature and authoritative payment object. Use idempotency keys and reconcile events against the provider's balance/charge records. Never treat a webhook body, invoice draft, payout, or test-mode event as collected customer revenue.

The initial sovereign controller does not execute payments or configure payment webhooks.

## Data ownership

- SQLite: local controller state, local event spool, and device audit trail.
- PostgreSQL: shared transactional data only when a multi-service host exists.
- Object storage: optional, only after a self-hosted durable storage target and backup policy are selected.
- Redis, MongoDB, Kafka, Kubernetes and other infrastructure are not mandatory dependencies. Add them only when measured workload and operational capacity justify them.

## Trust boundaries

- Market intelligence and trading-support systems are data producers only by default.
- Financial execution requires separate policy, risk checks, and explicit operator approval.
- AI agents cannot change deployment policy, secret stores, billing configuration, or production routing without an authorized control-plane decision.
- Every cross-service request is authenticated and carries a correlation ID.
