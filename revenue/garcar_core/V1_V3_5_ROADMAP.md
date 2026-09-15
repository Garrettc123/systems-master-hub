# Garcar Core v1 → v3.5

This is the implementation contract for the first commercial revenue-control product.

## v1.0 — Safe Lead Intake
- Strict event contract
- Tenant/idempotency boundary
- Deterministic lead identity
- Policy classification
- Append-only audit intent
- Draft-only actions

## v1.5 — Lifecycle Control
- Explicit state transitions
- Owner and next-action requirements
- SLA timestamps
- Stale-lead detection
- Recovery/replay semantics

## v2.0 — Persistent Multi-Tenant Control Plane
- PostgreSQL schema
- Tenant isolation/RLS
- Durable events, leads, actions, assignments and audit records
- Outbox pattern for external side effects
- Idempotency persisted at database level

## v2.5 — Revenue Workflow
- Qualification policy
- Assignment rules
- Booking adapter contract
- Estimate follow-up scheduler
- Lead recovery queue
- Revenue attribution events

## v3.0 — Governed Integrations
- CRM adapter interface
- Messaging adapter interface
- Calendar adapter interface
- Provider-neutral webhooks
- Signed webhook verification
- Rate limits and retry policy
- Human approval for consequential actions

## v3.5 — Reliability + Operations
- SLO/SLA measurement from observed events
- Dead-letter queue semantics
- Circuit breakers
- Reconciliation jobs
- Audit export
- Operator dashboard contract
- Tenant-scoped reporting
- Regression and contract-test suite

## Non-goals through v3.5
- Autonomous pricing
- Autonomous refunds
- Autonomous payment collection
- Unreviewed legal/medical/financial decisions
- Unbounded outbound messaging
- Autonomous production code merging

The platform should prove the lead-to-revenue control loop before adding broader agentic capabilities.