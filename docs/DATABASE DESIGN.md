1. Database Overview
1.1 Design Principles
Normalization: 3NF for transactional tables

Denormalization: For performance-critical queries

Partitioning: Large tables by date

Indexing: Strategic indexes for query performance

Vector Storage: pgvector for semantic search

Audit Trail: Complete history of changes

Data Retention: Automated cleanup policies

1.2 ER Diagram
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ER DIAGRAM                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐      │
│  │    Users     │  1    1  │   Profiles   │  1    1  │  Preferences │      │
│  ├──────────────┤──────────├──────────────┤──────────├──────────────┤      │
│  │ user_id      │          │ user_id      │          │ user_id      │      │
│  │ email        │          │ country      │          │ country      │      │
│  │ phone        │          │ education    │          │ budgets      │      │
│  │ password_hash│          │ skills       │          │ companies    │      │
│  │ created_at   │          │ languages    │          │ universities │      │
│  └──────────────┘          └──────────────┘          └──────────────┘      │
│         │                           │                          │           │
│         │1                         │                          │           │
│         │                          │                          │           │
│         │N                         │                          │           │
│  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐      │
│  │Search History│          │ Notifications│          │   Sessions   │      │
│  ├──────────────┤          ├──────────────┤          ├──────────────┤      │
│  │ search_id    │          │ notif_id     │          │ session_id   │      │
│  │ user_id      │          │ user_id      │          │ user_id      │      │
│  │ query        │          │ channel      │          │ token        │      │
│  │ filters      │          │ message      │          │ expires_at   │      │
│  │ executed_at  │          │ status       │          └──────────────┘      │
│  └──────────────┘          └──────────────┘                                │
│                                                                             │
│  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐      │
│  │ Opportunities│ 1    1  │   Jobs       │          │  RealEstate  │      │
│  ├──────────────┤──────────├──────────────┤          ├──────────────┤      │
│  │ opp_id       │          │ opp_id       │          │ opp_id       │      │
│  │ source       │          │ company_name │          │ property_type│      │
│  │ source_id    │          │ company_id   │          │ bedrooms     │      │
│  │ domain       │          │ job_type     │          │ area_sqft    │      │
│  │ title        │          │ experience   │          │ year_built   │      │
│  │ description  │          │ visa_sponsor │          │ price        │      │
│  │ embedding    │          └──────────────┘          └──────────────┘      │
│  │ score        │                                                         │
│  │ status       │          ┌──────────────┐          ┌──────────────┐      │
│  │ posted_date  │          │   Vehicles   │          │  Immigration │      │
│  │ expiry_date  │          ├──────────────┤          ├──────────────┤      │
│  └──────────────┘          │ opp_id       │          │ opp_id       │      │
│         │                  │ make         │          │ visa_type    │      │
│         │                  │ model        │          │ country      │      │
│         │                  │ year         │          │ processing   │      │
│         │                  │ price        │          │ requirements │      │
│         │                  └──────────────┘          └──────────────┘      │
│         │                                                                  │
│         │N                 ┌──────────────┐          ┌──────────────┐      │
│         │                  │  Education   │          │ Scholarships │      │
│         └─────────────────►├──────────────┤          ├──────────────┤      │
│                            │ opp_id       │          │ opp_id       │      │
│                            │ university   │          │ provider     │      │
│                            │ program      │          │ amount       │      │
│                            │ ranking      │          │ deadline     │      │
│                            │ tuition      │          │ eligibility  │      │
│                            └──────────────┘          └──────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
2. Schema Design
2.1 Users Module
sql
-- Users Table
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    avatar_url VARCHAR(500),
    
    -- Status flags
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    user_agent VARCHAR(255),
    ip_address INET,
    preferences JSONB,
    
    -- Indexes
    CONSTRAINT users_email_check CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT users_phone_check CHECK (phone ~* '^\+?[1-9]\d{1,14}$')
);

