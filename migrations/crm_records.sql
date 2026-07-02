-- ============================================================================
-- WildAutomations CRM — crm_records table
-- Run this in the Supabase SQL Editor (or psql) once.
-- Matches core/database_layer.py SupabaseDB.insert() payload:
--   { hash, raw_data (jsonb), normalized_data (jsonb) }
-- ============================================================================

create table if not exists public.crm_records (
    id               bigint generated always as identity primary key,
    hash             text        not null unique,
    raw_data         jsonb       not null,
    normalized_data  jsonb       not null,
    category         text,
    source           text,
    created_at       timestamptz not null default now()
);

-- Fast dedup lookups by hash (insert path does .eq("hash", ...))
create index if not exists idx_crm_records_hash       on public.crm_records (hash);
create index if not exists idx_crm_records_created_at on public.crm_records (created_at desc);
create index if not exists idx_crm_records_category   on public.crm_records (category);

-- Optional: query recent records by category quickly (GIN on jsonb)
create index if not exists idx_crm_records_norm_gin   on public.crm_records using gin (normalized_data);

-- ── Row Level Security ──────────────────────────────────────────────────────
-- The app connects with the service/secret key, which bypasses RLS. If you use
-- an anon key instead, enable RLS and add policies. Left enabled + permissive
-- for service-role writes; tighten later for multi-tenant use.
alter table public.crm_records enable row level security;

drop policy if exists "service_all" on public.crm_records;
create policy "service_all"
    on public.crm_records
    for all
    using (true)
    with check (true);

-- Done. Verify:
--   select count(*) from public.crm_records;
