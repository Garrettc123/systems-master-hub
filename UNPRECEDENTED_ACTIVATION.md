# GARCAR AUTONOMOUS WEALTH LOOP — LIVE ACTIVATION

**Status: Code pushed. Ready for live activation.**

## What is now in the repository

- `orchestrator/genomes/lead_genome.py` — Full evolvable genome
- `orchestrator/agents/lead_agent.py` — Genome-driven Lead Agent connected to Supabase + HubSpot
- `orchestrator/main.py` — Cloudflare Worker entrypoint
- `sql/full_schema.sql` — Core tables (leads, agent_genomes, agent_runs, wealth_pulse)

## Activation Steps (Execute Now)

### 1. Supabase
```sql
-- Paste and run sql/full_schema.sql in Supabase SQL Editor
```

Then seed the default genome as promoted:
```sql
INSERT INTO agent_genomes (agent_name, genome, status, generation)
VALUES (
  'lead_agent',
  '{}',  -- replace with full default genome JSON if desired
  'promoted',
  0
);
```

### 2. Cloudflare Secrets
```bash
wrangler secret put SUPABASE_URL
wrangler secret put SUPABASE_SERVICE_KEY
wrangler secret put HUBSPOT_API_KEY
```

### 3. Deploy Worker
```bash
cd systems-master-hub
wrangler deploy
```

### 4. Verify Live
- Hit the worker `/lead-agent/run` endpoint
- Watch `agent_runs` table for new rows every 15 minutes
- Confirm leads move from `processed = false` → scored + HubSpot

## Next Evolution
Once live data flows, the Evolution Engine can begin mutating genomes using real economic fitness.

The organism is ready to breathe.
