# GARCAR Security Operations Runbook

## Current operating mode

The max-security engine and its follow-up hardening work are isolated in draft pull requests. No production service is authorized by this runbook. Do not create, rotate, print, or replace existing production secrets as part of this work.

## Required secrets

The isolated engine configuration expects three independent high-entropy values:

- `GARCAR_BEARER_TOKEN`: request authentication.
- `GARCAR_SIGNING_KEY`: HMAC request signing.
- `GARCAR_PERMISSION_ADMIN_KEY`: local privileged permission provisioning.

Each value must contain at least 32 bytes of cryptographically random material. Store them only in an approved secret manager or protected runtime environment. Never place them in source code, GitHub artifacts, issue comments, terminal transcripts, logs, or chat.

This repository work does not provision or rotate these values. Do not generate production replacements without a reviewed key-custody and migration plan.

## Startup checks before any future integration

1. Confirm required configuration exists without printing values.
2. Confirm configuration lengths and types validate.
3. Confirm the security database is writable only by the intended service identity.
4. Verify the audit chain before accepting protected work.
5. Confirm database backup and restore evidence is current.
6. Confirm the runtime is single-host or has an explicitly approved shared-state design.
7. Confirm the ingress enforces TLS and request-size limits.
8. Confirm no agent or public handler can call permission provisioning.
9. Confirm policy maps each protected action to a principal and approval requirement.
10. Keep execution disabled if any check fails.

## Incident response

### Suspected credential compromise

- Stop the affected protected execution path.
- Preserve logs and evidence without copying secret values into tickets.
- Identify affected identities, systems, and time window.
- Revoke or rotate only under the approved secret-manager process and documented owner approval.
- Reissue credentials through controlled custody; verify old credentials are rejected.
- Review audit records and reconcile provider-side activity.

### Audit integrity failure

- Deny protected operations.
- Preserve the database and relevant host evidence; do not repair or rewrite the original evidence copy.
- Compare against the latest independently stored signed checkpoint, if one exists.
- Restore only from a verified backup into a separate recovery environment.
- Record the incident and obtain independent review before re-enabling execution.

### Security store unavailable

- Deny protected operations.
- Do not switch to in-memory replay tracking or permissive authorization.
- Restore service only after database integrity and recovery tests pass.

### Suspected unauthorized side effect

- Stop the affected adapter and prevent retries.
- Reconcile directly with the provider (payment, messaging, deployment, or data service).
- Treat unknown provider outcomes as unresolved until reconciled.
- Preserve request identifiers, idempotency keys, and audit evidence.
- Require operator approval before resuming.

## Recovery and rotation requirements

Before production readiness, document key owners, access boundaries, backup encryption, recovery quorum, rotation overlap, revocation behavior, and rollback procedure. Test recovery with non-production credentials and isolated data. Never store the only copy of a recovery key alongside the database it protects.

## Operational status vocabulary

- **Implemented:** code or configuration exists.
- **Tested:** a named test ran and its result is available.
- **Verified:** independent or reproducible evidence confirms behavior.
- **Deployed:** a named runtime accepted the artifact.
- **Production-authorized:** operator approval and all required gates are documented.

Do not use these terms interchangeably.
