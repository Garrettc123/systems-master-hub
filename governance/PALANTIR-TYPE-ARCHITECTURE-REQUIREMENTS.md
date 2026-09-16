# PALANTIR-TYPE ARCHITECTURE REQUIREMENTS
## Fully Approved — Unprecedented Full Sweep
**Status:** APPROVED & BINDING  
**Date:** 2026-09-15  
**Authority:** Garcar Enterprise Operator  

These requirements elevate the entire surface (control planes, revenue organs, compliance isolation) to high-assurance, evidence-driven architecture standards equivalent to enterprise government/intelligence platforms (ontology, provenance, least-privilege, immutable audit, governed pipelines).

## Core Principles (Non-Negotiable)

| Principle | Requirement | BioForge / Garcar Mapping |
|-----------|-------------|---------------------------|
| Ontology-first | All business objects (Lead, Deal, Payment, Organ, Evidence) have canonical schemas and relationships | Module contracts + RHNS ports |
| Provenance & lineage | Every state change is attributable, timestamped, and linked to prior evidence | CMC commit + audit trail in Core |
| Least privilege | Explicit permissions; no default read-write tokens; role-scoped access | Workflow `permissions:` blocks + tenancy in Core |
| Immutability | No in-place mutation of production artifacts; new instances only | Indestructible infra + detach/rollback |
| Governed pipelines | Every hop that moves money, reputation, or customer data is gated | RHNS plan/verify/gate/escalate + CMC |
| Evidence closure | Actions produce verifiable artifacts (SBOM, logs, commits, ledger entries) | CycloneDX + gc_ledger + status dashboards |
| Detachability | Every organ can be cleanly removed without core corruption | Six certification gates |

## Revenue Spine
The eight-hop walking skeleton remains the sole monetizing path. Every hop must declare planner, constraint, confidence gate, audit write, SKU, and detach behavior. No hop may bypass CMC `commit`.

## Approval
Palantir-type architecture requirements are fully approved. Unprecedented full sweep is authorized under these controls.
