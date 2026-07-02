-- Migration 002: Opportunities Module
-- Run AFTER 001_users.sql
-- Tables: opportunities, job_opportunities, real_estate_opportunities,
--         vehicle_opportunities, immigration_opportunities

-- ─────────────────────────────────────────────────────────────────────────────
-- BASE OPPORTUNITIES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source
    source    VARCHAR(50)  NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    domain    VARCHAR(50)  NOT NULL,
    source_url TEXT,

    -- Content
    title       TEXT NOT NULL,
    description TEXT,
    raw_data    JSONB,
    normalized_data JSONB,

    -- Processing
    score      FLOAT,
    confidence FLOAT,

    -- Status
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('active','expired','archived','duplicate')),

    -- Dates
    posted_date  TIMESTAMP WITH TIME ZONE,
    expiry_date  TIMESTAMP WITH TIME ZONE,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_source_opportunity UNIQUE (source, source_id),
    CONSTRAINT valid_score      CHECK (score      IS NULL OR (score      >= 0 AND score      <= 1)),
    CONSTRAINT valid_confidence CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- JOBS
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS job_opportunities (
    opportunity_id UUID PRIMARY KEY REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,

    -- Company
    company_name      VARCHAR(255),
    company_id        VARCHAR(100),
    company_website   VARCHAR(500),
    company_industry  VARCHAR(100),
    company_size      VARCHAR(50),

    -- Job
    job_type        VARCHAR(50) CHECK (job_type IN ('full-time','part-time','contract','internship','freelance','remote')),
    experience_level VARCHAR(50) CHECK (experience_level IN ('entry','mid','senior','lead','executive')),
    education_level  VARCHAR(50),
    skills_required  TEXT[],
    languages_required TEXT[],

    -- Compensation
    salary_min      DECIMAL(12,2),
    salary_max      DECIMAL(12,2),
    salary_currency VARCHAR(3),
    salary_period   VARCHAR(20) CHECK (salary_period IN ('hourly','monthly','yearly')),

    -- Work
    visa_sponsorship BOOLEAN DEFAULT FALSE,
    remote_allowed   BOOLEAN DEFAULT FALSE,
    hybrid           BOOLEAN DEFAULT FALSE,

    -- Location
    location_country VARCHAR(100),
    location_city    VARCHAR(100),
    location_address TEXT,

    -- Application
    application_url      TEXT,
    application_deadline TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- REAL ESTATE
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS real_estate_opportunities (
    opportunity_id UUID PRIMARY KEY REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,

    property_type    VARCHAR(50) CHECK (property_type IN ('apartment','villa','townhouse','office','retail','land')),
    transaction_type VARCHAR(50) CHECK (transaction_type IN ('sale','rent','investment')),

    bedrooms       INTEGER,
    bathrooms      INTEGER,
    area_sqft      DECIMAL(10,2),
    furnished      BOOLEAN DEFAULT FALSE,
    year_built     INTEGER,
    parking_spaces INTEGER,

    price           DECIMAL(15,2),
    currency        VARCHAR(3),
    price_per_sqft  DECIMAL(10,2),
    security_deposit DECIMAL(10,2),

    amenities          TEXT[],
    location_country   VARCHAR(100),
    location_city      VARCHAR(100),
    location_area      VARCHAR(100),
    location_address   TEXT,
    latitude           DECIMAL(10,8),
    longitude          DECIMAL(11,8),

    agent_name    VARCHAR(200),
    agent_contact VARCHAR(50),
    developer_name VARCHAR(200),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- VEHICLES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS vehicle_opportunities (
    opportunity_id UUID PRIMARY KEY REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,

    make  VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    year  INTEGER NOT NULL,
    trim  VARCHAR(100),

    mileage      INTEGER,
    transmission VARCHAR(50) CHECK (transmission IN ('automatic','manual','cvt','other')),
    fuel_type    VARCHAR(50) CHECK (fuel_type IN ('petrol','diesel','electric','hybrid','cng','lpg')),
    engine_size  DECIMAL(4,1),
    color        VARCHAR(50),

    condition VARCHAR(50) CHECK (condition IN ('new','used','certified','damaged')),
    accident_history BOOLEAN DEFAULT FALSE,
    service_history  BOOLEAN DEFAULT FALSE,

    price    DECIMAL(15,2),
    currency VARCHAR(3),

    features TEXT[],

    location_country VARCHAR(100),
    location_city    VARCHAR(100),

    seller_type VARCHAR(50) CHECK (seller_type IN ('dealer','private','auction')),
    seller_name VARCHAR(200),
    vin         VARCHAR(17),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- IMMIGRATION
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS immigration_opportunities (
    opportunity_id UUID PRIMARY KEY REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,

    visa_type     VARCHAR(100) NOT NULL,
    visa_category VARCHAR(100),
    country       VARCHAR(100) NOT NULL,

    processing_time_days INTEGER,
    processing_fee       DECIMAL(10,2),
    fee_currency         VARCHAR(3),

    requirements         TEXT[],
    documents_required   TEXT[],
    eligibility_criteria TEXT[],
    minimum_income       DECIMAL(12,2),
    minimum_education    VARCHAR(100),
    minimum_experience   INTEGER,

    application_deadline TIMESTAMP WITH TIME ZONE,
    visa_validity_days   INTEGER,

    sponsorship_available BOOLEAN DEFAULT FALSE,
    official_link  TEXT,
    application_link TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_opp_domain        ON opportunities(domain);
CREATE INDEX IF NOT EXISTS idx_opp_status        ON opportunities(status);
CREATE INDEX IF NOT EXISTS idx_opp_source        ON opportunities(source, source_id);
CREATE INDEX IF NOT EXISTS idx_opp_posted_date   ON opportunities(posted_date DESC);
CREATE INDEX IF NOT EXISTS idx_opp_title_trgm    ON opportunities USING gin(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_opp_created_at    ON opportunities(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_country      ON job_opportunities(location_country);
CREATE INDEX IF NOT EXISTS idx_jobs_visa         ON job_opportunities(visa_sponsorship);
CREATE INDEX IF NOT EXISTS idx_re_country        ON real_estate_opportunities(location_country);
CREATE INDEX IF NOT EXISTS idx_re_type           ON real_estate_opportunities(property_type);
CREATE INDEX IF NOT EXISTS idx_veh_make          ON vehicle_opportunities(make, model);

-- ─────────────────────────────────────────────────────────────────────────────
-- AUTO-UPDATE TRIGGER
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE TRIGGER trg_opp_updated_at
    BEFORE UPDATE ON opportunities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
