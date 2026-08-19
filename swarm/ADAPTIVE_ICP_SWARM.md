# Adaptive ICP Swarm

## Purpose

The swarm now treats the ideal customer profile as an online learning problem rather than a static marketing configuration.

## Closed loop

```text
Market discovery
      -> enrichment
      -> ICP hypothesis scoring
      -> personalized outreach
      -> qualification
      -> proposal
      -> sale / loss
      -> retention / expansion
      -> outcome ledger
      -> Adaptive ICP Engine
      -> segment re-ranking
      -> next discovery cycle
```

## Agent roles

| Agent | Responsibility | Output |
|---|---|---|
| Scout | Discover candidate accounts and segments | Prospect observations |
| Enricher | Normalize firmographic and operational signals | Evidence record |
| Qualifier | Estimate pain, urgency, buying authority | Signal vector |
| Offer Agent | Select the narrowest viable offer | Offer hypothesis |
| Outreach Agent | Execute approved contact sequences | Conversation events |
| Deal Agent | Move qualified opportunities toward payment | Deal events |
| Retention Agent | Measure retention and expansion signals | Customer outcomes |
| ICP Analyst | Update segment scores from observed evidence | Ranked ICPs |
| Orchestrator | Enforce state transitions, budgets, permissions and stop conditions | Auditable actions |

## Decision contract

The swarm should optimize for **expected economic value**, not activity volume. Every autonomous action should have:

1. a target segment,
2. an evidence basis,
3. an expected outcome,
4. a budget/rate limit,
5. a reversible action where practical,
6. an outcome event written back to the ledger.

The ICP engine uses seven initial signals:

- pain severity — 20%
- ability to pay — 20%
- lead volume — 15%
- operational inefficiency — 15%
- buying urgency — 10%
- decision-maker access — 10%
- retention potential — 10%

As evidence accumulates, actual win rate, retention and revenue-to-acquisition-cost performance increasingly influence the segment score.

## Integration boundary

`AdaptiveICPEngine` is deliberately framework-independent. The existing swarm/orchestration layer can feed it normalized `ProspectObservation` events and consume ranked segments without coupling the decision logic to a specific LLM provider, CRM, database, or UI.

### Example

```python
from swarm.adaptive_icp_engine import AdaptiveICPEngine, ProspectObservation

engine = AdaptiveICPEngine()
engine.ingest(ProspectObservation(
    segment="owner_led_service_business",
    signals={
        "pain_severity": 0.9,
        "ability_to_pay": 0.8,
        "lead_volume": 0.7,
        "operational_inefficiency": 0.9,
        "buying_urgency": 0.8,
        "decision_maker_access": 1.0,
        "retention_potential": 0.8,
    },
    outcome="won",
    contract_value=5000,
    acquisition_cost=450,
    retained=True,
))

print(engine.rank())
```

## Guardrails

This component ranks commercial opportunities; it does not authorize unrestricted autonomous contact. Outreach, purchasing, financial commitments, credential use, and other consequential actions remain subject to the permissions, compliance controls, rate limits, and human-approval gates of the host orchestration layer.
