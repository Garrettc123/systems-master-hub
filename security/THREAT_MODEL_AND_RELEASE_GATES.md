# GARCAR Enterprise — Security Threat Model and Release Gates

**Scope:** isolated reference components in `systems-master-hub`, branch `security/max-security-hardening-20261102`. This is a design and test evidence document, not independent certification. Do not interpret it as confirmation that any other Garcar service uses these controls.

## Protected assets and trust boundaries

1. **Operator identity and approval:** controlled outside the agent/model runtime. Passkey login alone must not confer permission to deploy, pay, send, delete, or modify secrets.
2. **Service credentials:** bearer, HMAC request key, permission-provisioning key, and independent checkpoint-signing key are four separate roles. Never pass them to prompts, agents, logs, or GitHub.
3. **Execution and billing:** production deployments, real Stripe transactions, outbound messages, repository administration, and destructive data changes require separate scoped policies.
4. **Audit integrity:** local SQLite is attacker-accessible if the host or its storage is compromised. A signed checkpoint only becomes strong rollback evidence after independent archival.
5. **Tenant/private data:** the provided shared token authenticates a service, not an individual tenant. Tenant identity and row scopes require a separate ingress/session integration.

## Threats, status, and controls

| Threat | Mitigation in this branch | Remaining risk |
|---|---|---|
| Forged requests and body tampering | HMAC over method/path/time/nonce/body digest, token match | Key theft, TLS/edge canonicalization, signing-client trust |
| Timestamp coercion and control-character injection | Strict integer bounds and HTTP method/path validation | Reverse-proxy normalization and body canonicalization not tested |
| Replay and concurrent nonce use | SQLite unique nonce key + write transactions | Single-host database; no global replay protection across nodes |
| Automated high-volume abuse | Persistent rate buckets; keyed subject identifiers | Fixed-window bursts, no global distributed throttle |
| Permission escalation | Separate admin key, default deny, transactional grant/revoke audit | Key custody, caller identity binding, administrative dual control |
| Agent or caller bypassing approvals | Default-required approval in example gateway, evaluated after request verification | No actual WebAuthn approval artifact verifier connected |
| Unauthorized side effect after denial | Gateway callback not invoked on failed gates | Existing live services are not yet routed through gateway |
| Local ledger record modification | Chained hashes, sequence-gap checks, gate-time integrity check | Full DB rewrite/rollback without independent checkpoint comparison |
| Audit rollback/truncation | Offline checkpoint HMAC verification of historic prefix | No independently administered WORM archive or startup-enforcement hook |
| Outage or database corruption | Local gate denies if stores fail | Backups, restore drills, failover, distributed transactional design absent |
| Secret exposure | No keys committed by this change, environment loader denies on absence | Existing secrets/config and repository history not comprehensively audited |
| Fraud or duplicate external actions | Contract prohibits pre-gate calls, mandates outbox/reconciliation | Durable production outbox/idempotency not implemented |
| CI supply-chain compromise | Focused GitHub Actions workflow with read-only content permission | All observed workflows failed with unavailable steps/logs; no successful test evidence |
| Compromised CI/build/runtime | No production change from draft PR | SLSA/provenance, deploy attestations, isolate runner, independent code review pending |

## Release criteria — ALL required

- [ ] A named reviewer validates authorization, trust-boundary assumptions, and hostile-input cases.
- [ ] Security unit tests and targeted integration tests execute and pass with logs attached to a specific commit.
- [ ] Operator identities and tenant scopes are validated by the actual ingress, not untrusted request fields.
- [ ] Real approval artifacts implement single-use proof bound to principal, action, environment, body digest, and expiry.
- [ ] External providers use idempotent transaction/outbox/reconciliation flows.
- [ ] Restricted secret manager delivers independent keys; no shared credentials across permission and audit-signature roles.
- [ ] A separate administrator controls immutable off-host audit checkpoints, with startup validation and tamper alarm.
- [ ] A distributed authority or one-replica hard restriction is tested for all nonce, permission, and rate state.
- [ ] Backup restore, corruption recovery, key rotation, and rollback procedures pass recorded drills.
- [ ] Static analysis, dependency/scanner results, workflow checks, and independent security review are recorded.
- [ ] Explicit operator approval for each production deployment or high-impact activation.

## Safe verification, currently possible

From repository root:

```sh
python -m py_compile security/max_security.py security/operation_gateway.py security/audit_checkpoint.py
python -m unittest discover -s tests -p 'test_max_security.py' -v
```

Tests only use local temporary SQLite files and fixed test keys; do **not** copy test secrets into any runtime configuration. Do not run deployments or payment actions as part of this security sweep.

## Verified vs unverified

**Repository commits:** Code, tests, and documentation have been written to the isolated branch through GitHub.

**GitHub Actions:** The observed PR commit's workflows reported failure; the GitHub connector returned empty job-step arrays and log retrieval errors. Root cause and actual test execution remain unverified.

**Production:** No claim of operational integration, WebAuthn enforcement, remote WORM storage, restored backups, successful security certification, or live release can be made from this PR.
