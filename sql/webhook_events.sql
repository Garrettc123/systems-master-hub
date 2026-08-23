-- GARCAR WEBHOOK + IDEMPOTENCY TABLES
-- Append to sql/full_schema.sql or run independently in Supabase
-- Version: 1.0.0 — Foundation for all external event ingress

CREATE TABLE IF NOT EXISTS webhook_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id        TEXT NOT NULL,
    source          TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    occurred_at     TIMESTAMPTZ NOT NULL,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status          TEXT NOT NULL DEFAULT 'received'
                        CHECK (status IN (
                            'received',
                            'processing',
                            'processed',
                            'failed',
                            'ignored',
                            'replayed'
                        )),
    payload         JSONB NOT NULL DEFAULT '{}',
    raw             JSONB,
    metadata        JSONB DEFAULT '{}',
    error_message   TEXT,
    processed_at    TIMESTAMPTZ,
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    correlation_id  TEXT,
    genome_id       TEXT,
    run_id          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webhook_events_idempotency
    ON webhook_events (idempotency_key);

CREATE INDEX IF NOT EXISTS idx_webhook_events_source_type
    ON webhook_events (source, event_type, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_webhook_events_status
    ON webhook_events (status) WHERE status IN ('received', 'processing', 'failed');

CREATE INDEX IF NOT EXISTS idx_webhook_events_correlation
    ON webhook_events (correlation_id) WHERE correlation_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS webhook_handler_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_event_id UUID NOT NULL REFERENCES webhook_events(id) ON DELETE CASCADE,
    handler_name    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'started'
                        CHECK (status IN ('started', 'succeeded', 'failed', 'skipped')),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    duration_ms     INTEGER,
    result          JSONB,
    error_message   TEXT,
    UNIQUE (webhook_event_id, handler_name)
);

CREATE INDEX IF NOT EXISTS idx_handler_runs_event
    ON webhook_handler_runs (webhook_event_id);

CREATE OR REPLACE FUNCTION claim_webhook_event(p_idempotency_key TEXT)
RETURNS TABLE (
    claimed BOOLEAN,
    event_row JSONB
) LANGUAGE plpgsql AS $$
DECLARE
    v_row webhook_events%ROWTYPE;
BEGIN
    BEGIN
        INSERT INTO webhook_events (
            event_id, source, event_type, idempotency_key,
            occurred_at, status, payload
        )
        VALUES (
            split_part(p_idempotency_key, ':', 2),
            split_part(p_idempotency_key, ':', 1),
            'unknown',
            p_idempotency_key,
            NOW(),
            'received',
            '{}'
        )
        ON CONFLICT (idempotency_key) DO NOTHING
        RETURNING * INTO v_row;

        IF FOUND THEN
            claimed := TRUE;
            event_row := to_jsonb(v_row);
            RETURN NEXT;
            RETURN;
        END IF;
    EXCEPTION WHEN unique_violation THEN
        NULL;
    END;

    SELECT * INTO v_row FROM webhook_events WHERE idempotency_key = p_idempotency_key;
    claimed := FALSE;
    event_row := to_jsonb(v_row);
    RETURN NEXT;
END;
$$;

COMMENT ON TABLE webhook_events IS 'Canonical ledger of every inbound event. Idempotency key is the single source of truth for deduplication.';
COMMENT ON TABLE webhook_handler_runs IS 'Per-handler execution record. Enables selective replay of failed subscribers without re-processing the whole event.';
