# Garcar Enterprise — Final Architecture

**Multi-Model AGI Substrate · Genome Evolution · Observation · Benchmarked Results**

## Principle

Use every model. Record every outcome. Evolve only on proven economic value. Never lose contact with reality.

## Layout

```
orchestrator/
  providers/
    base.py          # ProviderResponse + BaseProvider
    router.py        # MultiModelRouter (genome-controlled)
  evolution/
    crossover.py     # Hybrid crossover strategies
    fitness.py       # Economic fitness + promotion gate
    synchronicity.py # Cross-model/genome alignment detector
    drift.py         # Performance/cost/model drift monitor
  agents/
    lead_agent.py    # Existing — genome-driven lead scoring
  genomes/
    lead_genome.py   # Existing — evolvable config unit
  main.py            # Cloudflare Worker entry
```

## Schema (sql/full_schema.sql)

- `leads`, `agent_genomes`, `agent_runs`, `wealth_pulse`
- `lead_outcomes` — bidirectional HubSpot feedback
- `synchronicity_events` — emergent alignment
- `drift_signals` — reality contact

## Data Flow

1. Lead Agent loads promoted genome
2. MultiModelRouter selects providers per task type
3. Scores + routes high-value leads to HubSpot
4. Feedback writes lead_outcomes
5. Fitness updated from outcomes
6. SynchronicityDetector records cross-model/genome alignment
7. DriftMonitor compares current windows to promotion baseline
8. Crossover + mutation create candidates
9. Promotion only on measured economic lift

## Benchmarks (Required for Promotion)

| Metric | Direction |
|--------|-----------|
| Revenue per Lead | ↑ |
| Cost per Won | ↓ |
| Expected Value per Lead | ↑ |
| Net Economic Lift vs previous promoted | > threshold |
| Sample size | ≥ minimum |

Secondary: cross-model agreement, synchronicity frequency, drift severity.

## Guardrails

- Production behavior changes **only** via genome promotion
- Every autonomous action writes an outcome event
- Prefer expected economic value over activity volume
- Rate limits, budgets, human-approval gates remain in host orchestrator
- Drift never auto-demotes; it increases candidate pressure

## Providers (Wire via Autokey)

- `PERPLEXITY_API_KEY` — live web
- `GEMINI_API_KEY` / `GOOGLE_API_KEY` — long context
- `OPENAI_API_KEY` — tools + instruction following
- `ANTHROPIC_API_KEY` — reasoning + safety

## Status

Foundation implemented: schema, router, crossover, fitness, synchronicity, drift.
Next: concrete provider clients, Feedback Agent, full Lead Agent integration, benchmark runner.
