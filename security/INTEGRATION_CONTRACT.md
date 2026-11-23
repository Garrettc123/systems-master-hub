# GARCAR Protected Operation Integration Contract

## Purpose

Define the mandatory control sequence for any GARCAR subsystem that can read sensitive data or cause a side effect. This contract is a design requirement; the current branch does not claim that existing services already comply.

## Required request context

The trusted ingress adapter must provide:

- Verified bearer identity and request signature.
- Raw request body bytes and canonical request method/path.
- Timestamp and unique nonce.
- Principal and tenant derived from verified identity/session context.
- Action selected from a server-side allowlist, never copied from an untrusted payload.
- Rate-limit subject derived from the verified principal or service identity.
- Approval evidence when policy requires a human operator.

Do not log bearer tokens, signing keys, raw payment credentials, or unnecessary personal data.

## Mandatory gate

Call `MaxSecurityEngine.authorize_operation()` before any protected side effect. It performs request verification, replay protection, rate limiting, permission checks, and a final audit append. If it raises `SecurityDenied`, stop processing and return a generic denial response.

The returned audit receipt is evidence that the local authorization sequence completed. It is not a payment confirmation, deployment confirmation, business approval, or proof that the requested operation succeeded.

## Side-effect rules

- Do not execute an action inside `authorize_operation()`.
- Do not perform a database write, payment request, email/SMS send, deployment, secret mutation, or external tool call before the gate returns successfully.
- For actions requiring human approval, verify a separate approval artifact before execution; ordinary authentication is not approval.
- Use idempotency keys for payment and other non-repeatable operations.
- Record intent before execution and outcome after execution using a durable outbox or equivalent transaction-safe pattern.
- A timeout or unknown provider response is an unknown outcome, not success. Reconcile before retrying.
- Do not retry non-idempotent side effects automatically.
- Never grant an agent the permission-provisioning key.


## Isolated gateway implementation and trust contract

The `security/operation_gateway.py` reference implementation is a **trusted in-process adapter**, not a public API endpoint. It denies unknown actions. `ActionPolicy()` requires independent approval by default, and `ActionPolicy(requires_approval=False)` is only appropriate for narrowly scoped actions that policy explicitly exempts, such as an isolated local read test. The supplied `operation` callback is not invoked unless the completed authorization gate returns a receipt.

The approval-verifier callback is invoked **after** the signed request, nonce, rate limit, and permission checks. Approval verifiers must authenticate independent operator approval, bind it to tenant/principal/action/body digest, enforce bounded validity and replay resistance, and have no side effects. A demo callback or boolean is not a real approval artifact.

The gateway assumes trusted code derives the principal and rate-limit subject from authenticated identity. These values are not cryptographically bound to individual identities by the current shared bearer-token mechanism. Never accept `principal`, `action`, policies, callback functions, or `rate_subject` directly from public JSON or model-generated tool arguments.

Before integrating Stripe, email, GitHub deploy, or any external side effect, implement a durable idempotency/outbox and an approval system with independent persistence. The current adapter has neither. Existing public endpoints and services have not been wired to this adapter.

## Signed offline audit checkpoints

`security/audit_checkpoint.py` produces and verifies HMAC-authenticated JSON checkpoints for the local audit-chain prefix. Each checkpoint requires a separate, independent key with at least 32 bytes. Local JSON is **not** WORM storage. A separate administrative domain must archive checkpoints immutably, and a trustworthy bootstrap must validate them prior to operations. Full ledger rescans incur linear cost and are not a scalable distributed production implementation.

## Subsystem integration map

| Subsystem | Protected actions | Required policy |
|---|---|---|
| RHNS agents | Tool invocation, data access, delegated tasks | Per-agent identity, explicit tool/action allowlist, bounded delegation, approval for high-impact actions |
| NEXUS/orchestrator | Workflow start, worker dispatch, cross-system writes | Service identity, workflow-level authorization, execution ledger, deny on missing policy |
| Stripe/payment loop | Create/confirm/refund/payout operations | Separate payment permission, explicit human approval, idempotency, provider reconciliation; no live connection from this branch |
| Gmail/Twilio/outbound messaging | Send, reply, bulk outreach | Explicit communication permission, recipient/volume limits, consent/compliance checks, human approval where required |
| GitHub/deployment automation | Write files, create PRs, merge, deploy, alter secrets | Read-only default, branch isolation, reviewed PR, no auto-merge or production deployment |
| Supabase/data services | Read/write/export/delete records | Tenant and row scope, RLS, explicit action grants, backup and recovery controls |
| Revenue/CRM systems | Lead updates, customer records, invoice state | Data minimization, scoped write permissions, auditable state transitions |

## Deployment topology constraints

The current engine stores replay, rate-limit, permission, and audit state in local SQLite. Do not deploy multiple replicas and assume those controls are globally consistent. A distributed production design requires a centrally managed transactional store, concurrency controls, independent audit anchoring, and tested failure behavior.

Terminate TLS at a controlled ingress. Restrict network reachability between services. Use workload identity and short-lived credentials where supported. Do not expose the SQLite database or provisioning method to public endpoints.

## Integration acceptance tests

For every adapter, prove all of the following in an isolated environment:

1. Missing or invalid credentials deny the request.
2. Invalid signature, altered body, stale timestamp, and replay deny the request.
3. Rate-limit exhaustion denies the request under concurrent load.
4. Missing permission and cross-tenant access deny the request.
5. Audit-store failure prevents the side effect.
6. Approval-required actions deny without a valid approval artifact.
7. Retries do not duplicate non-idempotent side effects.
8. Provider timeouts remain unknown until reconciled.
9. Secrets are not present in logs, traces, artifacts, or test output.
10. Recovery from corrupted or unavailable state is documented and tested.

## Production boundary

No subsystem is authorized for production integration by this document. Production activation requires passing evidence, independent review, key custody, recovery validation, and explicit operator approval.