-- User Profiles
CREATE TABLE user_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Personal Information
    country VARCHAR(100),
    city VARCHAR(100),
    date_of_birth DATE,
    gender VARCHAR(20),
    nationality VARCHAR(100),
    
    -- Education
    education_level VARCHAR(50),
    degree VARCHAR(100),
    field_of_study VARCHAR(100),
    institution VARCHAR(200),
    graduation_year INTEGER,
    
    -- Professional
    experience_years INTEGER,
    current_title VARCHAR(100),
    current_company VARCHAR(200),
    skills TEXT[],
    languages TEXT[],
    
    -- Preferences
    visa_status VARCHAR(50),
    preferred_countries TEXT[],
    preferred_cities TEXT[],
    budget_range JSONB,
    salary_range JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_experience CHECK (experience_years >= 0),
    CONSTRAINT valid_graduation CHECK (graduation_year >= 1900 AND graduation_year <= EXTRACT(YEAR FROM CURRENT_DATE) + 5)
);

-- User Preferences
CREATE TABLE user_preferences (
    preference_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Notification Preferences
    notifications_enabled BOOLEAN DEFAULT TRUE,
    notification_channels TEXT[] DEFAULT ARRAY['email', 'whatsapp'],
    email_notifications BOOLEAN DEFAULT TRUE,
    whatsapp_notifications BOOLEAN DEFAULT TRUE,
    
    -- Frequency Settings
    daily_summary BOOLEAN DEFAULT TRUE,
    weekly_summary BOOLEAN DEFAULT TRUE,
    real_time_alerts BOOLEAN DEFAULT TRUE,
    
    -- Domain Preferences
    domains TEXT[] DEFAULT ARRAY['jobs', 'real_estate', 'vehicles', 'education', 'immigration'],
    
    -- Custom Filters
    custom_filters JSONB,
    saved_searches JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
2.2 Opportunities Module
sql
-- Base Opportunities Table
CREATE TABLE opportunities (
    opportunity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source Information
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    domain VARCHAR(50) NOT NULL,
    source_url TEXT,
    
    -- Content
    title TEXT NOT NULL,
    description TEXT,
    raw_data JSONB,
    normalized_data JSONB,
    
    -- Processing
    embedding vector(768),
    score FLOAT,
    confidence FLOAT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'expired', 'archived', 'duplicate')),
    
    -- Dates
    posted_date TIMESTAMP WITH TIME ZONE,
    expiry_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_source_opportunity UNIQUE (source, source_id),
    CONSTRAINT valid_score CHECK (score >= 0 AND score <= 1),
    CONSTRAINT valid_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

