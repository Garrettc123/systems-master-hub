# GARCAR Security Threat Model

## Status and scope

This is a design and review artifact for the isolated max-security branch. It is not a penetration-test report, compliance attestation, or proof that every GARCAR service implements these controls.

## Assets to protect

- Operator identities, passkeys, and privileged credentials.
- Signing and permission-provisioning keys.
- Customer, prospect, financial, and business data.
- Payment instructions, payout instructions, and transaction state.
- Agent instructions, tool permissions, and execution policies.
- Deployment credentials, infrastructure configuration, and source code.
- Audit records, backups, recovery material, and evidence provenance.

## Trust boundaries

1. **Untrusted client boundary:** HTTP requests, mobile clients, browser sessions, inbound webhooks, and external integrations.
2. **Identity boundary:** Authenticated operator or service identity. Identity must be derived from verified credentials, not request-body claims.
3. **Policy boundary:** Static action catalog, role/permission policy, tenant scope, and approval requirements.
4. **Execution boundary:** Agents, orchestrators, payment adapters, messaging adapters, deployment tools, and database writers.
5. **Evidence boundary:** Local audit database and separately administered external audit/checkpoint storage.
6. **Recovery boundary:** Backups, signing-key custody, key recovery, and incident-response operators.

## Threat scenarios and required controls

| Threat | Required control | Current status |
|---|---|---|
| Credential theft or token guessing | High-entropy secrets, constant-time comparison, MFA/passkeys, rate limiting, revocation | Partial; passkeys/MFA integration not implemented here |
| Request tampering | HMAC signature bound to method, path, timestamp, nonce, and body digest | Primitive present; integration not verified |
| Replay | Persistent atomic nonce consumption and bounded timestamp window | Implemented in isolated engine; tests pending |
| Privilege escalation | Default deny, separate provisioning credential, server-derived principal/action | Partial; provisioning API must remain local and isolated |
| Agent/tool misuse | Explicit tool allowlists, scoped identity, approval gates, no direct secret access | Not integrated |
| Audit rewriting | Hash chain plus separately administered signed checkpoints/WORM storage | Local chain only; external anchoring not implemented |
| Database outage or corruption | Fail closed, tested restore, integrity verification, recovery runbook | Fail-closed primitives partial; recovery not verified |
| Concurrent request race | Transactional nonce and rate-limit updates; concurrency tests | Implemented in isolated engine; tests pending |
| Supply-chain compromise | Pinned actions/dependencies, least-privilege workflow tokens, review and provenance | Repository-wide audit required |
| Malicious deployment or payment action | Separate approvals, dry-run, idempotency, explicit operator confirmation | Not connected by this branch |
| Denial of service | Edge controls, bounded body sizes, quotas, distributed rate limiting | Local controls partial; edge/distributed controls absent |

## Security invariants

- No protected side effect occurs before every applicable gate passes.
- Missing, malformed, stale, replayed, unauthorized, or unverifiable requests are denied.
- A caller cannot choose or self-assert its own principal, tenant, or privileged action.
- Permission provisioning is separate from normal request authentication.
- Security failures never silently fall back to permissive behavior.
- Test or preview status is never treated as production authorization.
- Production secrets and configurations are not changed by this branch.

## Residual risks and explicit exclusions

This branch does not provide a complete network perimeter, TLS termination, WebAuthn/passkeys, MFA, workload identity, OS/container isolation, distributed rate limiting, external WORM audit storage, backup restoration, key escrow, disaster recovery, or independent penetration testing. SQLite state is local to one host and is not a distributed security authority.

## Acceptance evidence required

1. Passing isolated unit and concurrency tests.
2. Integration tests proving denied requests cannot trigger side effects.
3. Independent review of the threat model and implementation.
4. Verified key custody, recovery, and rotation procedures.
5. External audit checkpoint proof and backup restore evidence.
6. Operator approval before any production connection.
