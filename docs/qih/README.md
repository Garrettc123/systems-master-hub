# QIH Framework

## A Framework for Auditable Autonomous Decision Systems

QIH, the Quantified Intelligence Hierarchy, is a software architecture and governance framework for autonomous systems that make or support consequential operational decisions. Its purpose is practical: make automated behavior traceable, reproducible, reviewable, and safer to operate under uncertainty.

## The problem

Autonomous systems often degrade quietly. Signals change, confidence thresholds drift, retries create duplicate actions, queues stall, and operators cannot reconstruct why a decision happened. Monitoring and testing help, but neither alone makes the decision path provable.

QIH describes the minimum operating structures intended to address that gap.

## Five primitives

### 1. Typed signal ingestion

Environmental inputs are validated and typed before they affect a decision pipeline. This establishes a defined sensory boundary and reduces nondeterministic downstream behavior.

### 2. Confidence-scored intelligence

Signals are evaluated with confidence or policy scores before they influence actions. Scores are intended to be updated from outcome history rather than treated as permanent constants.

### 3. Idempotent action commitment

Actions are committed with an idempotency key before execution. Replays of the same event should result in one committed action, preventing common duplicate-delivery and retry failures.

### 4. Proof-certificate ledger

Committed actions produce append-only evidence entries with a canonical trace identifier. The ledger provides a reconstructable operational history rather than relying on transient process state.

### 5. Metacognitive maintenance loop

A second-order process monitors first-order behavior, identifies anomalies or divergence, and updates operational parameters through controlled change procedures. The maintenance loop itself must be monitored.

## Compliance intent

A QIH-aligned system should be able to answer: What signal was received? How was it interpreted? What policy or confidence threshold applied? What action was committed? Can the action be replayed and independently checked? What changed after the outcome was observed?

Read the [compliance rubric](COMPLIANCE_RUBRIC.md) for the implementation checklist and [intellectual foundations](COMPARISONS.md) for the conceptual lineage.

## Implementation status

Garcar Enterprise maintains a private technical implementation repository and a production data foundation that includes telemetry, processing-run, insight, trace, memory, and metacognitive-flag structures. Public documentation describes the framework and intended controls. It does not claim completed independent certification, live commercial availability, or any unverified performance, security, or revenue result.

## Scope boundary

QIH is a software engineering and governance framework. It does not make claims about consciousness, quantum gravity, cosmology, or physical reality. Those claims require independent empirical evidence outside the scope of this project.

## Contact

Garcar Enterprise develops automation, revenue-operations, and governance systems for organizations that need transparent, accountable AI-assisted workflows.