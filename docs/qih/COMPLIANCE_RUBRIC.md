# QIH Compliance Rubric

## Purpose

This rubric is an implementation checklist for systems that seek alignment with the QIH Framework. It is not an independent audit, certification, security attestation, or legal compliance determination. A system should not claim QIH certification merely by publishing this checklist.

## Primitive 1 — Typed signal ingestion

- [ ] Every external signal enters through a documented schema or typed boundary.
- [ ] Invalid, incomplete, and unsupported inputs are rejected or quarantined with an observable outcome.
- [ ] Schema versions and breaking changes are tracked.
- [ ] Input provenance and receipt time are recorded.

## Primitive 2 — Confidence-scored intelligence

- [ ] Material signals receive a documented policy, confidence, or risk score before action.
- [ ] Scoring inputs and decision thresholds are reproducible from retained evidence.
- [ ] Threshold changes follow a controlled review or change process.
- [ ] Outcome history is used to evaluate calibration and drift.

## Primitive 3 — Idempotent action commitment

- [ ] Every consequential action has an idempotency key or equivalent uniqueness control.
- [ ] Duplicate event delivery produces one committed effect.
- [ ] Claims and leases used by workers are atomic, bounded, and recoverable.
- [ ] Retry behavior, timeout handling, and dead-letter behavior are documented and tested.

## Primitive 4 — Proof-certificate ledger

- [ ] Every committed action produces a durable traceable record.
- [ ] A canonical trace identifier propagates across relevant pipeline stages.
- [ ] Evidence records are append-only or protected by equivalent tamper-evident controls.
- [ ] Sensitive fields are minimized, redacted, or access-controlled.
- [ ] Historical actions can be reconstructed from retained evidence.

## Primitive 5 — Metacognitive maintenance loop

- [ ] A scheduled or event-driven oversight process checks for stuck, divergent, unsafe, or degraded states.
- [ ] The oversight process produces an observable run record and alert on failure.
- [ ] Parameter changes are versioned and attributable.
- [ ] The maintenance process is independently monitored.
- [ ] Rollback procedures exist for rule, model, and schema changes.

## Evidence requirements

To support a credible implementation claim, retain redacted evidence for: event receipt; scoring or policy evaluation; idempotency claim; action commitment; trace propagation; replay result; maintenance-run result; alert behavior; and rollback or remediation activity where applicable.

## Classification

| Level | Minimum condition | Meaning |
|---|---|---|
| QIH-aligned | All five primitives implemented with retained evidence | Architecture follows the framework; independent review may still be required |
| Operationally instrumented | Primitives 1–3 substantially implemented | Inputs and actions are structured, but proof and self-maintenance are incomplete |
| Partially structured | Primitive 1 implemented | Inputs are normalized, with limited guarantees about decisions and actions |
| Unverified | No retained evidence for one or more material stages | Claims should be limited to experimental or development status |

## Claim discipline

Use accurate language. “QIH-aligned” means this rubric has been applied to an implementation. “Independently certified” requires a defined, reproducible assessment method, an identified assessor, retained evidence, and a stated scope. Security, privacy, regulatory, and financial-compliance claims require their own applicable review.