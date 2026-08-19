-- GARCAR FULL SCHEMA — Final Architecture Source of Truth
-- Run in Supabase SQL Editor
-- Version: Multi-Model AGI Substrate + Evolution + Observation

-- ─────────────────────────────────────────────────────────────
-- CORE TABLES
-- ─────────────────────────────────────────────────────────────

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

-- ─────────────────────────────────────────────────────────────
-- OUTCOME LEDGER (Bidirectional Feedback)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS lead_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES leads(id),
    hubspot_contact_id TEXT,
    hubspot_deal_id TEXT,
    genome_id TEXT,
    original_run_id TEXT,
    outcome_type TEXT NOT NULL,
    revenue_usd NUMERIC(12,2),
    acquisition_cost_usd NUMERIC(10,4),
    days_to_close INTEGER,
    dealstage_at_outcome TEXT,
    observed_at TIMESTAMPTZ DEFAULT NOW(),
    raw_payload JSONB,
    UNIQUE(hubspot_deal_id)
);

-- ─────────────────────────────────────────────────────────────
-- SYNCHRONICITY EVENTS (Emergent Alignment)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS synchronicity_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    strength NUMERIC(5,4) NOT NULL,
    participants JSONB NOT NULL,
    shared_signal JSONB,
    economic_value NUMERIC(12,2),
    observed_at TIMESTAMPTZ DEFAULT NOW(),
    explained TEXT
);

-- ─────────────────────────────────────────────────────────────
-- DRIFT SIGNALS (Reality Contact)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS drift_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drift_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    baseline_value NUMERIC,
    current_value NUMERIC,
    delta NUMERIC,
    severity TEXT CHECK (severity IN ('low','medium','high','critical')),
    window_start TIMESTAMPTZ,
    window_end TIMESTAMPTZ,
    genome_id TEXT,
    provider TEXT,
    details JSONB,
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_leads_unprocessed ON leads(processed) WHERE processed = false;
CREATE INDEX IF NOT EXISTS idx_genomes_promoted ON agent_genomes(agent_name, status) WHERE status = 'promoted';
CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_time ON agent_runs(agent_name, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_lead_outcomes_genome ON lead_outcomes(genome_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_synchronicity_time ON synchronicity_events(observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_drift_type_time ON drift_signals(drift_type, detected_at DESC);
