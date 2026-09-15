# Garcar Core v3.5 Operations Contract

## Reliability

Every externally executed action must have:
- tenant_id
- action_id
- lead_id when applicable
- idempotency key
- policy decision
- attempt counter
- timestamps
- outcome

Retries use exponential backoff and terminate in a dead-letter state after the configured attempt ceiling.

## Reconciliation

A scheduled reconciler compares internal action state with adapter/provider state. Differences become reconciliation events; the reconciler must not silently rewrite history.

## Circuit breaker

An adapter is disabled for new work when consecutive provider failures exceed a configured threshold. Existing actions remain observable and retryable according to policy.

## Reporting

Tenant reports should expose:
- inbound leads
- response-time distribution
- contact rate
- qualification rate
- booking rate
- estimate follow-up completion
- stale leads
- recovered leads
- attributed revenue
- action failures

## Security boundary

Secrets belong to the deployment environment or secret manager, never lead payloads, Git history, or application logs. Customer-sensitive values should be minimized before storage and never copied into telemetry labels.

## Deployment gate

v3.5 is production-ready only after:
1. database migrations are reviewed and applied in a controlled environment;
2. adapter contract tests pass;
3. webhook signatures are verified;
4. tenant isolation is tested;
5. replay/idempotency tests pass;
6. dead-letter and reconciliation paths are exercised;
7. human approval requirements are enforced for configured high-impact actions;
8. observed SLOs are measured rather than asserted.