-- Jobs Domain
CREATE TABLE job_opportunities (
    opportunity_id UUID PRIMARY KEY REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    
    -- Company
    company_name VARCHAR(255),
    company_id VARCHAR(100),
    company_website VARCHAR(500),
    company_linkedin VARCHAR(500),
    company_industry VARCHAR(100),
    company_size VARCHAR(50),
    
    -- Job Details
    job_type VARCHAR(50) CHECK (job_type IN ('full-time', 'part-time', 'contract', 'internship', 'freelance', 'remote')),
    experience_level VARCHAR(50) CHECK (experience_level IN ('entry', 'mid', 'senior', 'lead', 'executive')),
    education_level VARCHAR(50),
    skills_required TEXT[],
    languages_required TEXT[],
    
    -- Compensation
    salary_min DECIMAL(12,2),
    salary_max DECIMAL(12,2),
    salary_currency VARCHAR(3),
    salary_period VARCHAR(20) CHECK (salary_period IN ('hourly', 'monthly', 'yearly')),
    
    -- Work Details
    visa_sponsorship BOOLEAN DEFAULT FALSE,
    remote_allowed BOOLEAN DEFAULT FALSE,
    hybrid BOOLEAN DEFAULT FALSE,
    
    -- Location
    location_country VARCHAR(100),
    location_city VARCHAR(100),
    location_address TEXT,
    remote_country VARCHAR(100),
    
    -- Application
    application_url TEXT,
    application_deadline TIMESTAMP WITH TIME ZONE,
    application_process TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Real Estate Domain
CREATE TABLE real_estate_opportunities (
    opportunity_id UUID PRIMARY KEY REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    
    -- Property Details
    property_type VARCHAR(50) CHECK (property_type IN ('apartment', 'villa', 'townhouse', 'office', 'retail', 'land')),
    transaction_type VARCHAR(50) CHECK (transaction_type IN ('sale', 'rent', 'investment')),
    
    -- Specifications
    bedrooms INTEGER,
    bathrooms INTEGER,
    area_sqft DECIMAL(10,2),
    land_area_sqft DECIMAL(10,2),
    furnished BOOLEAN DEFAULT FALSE,
    year_built INTEGER,
    parking_spaces INTEGER,
    
    -- Pricing
    price DECIMAL(15,2),
    currency VARCHAR(3),
    price_per_sqft DECIMAL(10,2),
    maintenance_fee DECIMAL(10,2),
    security_deposit DECIMAL(10,2),
    
    -- Features
    amenities TEXT[],
    property_features TEXT[],
    
    -- Location
    location_country VARCHAR(100),
    location_city VARCHAR(100),
    location_area VARCHAR(100),
    location_address TEXT,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    
    -- Agent/Developer
    agent_name VARCHAR(200),
    agent_contact VARCHAR(50),
    agent_license VARCHAR(50),
    developer_name VARCHAR(200),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Vehicles Domain
CREATE TABLE vehicle_opportunities (
    opportunity_id UUID PRIMARY KEY REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    
    -- Vehicle Details
    make VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    year INTEGER NOT NULL,
    trim VARCHAR(100),
    generation VARCHAR(50),
    
    -- Specifications
    mileage INTEGER,
    transmission VARCHAR(50) CHECK (transmission IN ('automatic', 'manual', 'cvt', 'other')),
    fuel_type VARCHAR(50) CHECK (fuel_type IN ('petrol', 'diesel', 'electric', 'hybrid', 'cng', 'lpg')),
    engine_size DECIMAL(4,1),
    engine_cylinders INTEGER,
    horsepower INTEGER,
    color VARCHAR(50),
    interior_color VARCHAR(50),
    number_of_doors INTEGER,
    seating_capacity INTEGER,
    
    -- Condition
    condition VARCHAR(50) CHECK (condition IN ('new', 'used', 'certified', 'damaged')),
    damage_description TEXT,
    accident_history BOOLEAN DEFAULT FALSE,
    service_history BOOLEAN DEFAULT FALSE,
    
    -- Pricing
    price DECIMAL(15,2),
    currency VARCHAR(3),
    original_price DECIMAL(15,2),
    
    -- Features
    features TEXT[],
    safety_features TEXT[],
    entertainment_features TEXT[],
    
    -- Location
    location_country VARCHAR(100),
    location_city VARCHAR(100),
    location_address TEXT,
    
    -- Seller
    seller_type VARCHAR(50) CHECK (seller_type IN ('dealer', 'private', 'auction')),
    seller_name VARCHAR(200),
    seller_contact VARCHAR(50),
    
    -- VIN
    vin VARCHAR(17),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Immigration Domain
CREATE TABLE immigration_opportunities (
    opportunity_id UUID PRIMARY KEY REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    
    -- Visa Details
    visa_type VARCHAR(100) NOT NULL,
    visa_category VARCHAR(100),
    visa_subcategory VARCHAR(100),
    country VARCHAR(100) NOT NULL,
    
    -- Processing
    processing_time_days INTEGER,
    processing_fee DECIMAL(10,2),
    fee_currency VARCHAR(3),
    quota INTEGER,
    
    -- Requirements
    requirements TEXT[],
    documents_required TEXT[],
    eligibility_criteria TEXT[],
    points_required INTEGER,
    minimum_income DECIMAL(12,2),
    minimum_education VARCHAR(100),
    minimum_experience INTEGER,
    
    -- Dates
    application_start_date TIMESTAMP WITH TIME ZONE,
    application_deadline TIMESTAMP WITH TIME ZONE,
    decision_date TIMESTAMP WITH TIME ZONE,
    visa_validity_days INTEGER,
    
    -- Sponsorship
    sponsorship_available BOOLEAN DEFAULT FALSE,
    sponsor_list TEXT[],
    
    -- Links
    official_link TEXT,
    application_link TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
2.3 Audit & Logs
sql
-- Audit Logs
CREATE TABLE audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Context
    user_id UUID REFERENCES users(user_id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    
    -- Details
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    
    -- Result
    status VARCHAR(20) DEFAULT 'success' CHECK (status IN ('success', 'failure', 'pending')),
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Index for partitioning
    created_date DATE GENERATED ALWAYS AS (DATE(created_at)) STORED
) PARTITION BY RANGE (created_date);

-- Notification Logs
CREATE TABLE notification_logs (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Target
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    opportunity_id UUID REFERENCES opportunities(opportunity_id),
    
    -- Content
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('email', 'whatsapp', 'web', 'push')),
    message TEXT NOT NULL,
    template_id VARCHAR(100),
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'delivered', 'read', 'failed')),
    error_message TEXT,
    
    -- Timestamps
    scheduled_at TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Search History
CREATE TABLE search_history (
    search_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Query
    query TEXT NOT NULL,
    query_type VARCHAR(50) DEFAULT 'text' CHECK (query_type IN ('text', 'voice', 'image')),
    filters JSONB,
    intent JSONB,
    
    -- Results
    result_ids UUID[],
    result_count INTEGER,
    clicked_result_id UUID,
    clicked_at TIMESTAMP WITH TIME ZONE,
    
    -- Session
    session_id UUID,
    referrer TEXT,
    
    -- Timestamps
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- System Logs
CREATE TABLE system_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Log Details
    level VARCHAR(20) NOT NULL CHECK (level IN ('debug', 'info', 'warning', 'error', 'critical')),
    component VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    
    -- Context
    context JSONB,
    request_id UUID,
    trace_id VARCHAR(64),
    span_id VARCHAR(64),
    
    -- Details
    exception TEXT,
    stack_trace TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
3. Vector Search Implementation
3.1 pgvector Setup
sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create embedding table
CREATE TABLE embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    embedding vector(768) NOT NULL,
    model VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(opportunity_id, model, version)
);

-- Vector similarity search function
CREATE OR REPLACE FUNCTION search_similar_opportunities(
    query_embedding vector(768),
    limit_count INTEGER DEFAULT 20,
    domain_filter VARCHAR(50) DEFAULT NULL
) RETURNS TABLE(
    opportunity_id UUID,
    title TEXT,
    domain VARCHAR(50),
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        o.opportunity_id,
        o.title,
        o.domain,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM opportunities o
    INNER JOIN embeddings e ON o.opportunity_id = e.opportunity_id
    WHERE o.status = 'active'
        AND (domain_filter IS NULL OR o.domain = domain_filter)
    ORDER BY e.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;
3.2 Index Creation
sql
-- Create index for vector similarity search
CREATE INDEX idx_embeddings_embedding ON embeddings 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Create index for exact nearest neighbor search
CREATE INDEX idx_embeddings_embedding_hnsw ON embeddings 
    USING hnsw (embedding vector_cosine_ops);

-- Refresh index periodically
CREATE OR REPLACE FUNCTION refresh_embedding_index()
RETURNS void AS $$
BEGIN
    REINDEX INDEX CONCURRENTLY idx_embeddings_embedding;
END;
$$ LANGUAGE plpgsql;
4. Materialized Views
sql
-- Active opportunities by domain and source
CREATE MATERIALIZED VIEW mv_domain_source_stats AS
SELECT 
    domain,
    source,
    COUNT(*) as count,
    AVG(score) as avg_score,
    MIN(posted_date) as oldest_post,
    MAX(posted_date) as newest_post,
    COUNT(DISTINCT EXTRACT(DAY FROM posted_date) || '-' || EXTRACT(MONTH FROM posted_date)) as days_active
FROM opportunities
WHERE status = 'active'
    AND expiry_date > NOW()
GROUP BY domain, source
WITH NO DATA;

CREATE UNIQUE INDEX idx_mv_domain_source ON mv_domain_source_stats (domain, source);

REFRESH MATERIALIZED VIEW CONCURRENTLY mv_domain_source_stats;

-- User engagement summary
CREATE MATERIALIZED VIEW mv_user_engagement AS
SELECT 
    u.user_id,
    u.email,
    COUNT(DISTINCT sh.search_id) as total_searches,
    COUNT(DISTINCT sh.executed_at::DATE) as active_days,
    COUNT(DISTINCT nl.notification_id) as total_notifications,
    COUNT(DISTINCT CASE WHEN nl.status = 'read' THEN nl.notification_id END) as read_notifications,
    AVG(CASE WHEN nl.read_at IS NOT NULL 
        AND nl.sent_at IS NOT NULL 
        AND nl.read_at > nl.sent_at 
        THEN EXTRACT(EPOCH FROM (nl.read_at - nl.sent_at)) 
        END) as avg_read_time_seconds,
    MAX(sh.executed_at) as last_seen
FROM users u
LEFT JOIN search_history sh ON u.user_id = sh.user_id
LEFT JOIN notification_logs nl ON u.user_id = nl.user_id
GROUP BY u.user_id, u.email
WITH NO DATA;
5. Backup & Recovery
5.1 Backup Strategy
sql
-- Backup configuration
CREATE TABLE backup_config (
    config_id INTEGER PRIMARY KEY DEFAULT 1,
    backup_enabled BOOLEAN DEFAULT TRUE,
    retention_days INTEGER DEFAULT 30,
    compression_enabled BOOLEAN DEFAULT TRUE,
    encryption_enabled BOOLEAN DEFAULT TRUE,
    backup_schedule VARCHAR(20) DEFAULT '0 2 * * *',
    last_backup_timestamp TIMESTAMP WITH TIME ZONE,
    backup_path VARCHAR(500)
);

-- Backup function
CREATE OR REPLACE FUNCTION perform_backup()
RETURNS void AS $$
DECLARE
    backup_name VARCHAR(100);
    backup_path VARCHAR(500);
BEGIN
    backup_name := 'backup_' || TO_CHAR(NOW(), 'YYYYMMDD_HH24MI');
    backup_path := '/backups/' || backup_name || '.sql';
    
    -- Create backup file
    EXECUTE format('COPY (SELECT * FROM opportunities) TO %L WITH CSV HEADER', backup_path || '_opportunities.csv');
    EXECUTE format('COPY (SELECT * FROM users) TO %L WITH CSV HEADER', backup_path || '_users.csv');
    
    -- Update backup config
    UPDATE backup_config 
    SET last_backup_timestamp = NOW() 
    WHERE config_id = 1;
    
    -- Clean old backups
    PERFORM clean_old_backups();
END;
$$ LANGUAGE plpgsql;
5.2 Disaster Recovery
sql
-- Recovery procedure
CREATE OR REPLACE FUNCTION recover_from_backup(
    backup_timestamp TIMESTAMP WITH TIME ZONE
) RETURNS void AS $$
DECLARE
    backup_id VARCHAR(100);
BEGIN
    backup_id := 'backup_' || TO_CHAR(backup_timestamp, 'YYYYMMDD_HH24MI');
    
    -- Start transaction
    BEGIN;
    
    -- Truncate tables
    TRUNCATE TABLE opportunities CASCADE;
    TRUNCATE TABLE users CASCADE;
    
    -- Load data from backup
    EXECUTE format('COPY opportunities FROM %L WITH CSV HEADER', '/backups/' || backup_id || '_opportunities.csv');
    EXECUTE format('COPY users FROM %L WITH CSV HEADER', '/backups/' || backup_id || '_users.csv');
    
    -- Validate data
    PERFORM validate_loaded_data();
    
    -- Commit
    COMMIT;
    
    -- Rebuild indexes
    REINDEX DATABASE wildautomations;
    
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        RAISE;
END;
$$ LANGUAGE plpgsql;
6. Data Retention Policy
sql
-- Retention policy configuration
CREATE TABLE retention_policy (
    policy_id INTEGER PRIMARY KEY DEFAULT 1,
    domain VARCHAR(50) NOT NULL,
    retention_days INTEGER NOT NULL,
    archive_enabled BOOLEAN DEFAULT TRUE,
    delete_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(domain)
);

INSERT INTO retention_policy (domain, retention_days) VALUES
    ('jobs', 180),
    ('real_estate', 90),
    ('vehicles', 60),
    ('immigration', 365),
    ('education', 365),
    ('scholarships', 180);

-- Cleanup function
CREATE OR REPLACE FUNCTION cleanup_expired_data()
RETURNS void AS $$
DECLARE
    policy RECORD;
BEGIN
    FOR policy IN SELECT * FROM retention_policy
    LOOP
        -- Archive expired opportunities
        IF policy.archive_enabled THEN
            INSERT INTO archived_opportunities
            SELECT * FROM opportunities
            WHERE domain = policy.domain
                AND (expiry_date < NOW() - (policy.retention_days || ' days')::INTERVAL
                    OR posted_date < NOW() - (policy.retention_days * 2 || ' days')::INTERVAL);
        END IF;
        
        -- Delete expired opportunities
        IF policy.delete_enabled THEN
            DELETE FROM opportunities
            WHERE domain = policy.domain
                AND (expiry_date < NOW() - (policy.retention_days || ' days')::INTERVAL
                    OR posted_date < NOW() - (policy.retention_days * 2 || ' days')::INTERVAL);
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;