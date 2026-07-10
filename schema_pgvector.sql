-- Wild Automations — PostgreSQL + pgvector schema
-- Run once against your Railway Postgres instance:
--   psql $DATABASE_URL -f schema_pgvector.sql

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for fuzzy text search

-- ── Jobs table ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jobs (
    job_id          TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    norm_title      TEXT,
    company         TEXT,
    company_canon   TEXT,
    location        TEXT,
    city            TEXT,
    country_iso     CHAR(2),
    remote          BOOLEAN DEFAULT FALSE,
    seniority       TEXT,

    -- Salary
    salary_raw      TEXT,
    salary_usd      INTEGER,
    salary_display  TEXT,
    salary_est      JSONB,   -- {estimated, usd_low, usd_high, confidence, method}

    -- AI intelligence
    ats_platform    TEXT DEFAULT 'unknown',
    remote_score    REAL DEFAULT 0.15,
    remote_label    TEXT,
    scam_score      REAL DEFAULT 0.0,
    is_likely_scam  BOOLEAN DEFAULT FALSE,
    match_score     INTEGER,  -- 0-100, vs user CV

    -- Hiring velocity (updated per-run)
    hiring_velocity TEXT,     -- 'high' | 'medium' | 'low'
    velocity_count  INTEGER,

    -- Visa / sponsor
    visa_flag       BOOLEAN DEFAULT FALSE,
    sponsor_verified BOOLEAN DEFAULT FALSE,
    sponsor_routes  TEXT[],

    -- Content
    description     TEXT,
    skills          TEXT[],
    url             TEXT,
    source          TEXT,
    posted          TEXT,
    employees       TEXT,

    -- Embeddings (text-embedding-3-small = 1536 dims)
    embedding       vector(1536),

    -- Tracking
    first_seen      TIMESTAMPTZ DEFAULT NOW(),
    last_seen       TIMESTAMPTZ DEFAULT NOW(),
    times_seen      INTEGER DEFAULT 1,

    -- Full intelligence blob (for fast read)
    intelligence    JSONB
);

-- Indexes
CREATE INDEX IF NOT EXISTS jobs_company_idx   ON jobs (company_canon);
CREATE INDEX IF NOT EXISTS jobs_remote_idx    ON jobs (remote);
CREATE INDEX IF NOT EXISTS jobs_country_idx   ON jobs (country_iso);
CREATE INDEX IF NOT EXISTS jobs_source_idx    ON jobs (source);
CREATE INDEX IF NOT EXISTS jobs_ats_idx       ON jobs (ats_platform);
CREATE INDEX IF NOT EXISTS jobs_scam_idx      ON jobs (is_likely_scam);
CREATE INDEX IF NOT EXISTS jobs_sponsor_idx   ON jobs (sponsor_verified);
CREATE INDEX IF NOT EXISTS jobs_seen_idx      ON jobs (last_seen DESC);

-- Trigram index for fuzzy title search
CREATE INDEX IF NOT EXISTS jobs_title_trgm    ON jobs USING GIN (norm_title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS jobs_company_trgm  ON jobs USING GIN (company_canon gin_trgm_ops);

-- Vector similarity search index (HNSW — fast approximate nearest-neighbor)
CREATE INDEX IF NOT EXISTS jobs_embedding_idx ON jobs
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ── User CVs / profiles ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id         TEXT PRIMARY KEY,
    cv_text         TEXT,
    cv_summary      TEXT,
    role            TEXT,
    skills          TEXT[],
    location        TEXT,
    seniority       TEXT,
    cv_embedding    vector(1536),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Tracked jobs (user bookmarks) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tracked_jobs (
    id              SERIAL PRIMARY KEY,
    user_id         TEXT NOT NULL,
    job_id          TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    status          TEXT DEFAULT 'saved',  -- saved | applied | interviewing | rejected | offered
    notes           TEXT,
    tracked_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, job_id)
);

-- ── Search history ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS search_history (
    id              SERIAL PRIMARY KEY,
    user_id         TEXT,
    query           TEXT,
    location        TEXT,
    job_type        TEXT,
    results_count   INTEGER,
    searched_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ── Outreach history ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS outreach_history (
    id              SERIAL PRIMARY KEY,
    user_id         TEXT,
    job_id          TEXT REFERENCES jobs(job_id) ON DELETE SET NULL,
    type            TEXT,  -- 'cover_letter' | 'outreach_email'
    content         TEXT,
    generated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Semantic search function: find similar jobs by embedding
CREATE OR REPLACE FUNCTION search_similar_jobs(
    query_embedding vector(1536),
    top_k INTEGER DEFAULT 20,
    min_score REAL DEFAULT 0.7
)
RETURNS TABLE (job_id TEXT, title TEXT, company TEXT, location TEXT, similarity REAL) AS $$
    SELECT job_id, title, company, location,
           1 - (embedding <=> query_embedding) AS similarity
    FROM jobs
    WHERE embedding IS NOT NULL
      AND is_likely_scam = FALSE
      AND 1 - (embedding <=> query_embedding) >= min_score
    ORDER BY embedding <=> query_embedding
    LIMIT top_k;
$$ LANGUAGE SQL STABLE;
