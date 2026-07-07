-- WildAutomations — Supabase schema
-- Run this ONCE in your Supabase project: Dashboard → SQL Editor → paste → Run.
-- After this, set SUPABASE_URL + SUPABASE_KEY on Railway and your data becomes
-- durable (survives redeploys) and queryable here.

-- 1) Raw scraped records (the main store mirror + cold-start hydration source)
create table if not exists crm_records (
    id           bigint generated always as identity primary key,
    hash         text unique not null,
    raw_data     jsonb,
    normalized_data jsonb,
    created_at   timestamptz default now()
);
create index if not exists idx_crm_records_hash on crm_records (hash);

-- 2) Final QUALIFIED leads (scores + AI explanation + contact) — your sales output
create table if not exists qualified_leads (
    lead_key                    text primary key,
    name                        text,
    category                    text,
    location                    text,
    ticket                      text,
    qualification_score         numeric,
    decision                    text,
    buyer_score                 numeric,
    service_score               numeric,
    website                     text,
    phone                       text,
    email                       text,
    whatsapp                    text,
    instagram                   text,
    what_to_sell                text,
    who_to_contact              text,
    outreach_channel            text,
    expected_close_probability  numeric,
    why_buyer                   text,
    opportunity_evidence        text,
    trace_id                    text,
    canonical_id                text,
    updated_at                  timestamptz default now()
);
create index if not exists idx_qleads_score on qualified_leads (qualification_score desc);
create index if not exists idx_qleads_category on qualified_leads (category);

-- ── jobs_found: every job the platform discovers (job warehouse mirror) ──────
-- New searches check this table first (via local SQLite copy); Supabase copy
-- survives Railway redeploys and becomes the growing proprietary jobs dataset.
create table if not exists jobs_found (
    url          text primary key,
    title        text not null,
    company      text,
    location     text,
    job_type     text,
    salary       text,
    source       text,
    posted_iso   text,
    query        text,
    last_seen    timestamptz default now()
);
create index if not exists idx_jobs_found_seen  on jobs_found (last_seen desc);
create index if not exists idx_jobs_found_title on jobs_found (title);
