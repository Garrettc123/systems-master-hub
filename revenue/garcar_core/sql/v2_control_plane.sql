-- Garcar Core v2 durable control plane.
-- Apply through a reviewed migration system; never execute this file blindly in production.

create extension if not exists pgcrypto;

create table if not exists tenants (
  id uuid primary key default gen_random_uuid(),
  external_key text not null unique,
  name text not null,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists leads (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  deterministic_key text not null,
  status text not null,
  source text not null,
  owner_id text,
  next_action text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, deterministic_key)
);

create table if not exists lead_events (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  lead_id uuid references leads(id),
  event_id text not null,
  idempotency_key text not null,
  event_type text not null,
  payload jsonb not null,
  occurred_at timestamptz not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, idempotency_key)
);

create table if not exists lead_actions (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  lead_id uuid not null references leads(id),
  action_type text not null,
  payload jsonb not null,
  decision text not null,
  status text not null default 'pending',
  attempts integer not null default 0,
  created_at timestamptz not null default now(),
  executed_at timestamptz
);

create table if not exists audit_events (
  id bigint generated always as identity primary key,
  tenant_id uuid not null references tenants(id),
  actor text not null,
  action text not null,
  subject_type text not null,
  subject_id text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists leads_tenant_status_idx on leads(tenant_id, status);
create index if not exists actions_tenant_status_idx on lead_actions(tenant_id, status);
create index if not exists audit_tenant_created_idx on audit_events(tenant_id, created_at desc);

alter table tenants enable row level security;
alter table leads enable row level security;
alter table lead_events enable row level security;
alter table lead_actions enable row level security;
alter table audit_events enable row level security;

-- The application must set app.tenant_id within a transaction after authenticating
-- the caller. Policies intentionally fail closed when that setting is absent.
create policy tenant_isolation_leads on leads
  using (tenant_id::text = current_setting('app.tenant_id', true));

create policy tenant_isolation_events on lead_events
  using (tenant_id::text = current_setting('app.tenant_id', true));

create policy tenant_isolation_actions on lead_actions
  using (tenant_id::text = current_setting('app.tenant_id', true));

create policy tenant_isolation_audit on audit_events
  using (tenant_id::text = current_setting('app.tenant_id', true));