-- GARCAR Revenue Ledger — Supabase Schema
-- Deploy via: Supabase Dashboard > SQL Editor
-- Part of the garcar-payment-loop real-time revenue tracking system

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Core revenue events table
CREATE TABLE IF NOT EXISTS revenue_events (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source          TEXT NOT NULL CHECK (source IN ('stripe', 'shopify', 'base_l2', 'huggingface', 'linear', 'manual')),
  event_type      TEXT NOT NULL,  -- payment.succeeded, subscription.created, etc.
  amount          DECIMAL(14, 2) NOT NULL DEFAULT 0,
  currency        TEXT NOT NULL DEFAULT 'USD',
  customer_id     TEXT,
  customer_email  TEXT,
  product_id      TEXT,
  product_name    TEXT,
  stripe_id       TEXT,
  metadata        JSONB DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Lead pipeline table (fed by lead-enrichment-engine)
CREATE TABLE IF NOT EXISTS leads (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email           TEXT UNIQUE NOT NULL,
  full_name       TEXT,
  company         TEXT,
  title           TEXT,
  linkedin_url    TEXT,
  phone           TEXT,
  score           INTEGER DEFAULT 0 CHECK (score >= 0 AND score <= 100),
  stage           TEXT DEFAULT 'raw' CHECK (stage IN ('raw', 'enriched', 'qualified', 'contacted', 'demo', 'proposal', 'closed_won', 'closed_lost')),
  source          TEXT,
  apollo_id       TEXT,
  linear_issue_id TEXT,
  notion_page_id  TEXT,
  enrichment_data JSONB DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- System health metrics
CREATE TABLE IF NOT EXISTS system_metrics (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  system_name     TEXT NOT NULL,
  metric_name     TEXT NOT NULL,
  metric_value    DECIMAL(14, 4),
  metric_text     TEXT,
  recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Monthly revenue rollup view
CREATE OR REPLACE VIEW monthly_revenue AS
SELECT
  DATE_TRUNC('month', created_at) AS month,
  source,
  SUM(amount) AS total_revenue,
  COUNT(*) AS transaction_count,
  AVG(amount) AS avg_transaction
FROM revenue_events
WHERE currency = 'USD'
GROUP BY DATE_TRUNC('month', created_at), source
ORDER BY month DESC, total_revenue DESC;

-- Real-time notification trigger → feeds Slack webhook via Edge Function
CREATE OR REPLACE FUNCTION notify_revenue_event()
RETURNS trigger AS $$
BEGIN
  PERFORM pg_notify(
    'revenue_event',
    json_build_object(
      'id', NEW.id,
      'source', NEW.source,
      'amount', NEW.amount,
      'currency', NEW.currency,
      'event_type', NEW.event_type,
      'customer_email', NEW.customer_email,
      'created_at', NEW.created_at
    )::text
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER revenue_event_notify
  AFTER INSERT ON revenue_events
  FOR EACH ROW EXECUTE FUNCTION notify_revenue_event();

-- Enable Row Level Security
ALTER TABLE revenue_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_metrics ENABLE ROW LEVEL SECURITY;

-- Service role has full access (used by garcar-payment-loop)
CREATE POLICY "service_role_all" ON revenue_events
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "service_role_all" ON leads
  FOR ALL USING (auth.role() = 'service_role');

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_revenue_events_created_at ON revenue_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_revenue_events_source ON revenue_events(source);
CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage);
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);

COMMIT;
