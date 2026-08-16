-- GARCAR FULL SCHEMA — Source of Truth
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    first_name TEXT, last_name TEXT, company TEXT, title TEXT,
    source TEXT, company_size TEXT, tech_stack TEXT[],
    lead_score INTEGER DEFAULT 0, enriched BOOLEAN DEFAULT FALSE,
    hubspot_contact_id TEXT, genome_id TEXT,
    processed BOOLEAN DEFAULT FALSE, status TEXT DEFAULT 'new',
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_genomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    genome JSONB NOT NULL,
    status TEXT DEFAULT 'candidate' CHECK (status IN ('candidate','dreaming','promoted','retired')),
    fitness JSONB, generation INT DEFAULT 0, parent_ids TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    run_id TEXT UNIQUE NOT NULL,
    trigger_type TEXT, parent_run_id TEXT,
    status TEXT DEFAULT 'running',
    started_at TIMESTAMPTZ DEFAULT NOW(), finished_at TIMESTAMPTZ,
    duration_ms INTEGER, input_payload JSONB, output_result JSONB,
    metrics JSONB DEFAULT '{}', error_code TEXT, error_message TEXT,
    revenue_influenced_usd NUMERIC(12,2), cost_usd NUMERIC(10,6),
    genome_id TEXT, environment TEXT DEFAULT 'production'
);

CREATE TABLE IF NOT EXISTS wealth_pulse (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pulse_score NUMERIC(5,2), components JSONB,
    mrr_at_risk_usd NUMERIC(12,2), mrr_protected_usd NUMERIC(12,2),
    calculated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_unprocessed ON leads(processed) WHERE processed = false;
CREATE INDEX IF NOT EXISTS idx_genomes_promoted ON agent_genomes(agent_name, status) WHERE status = 'promoted';
CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_time ON agent_runs(agent_name, started_at DESC);
