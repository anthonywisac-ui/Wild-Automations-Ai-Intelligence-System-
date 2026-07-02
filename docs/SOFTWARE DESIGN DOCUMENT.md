1. Architecture Overview
1.1 Design Goals
Modularity: Clear separation of concerns for maintainability

Scalability: Support for growing data and user base

Extensibility: Easy addition of new sources and features

Resilience: Graceful degradation under failure conditions

Cost-Efficiency: Optimized resource utilization

1.2 System Context Diagram
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SYSTEMS                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                    │
│  │  Data Sources │  │  AI Providers│  │  Messaging  │                    │
│  │  (LinkedIn,  │  │  (Gemini,    │  │  (WhatsApp, │                    │
│  │  Dubizzle,   │  │  Claude,     │  │  Twilio)    │                    │
│  │  etc.)       │  │  GPT, etc.)  │  │             │                    │
│  └──────────────┘  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WILDAUTOMATIONS PLATFORM                               │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                     API Gateway/FastAPI                             │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │ │
│  │  │  Auth    │  │  Search  │  │  Profile │  │  Admin           │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘   │ │
│  ├──────────────────────────────────────────────────────────────────────┤ │
│  │                    Business Logic Layer                            │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │ │
│  │  │ AI/ML    │  │  Worker  │  │  Notify  │  │  Orchestration   │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘   │ │
│  ├──────────────────────────────────────────────────────────────────────┤ │
│  │                    Data Access Layer                               │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │ │
│  │  │  Repo    │  │  Cache   │  │  Queue   │  │  Vector Store    │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘   │ │
│  ├──────────────────────────────────────────────────────────────────────┤ │
│  │                    Data Collection Layer                           │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │ │
│  │  │  Scraper │  │  Parser  │  │  Normal  │  │  Dedupe          │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘   │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA STORAGE                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                    │
│  │  PostgreSQL  │  │    Redis     │  │  S3 Storage  │                    │
│  │  (PgVector)  │  │   (Cache)    │  │   (Objects)  │                    │
│  └──────────────┘  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
1.3 Module Interactions
text
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Web Client  │◄──►│   FastAPI    │◄──►│  PostgreSQL  │
└──────────────┘    │              │    └──────────────┘
                    │              │◄──►    Redis
┌──────────────┐    │              │    ┌──────────────┐
│ WhatsApp Bot │◄──►│              │    │  Celery      │
└──────────────┘    │              │    │  Workers     │
                    └──────────────┘    └──────────────┘
                              ▲                  ▲
                              │                  │
                    ┌──────────────┐    ┌──────────────┐
                    │  AI Pipeline │    │  Scrapers    │
                    └──────────────┘    └──────────────┘
2. Module Design
2.1 Core Modules (Existing)
scraper_engine.py
Purpose: Orchestrates data collection from various sources
Responsibilities:

Source configuration loading

Strategy selection (HTTP, Browser, Apify)

Retry and error handling

Throttle management

robots.txt compliance

Interfaces:

python
class ScraperEngine:
    def configure_source(source_config: SourceConfig) -> None
    def scrape(source: Source, params: ScrapeParams) -> ScrapeResult
    def schedule_scrape(source: Source, schedule: Schedule) -> None
    def get_status(source: Source) -> ScrapeStatus
apify_client.py
Purpose: Manages Apify integration
Responsibilities:

Actor execution

Result retrieval

Cost tracking

Error handling

Interfaces:

python
class ApifyClient:
    def run_actor(actor_id: str, input_data: dict) -> ActorRun
    def get_result(run_id: str) -> dict
    def get_status(run_id: str) -> str
    def cancel_run(run_id: str) -> bool
scoring_engine.py
Purpose: Scores and ranks opportunities
Responsibilities:

User profile matching

Similarity calculation

Confidence scoring

Ranking optimization

Interfaces:

python
class ScoringEngine:
    def score_opportunity(opportunity: Opportunity, profile: UserProfile) -> Score
    def rank_opportunities(opportunities: List[Opportunity], profile: UserProfile) -> List[RankedOpportunity]
    def get_explanation(score: Score) -> str
dedupe_engine.py
Purpose: Removes duplicate opportunities
Responsibilities:

Source-level deduplication

Cross-source deduplication

Content similarity detection

Manual review queue

Interfaces:

python
class DedupeEngine:
    def is_duplicate(opportunity: Opportunity, existing: List[Opportunity]) -> bool
    def resolve_duplicates(opportunities: List[Opportunity]) -> List[Opportunity]
    def get_duplicates(opportunity: Opportunity) -> List[Opportunity]
database_layer.py
Purpose: Database access and management
Responsibilities:

CRUD operations

Connection management

Transaction handling

Query optimization

Interfaces:

python
class DatabaseLayer:
    def create_opportunity(opportunity: dict) -> Opportunity
    def get_opportunity(id: str) -> Opportunity
    def update_opportunity(id: str, data: dict) -> Opportunity
    def delete_opportunity(id: str) -> bool
    def search_opportunities(query: SearchQuery) -> List[Opportunity]
ai_processor.py
Purpose: AI/ML processing pipeline
Responsibilities:

Intent recognition

Opportunity extraction

Response generation

Model management

Interfaces:

python
class AIProcessor:
    def detect_intent(text: str) -> Intent
    def extract_opportunity(text: str) -> Opportunity
    def generate_response(query: str, context: dict) -> str
    def select_model(task: Task) -> Model
delivery_engine.py
Purpose: Opportunity delivery management
Responsibilities:

Notification formatting

Channel selection

Delivery tracking

Delivery confirmation

Interfaces:

python
class DeliveryEngine:
    def deliver_notification(user: User, opportunity: Opportunity) -> Delivery
    def format_message(opportunity: Opportunity, template: str) -> str
    def track_delivery(delivery_id: str) -> DeliveryStatus
    def handle_failure(delivery: Delivery) -> None
2.2 New Modules to Add
search_engine.py
Purpose: Advanced search capabilities
Responsibilities:

Semantic search

Keyword search

Hybrid search

Search caching

Interfaces:

python
class SearchEngine:
    def semantic_search(query: str, filters: Filters) -> SearchResult
    def keyword_search(query: str, filters: Filters) -> SearchResult
    def hybrid_search(query: str, filters: Filters) -> SearchResult
    def get_search_suggestions(query: str) -> List[str]
notification_manager.py
Purpose: Notification management
Responsibilities:

Notification scheduling

User preference matching

Channel routing

Notification tracking

Interfaces:

python
class NotificationManager:
    def schedule_notification(user: User, opportunity: Opportunity) -> Notification
    def send_now(user: User, opportunity: Opportunity) -> bool
    def process_queue() -> None
    def update_preferences(user: User, preferences: dict) -> None
user_profile_service.py
Purpose: User profile management
Responsibilities:

Profile CRUD

Preference matching

Profile analytics

Behavior tracking

Interfaces:

python
class UserProfileService:
    def create_profile(user_id: str, data: dict) -> UserProfile
    def get_profile(user_id: str) -> UserProfile
    def update_profile(user_id: str, data: dict) -> UserProfile
    def get_matching_opportunities(user_id: str) -> List[Opportunity]
admin_service.py
Purpose: Administration functionality
Responsibilities:

System monitoring

Source management

User management

Analytics reporting

Interfaces:

python
class AdminService:
    def get_system_health() -> HealthStatus
    def get_scraper_status(source: Source) -> ScraperStatus
    def manage_user(user_id: str, action: str) -> bool
    def get_analytics(params: AnalyticsParams) -> Analytics
3. Data Flow Design
3.1 Data Collection Flow
text
┌─────────────────────────────────────────────────────────────────┐
│                         SCHEDULER                              │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │  Source 1    │    │  Source 2    │    │  Source N    │     │
│  │  Scheduled   │    │  Scheduled   │    │  Scheduled   │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SCRAPER ENGINE                            │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │  Strategy    │    │  Strategy    │    │  Strategy    │     │
│  │  Selection   │───►│  Execution   │───►│  Result      │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AI PROCESSING PIPELINE                    │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐  │
│  │ Extract  │───►│ Normalize│───►│ Validate │───►│Score    │  │
│  └──────────┘    └──────────┘    └──────────┘    └─────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DEDUPLICATION                            │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                 │
│  │  Check   │───►│  Resolve │───►│  Final   │                 │
│  └──────────┘    └──────────┘    └──────────┘                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE STORAGE                            │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                 │
│  │  Insert  │───►│  Embed   │───►│  Index   │                 │
│  └──────────┘    └──────────┘    └──────────┘                 │
└─────────────────────────────────────────────────────────────────┘
3.2 User Search Flow
text
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   User Query │───►│   Intent     │───►│   AI Model   │
│   (Natural   │    │  Detection   │    │  Selection   │
│   Language)  │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
                                                  │
                                                  ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Database   │◄───│   Search     │◄───│   Query      │
│   Query      │    │   Execution  │    │   Processing │
└──────────────┘    └──────────────┘    └──────────────┘
      │
      ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Results    │───►│   Ranking    │───►│   Response   │
│   Retrieved  │    │   & Scoring  │    │   Generation │
└──────────────┘    └──────────────┘    └──────────────┘
3.3 Notification Flow
text
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  New         │───►│  Match       │───►│  User        │
│  Opportunity │    │  Detection   │    │  Selection   │
└──────────────┘    └──────────────┘    └──────────────┘
                                                  │
                                                  ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Channel     │◄───│  Preference  │◄───│  Format      │
│  Selection   │    │  Check       │    │  Message     │
└──────────────┘    └──────────────┘    └──────────────┘
      │
      ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Send        │───►│  Track       │───►│  Confirm     │
│  Notification│    │  Delivery    │    │  Delivery    │
└──────────────┘    └──────────────┘    └──────────────┘
4. API Design
4.1 RESTful API Structure
text
Base URL: https://api.wildautomations.com/v1

Authentication: Bearer JWT

Endpoints:
├── /auth
│   ├── POST /register
│   ├── POST /login
│   ├── POST /refresh
│   └── POST /logout
├── /profile
│   ├── GET /{user_id}
│   ├── PUT /{user_id}
│   ├── POST /preferences
│   └── GET /preferences
├── /search
│   ├── POST /query
│   ├── POST /advanced
│   └── GET /suggestions
├── /opportunities
│   ├── GET /{opportunity_id}
│   ├── GET /saved
│   ├── POST /save
│   └── DELETE /save/{id}
├── /notifications
│   ├── GET /active
│   ├── POST /subscribe
│   └── DELETE /unsubscribe
├── /admin
│   ├── GET /health
│   ├── GET /metrics
│   ├── GET /sources
│   ├── PUT /sources/{id}
│   └── GET /users
└── /whatsapp
    ├── POST /webhook
    └── GET /status
4.2 API Examples
Search Query
http
POST /api/v1/search/query
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "Data Science visa sponsorship jobs in Germany",
  "filters": {
    "country": "Germany",
    "visa_sponsorship": true,
    "industry": "technology"
  },
  "limit": 20,
  "offset": 0
}
Response
http
200 OK
{
  "results": [
    {
      "id": "opp_123",
      "title": "Senior Data Scientist",
      "company": "TechCorp GmbH",
      "location": {
        "country": "Germany",
        "city": "Berlin"
      },
      "salary": {
        "min": 85000,
        "max": 110000,
        "currency": "EUR"
      },
      "visa_sponsorship": true,
      "match_score": 0.94,
      "posted_date": "2024-01-15T10:00:00Z"
    }
  ],
  "pagination": {
    "total": 156,
    "limit": 20,
    "offset": 0
  },
  "meta": {
    "processing_time": 1.2
  }
}
5. Database Design
5.1 Schema Overview
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATABASE SCHEMA                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐     │
│  │   Users    │    │  Profiles  │    │ Preferences│    │  Sessions  │     │
│  └────────────┘    └────────────┘    └────────────┘    └────────────┘     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐     │
│  │Opportunity │    │   Jobs     │    │  RealEstate│    │  Vehicles  │     │
│  │    Base    │    │  Specific  │    │  Specific  │    │  Specific  │     │
│  └────────────┘    └────────────┘    └────────────┘    └────────────┘     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐     │
│  │Immigration │    │ Education  │    │Scholarship │    │  Auctions  │     │
│  │  Specific  │    │  Specific  │    │  Specific  │    │  Specific  │     │
│  └────────────┘    └────────────┘    └────────────┘    └────────────┘     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐     │
│  │   Search   │    │    Audit   │    │Notification│    │  Analytics │     │
│  │   History  │    │    Logs    │    │    Logs    │    │    Data    │     │
│  └────────────┘    └────────────┘    └────────────┘    └────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
5.2 Core Tables
Users Table
sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255),
    full_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    role VARCHAR(20) DEFAULT 'user'
);
Profiles Table
sql
CREATE TABLE profiles (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    country VARCHAR(100),
    city VARCHAR(100),
    education JSONB,
    experience JSONB,
    skills TEXT[],
    languages TEXT[],
    visa_status VARCHAR(50),
    budget_range JSONB,
    salary_range JSONB,
    preferences JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
Opportunities Base Table
sql
CREATE TABLE opportunities (
    opportunity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    domain VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    url TEXT,
    status VARCHAR(20) DEFAULT 'active',
    raw_data JSONB,
    normalized_data JSONB,
    embedding vector(768),
    score FLOAT,
    posted_date TIMESTAMP WITH TIME ZONE,
    expiry_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(source, source_id)
);
Domain-Specific Tables
sql
-- Jobs Specific Table
CREATE TABLE job_opportunities (
    opportunity_id UUID PRIMARY KEY REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    company_name VARCHAR(255),
    company_id VARCHAR(100),
    job_type VARCHAR(50),
    experience_level VARCHAR(50),
    education_level VARCHAR(50),
    skills_required TEXT[],
    salary_min DECIMAL(10,2),
    salary_max DECIMAL(10,2),
    salary_currency VARCHAR(3),
    salary_period VARCHAR(20),
    visa_sponsorship BOOLEAN DEFAULT FALSE,
    remote_allowed BOOLEAN DEFAULT FALSE,
    application_url TEXT,
    application_deadline TIMESTAMP WITH TIME ZONE
);
Search History Table
sql
CREATE TABLE search_history (
    search_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    filters JSONB,
    result_ids UUID[],
    result_count INTEGER,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
Notification Logs Table
sql
CREATE TABLE notification_logs (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    opportunity_id UUID REFERENCES opportunities(opportunity_id),
    channel VARCHAR(20) NOT NULL,
    message TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
5.3 Indexes
sql
-- Core indexes for performance
CREATE INDEX idx_opportunities_domain_status ON opportunities(domain, status);
CREATE INDEX idx_opportunities_source ON opportunities(source);
CREATE INDEX idx_opportunities_source_id ON opportunities(source_id);
CREATE INDEX idx_opportunities_posted_date ON opportunities(posted_date);
CREATE INDEX idx_opportunities_expiry_date ON opportunities(expiry_date);

-- Vector search indexes
CREATE INDEX idx_opportunities_embedding ON opportunities 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Search indexes
CREATE INDEX idx_opportunities_title_gin ON opportunities 
    USING gin(to_tsvector('english', title));

CREATE INDEX idx_opportunities_description_gin ON opportunities 
    USING gin(to_tsvector('english', description));

-- User indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_profiles_user_id ON profiles(user_id);

-- Job indexes
CREATE INDEX idx_jobs_company_name ON job_opportunities(company_name);
CREATE INDEX idx_jobs_visa_sponsorship ON job_opportunities(visa_sponsorship);

-- Search history indexes
CREATE INDEX idx_search_history_user_id ON search_history(user_id);
CREATE INDEX idx_search_history_executed_at ON search_history(executed_at);

-- Notification indexes
CREATE INDEX idx_notifications_user_id ON notification_logs(user_id);
CREATE INDEX idx_notifications_status ON notification_logs(status);
CREATE INDEX idx_notifications_sent_at ON notification_logs(sent_at);
5.4 Materialized Views
sql
-- Active opportunities by domain
CREATE MATERIALIZED VIEW active_opportunities_by_domain AS
SELECT 
    domain,
    COUNT(*) as count,
    AVG(score) as avg_score,
    MIN(posted_date) as oldest,
    MAX(posted_date) as newest
FROM opportunities
WHERE status = 'active'
AND expiry_date > NOW()
GROUP BY domain;

REFRESH MATERIALIZED VIEW active_opportunities_by_domain;

-- User activity summary
CREATE MATERIALIZED VIEW user_activity_summary AS
SELECT 
    u.user_id,
    u.email,
    COUNT(DISTINCT sh.search_id) as total_searches,
    COUNT(DISTINCT nl.notification_id) as total_notifications,
    MAX(sh.executed_at) as last_search,
    MAX(nl.sent_at) as last_notification
FROM users u
LEFT JOIN search_history sh ON u.user_id = sh.user_id
LEFT JOIN notification_logs nl ON u.user_id = nl.user_id
GROUP BY u.user_id, u.email;
5.5 Partitioning Strategy
sql
-- Partition opportunities by year
CREATE TABLE opportunities_partitioned (
    opportunity_id UUID NOT NULL,
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    domain VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    url TEXT,
    status VARCHAR(20) DEFAULT 'active',
    raw_data JSONB,
    normalized_data JSONB,
    embedding vector(768),
    score FLOAT,
    posted_date TIMESTAMP WITH TIME ZONE NOT NULL,
    expiry_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (opportunity_id, posted_date)
) PARTITION BY RANGE (posted_date);

-- Create partitions for each year
CREATE TABLE opportunities_2024 PARTITION OF opportunities_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
    
CREATE TABLE opportunities_2025 PARTITION OF opportunities_partitioned
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
5.6 Backup Strategy
sql
-- Daily backup script
CREATE OR REPLACE FUNCTION backup_database() RETURNS void AS $$
BEGIN
    PERFORM pg_backup_start('daily_backup', false);
    -- Perform backup operations
    -- Compress and encrypt backup
    -- Store to S3
    -- Verify backup
    -- Cleanup old backups
END;
$$ LANGUAGE plpgsql;

-- Schedule backup (via pg_cron)
SELECT cron.schedule('daily-backup', '0 2 * * *', 'SELECT backup_database();');
6. Component Interactions
6.1 Scraping Flow Sequence
text
┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐
│  Scheduler │   │  Scraper   │   │  AI        │   │  Database  │
│            │   │  Engine    │   │  Processor │   │  Layer     │
└────────────┘   └────────────┘   └────────────┘   └────────────┘
      │               │                │                │
      │ ① schedule    │                │                │
      ├──────────────►│                │                │
      │               │                │                │
      │               │ ② scrape      │                │
      │               │───────────────►│                │
      │               │                │                │
      │               │                │ ③ normalize    │
      │               │                │───────────────►│
      │               │                │                │
      │               │                │ ④ embed        │
      │               │                │───────────────►│
      │               │                │                │
      │               │ ⑤ result      │                │
      │               │◄───────────────│                │
      │               │                │                │
      │ ⑥ complete   │                │                │
      │◄──────────────│                │                │
      │               │                │                │
6.2 User Search Sequence
text
┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐
│   Client   │   │   API      │   │   Search   │   │  Database  │
│            │   │   Gateway  │   │   Engine   │   │  Layer     │
└────────────┘   └────────────┘   └────────────┘   └────────────┘
      │               │                │                │
      │ ① query       │                │                │
      ├──────────────►│                │                │
      │               │                │                │
      │               │ ② process     │                │
      │               │───────────────►│                │
      │               │                │                │
      │               │                │ ③ search      │
      │               │                │───────────────►│
      │               │                │                │
      │               │                │ ④ results     │
      │               │                │◄───────────────│
      │               │                │                │
      │               │ ⑤ ranking     │                │
      │               │◄───────────────│                │
      │               │                │                │
      │ ⑥ response   │                │                │
      │◄──────────────│                │                │
      │               │                │                │
DOCUMENT 05: SYSTEM ARCHITECTURE
1. Architecture Overview
1.1 Architecture Style
The system implements a Microservices Architecture with Event-Driven communication patterns. This design enables:

Independent scaling of components

Isolation of failures

Technology flexibility

Team autonomy

Easy deployment and updates

1.2 Architecture Principles
Stateless Services: Services don't maintain state between requests

Event Sourcing: System state changes captured as events

CQRS: Separate read and write models

Circuit Breakers: Graceful failure handling

Bulkheading: Resource isolation between components

2. Component Architecture
2.1 Service Components
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SERVICES LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  API Gateway     │  │  Auth Service    │  │  User Service            │  │
│  │                  │  │                  │  │                          │  │
│  │  • Routing       │  │  • Authentication│  │  • Profile Management   │  │
│  │  • Rate Limit    │  │  • Authorization │  │  • Preferences          │  │
│  │  • Load Balance  │  │  • JWT Issuer    │  │  • Search History       │  │
│  │  • SSL Term      │  │  • SSO          │  │  • Activity Tracking     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  Search Service  │  │  AI Service      │  │  Notification Service    │  │
│  │                  │  │                  │  │                          │  │
│  │  • Semantic      │  │  • Intent Detect │  │  • Matching              │  │
│  │  • Keyword       │  │  • Extract       │  │  • Formatting            │  │
│  │  • Hybrid        │  │  • Generate      │  │  • Channel Selection     │  │
│  │  • Caching       │  │  • Model Mgmt    │  │  • Delivery Tracking     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  Scraper Service │  │  Admin Service   │  │  WhatsApp Service        │  │
│  │                  │  │                  │  │                          │  │
│  │  • Source Mgmt   │  │  • Monitoring    │  │  • Message Processing    │  │
│  │  • Scheduling    │  │  • Analytics     │  │  • Session Management    │  │
│  │  • Execution     │  │  • User Mgmt     │  │  • Media Handling        │  │
│  │  • Deduplication │  │  • Source Mgmt   │  │  • Template Rendering    │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
2.2 Infrastructure Components
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INFRASTRUCTURE LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  Load Balancer   │  │  Message Queue   │  │  Redis Cache             │  │
│  │  (NGINX)         │  │  (Redis)         │  │                          │  │
│  │                  │  │                  │  │  • Session Storage       │  │
│  │  • HTTP/HTTPS    │  │  • Task Queue    │  │  • Rate Limiting         │  │
│  │  • Health Check  │  │  • Pub/Sub       │  │  • Search Cache          │  │
│  │  • SSL Certs     │  │  • Streams       │  │  • Lock Manager          │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  PostgreSQL      │  │  Celery Workers  │  │  Monitoring              │  │
│  │  (Primary)       │  │                  │  │                          │  │
│  │                  │  │  • Async Tasks   │  │  • Prometheus            │  │
│  │  • OLTP          │  │  • Scheduled     │  │  • Grafana              │  │
│  │  • pgvector      │  │  • Retry         │  │  • Loki                 │  │
│  │  • Replication   │  │  • Rate Limit    │  │  • Tempo                │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  PostgreSQL      │  │  Object Storage  │  │  DNS/SSL                 │  │
│  │  (Read Replicas) │  │  (S3-compatible) │  │                          │  │
│  │                  │  │                  │  │  • Domain Management     │  │
│  │  • Reporting     │  │  • Raw Data      │  │  • SSL Cert Renewal      │  │
│  │  • Analytics     │  │  • Images        │  │  • CDN Integration       │  │
│  │  • Search        │  │  • Backups       │  │  • DNS Load Balancing    │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
3. Deployment Architecture
3.1 Containerization Strategy
yaml
# Docker Compose Structure
services:
  # Load Balancer
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api

  # API Service
  api:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
      - AI_API_KEYS=...
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  # Celery Workers
  worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - postgres
    deploy:
      replicas: 5
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # Database
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      - POSTGRES_DB=wildautomations
      - POSTGRES_USER=wildautomations
      - POSTGRES_PASSWORD=...
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

  # Redis
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # Monitoring
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
3.2 Kubernetes Deployment
yaml
# Kubernetes Deployment Manifest
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wildautomations-api
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: wildautomations-api
  template:
    metadata:
      labels:
        app: wildautomations-api
    spec:
      containers:
      - name: api
        image: wildautomations/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: wildautomations-api
  namespace: production
spec:
  selector:
    app: wildautomations-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: wildautomations-api-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: wildautomations-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
4. Communication Architecture
4.1 Service Communication Patterns
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                     COMMUNICATION PATTERNS                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   SYNCHRONOUS (HTTP/REST)               ASYNCHRONOUS (Events)              │
│   ┌───────────────────────────┐        ┌───────────────────────────┐      │
│   │ API Gateway ←───→ Services│        │ Services ────→ Event Bus │      │
│   │                           │        │                           │      │
│   │ Webhooks ←───→ Endpoints │        │ Services ←───→ Event Bus │      │
│   │                           │        │                           │      │
│   │ Health Checks             │        │ Task Queue ←───→ Workers │      │
│   └───────────────────────────┘        └───────────────────────────┘      │
│                                                                             │
│   HYBRID (Request-Reply with Queues)   STREAMING (WebSocket)               │
│   ┌───────────────────────────┐        ┌───────────────────────────┐      │
│   │ Client → Queue → Worker   │        │ WhatsApp ←───→ WebSocket │      │
│   │         │                 │        │                           │      │
│   │ Client ←─┘                │        │ Real-time Updates         │      │
│   └───────────────────────────┘        └───────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
4.2 Event-Driven Architecture
yaml
Events:
  - OpportunityCreated:
      payload: { opportunity_id, domain, source }
      handlers: [NotificationService, SearchService, AnalyticsService]
      
  - OpportunityUpdated:
      payload: { opportunity_id, changes }
      handlers: [SearchService, NotificationService]
      
  - UserRegistered:
      payload: { user_id, email }
      handlers: [ProfileService, AnalyticsService, WelcomeService]
      
  - UserSearch:
      payload: { user_id, query, results }
      handlers: [AnalyticsService, RecommendationService]
      
  - NotificationDelivered:
      payload: { notification_id, user_id, channel, status }
      handlers: [AnalyticsService, UserService]
5. Security Architecture
5.1 Security Layers
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SECURITY LAYERS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   NETWORK LAYER                                                            │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │  • SSL/TLS Termination (NGINX)                                  │      │
│   │  • Rate Limiting (per IP, per User)                            │      │
│   │  • DDoS Protection (Cloudflare)                               │      │
│   │  • IP Whitelisting for Admin                                  │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│   APPLICATION LAYER                                                         │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │  • JWT Authentication (Bearer Token)                           │      │
│   │  • RBAC Authorization (Admin/User/Premium)                    │      │
│   │  • API Key Validation (External Services)                     │      │
│   │  • Input Validation (Pydantic)                                │      │
│   │  • SQL Injection Prevention (ORM)                             │      │
│   │  • XSS Prevention (Sanitization)                              │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│   DATA LAYER                                                                │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │  • Encryption at Rest (AES-256)                               │      │
│   │  • Encryption in Transit (TLS 1.3)                            │      │
│   │  • Data Masking (PII)                                         │      │
│   │  • Audit Logging (All Operations)                             │      │
│   │  • Backup Encryption                                          │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
5.2 Authentication Flow
text
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Client     │    │   API        │    │   Auth       │    │   Database   │
│              │    │   Gateway    │    │   Service    │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
      │                    │                    │                    │
      │ ① Login Request   │                    │                    │
      ├───────────────────►│                    │                    │
      │                    │                    │                    │
      │                    │ ② Validate         │                    │
      │                    ├───────────────────►│                    │
      │                    │                    │                    │
      │                    │                    │ ③ Check Creds     │
      │                    │                    ├───────────────────►│
      │                    │                    │                    │
      │                    │                    │ ④ User Found      │
      │                    │                    │◄───────────────────│
      │                    │                    │                    │
      │                    │ ⑤ JWT Token       │                    │
      │                    │◄───────────────────│                    │
      │                    │                    │                    │
      │ ⑥ Token + Profile │                    │                    │
      │◄───────────────────│                    │                    │
      │                    │                    │                    │
      │ ⑦ Subsequent      │                    │                    │
      │    Requests with   │                    │                    │
      │    Bearer Token    │                    │                    │
      ├───────────────────►│                    │                    │
      │                    │                    │                    │
      │                    │ ⑧ Validate Token  │                    │
      │                    ├───────────────────►│                    │
      │                    │                    │                    │
      │                    │ ⑨ Token Valid     │                    │
      │                    │◄───────────────────│                    │
      │                    │                    │                    │
      │ ⑩ Response        │                    │                    │
      │◄───────────────────│                    │                    │
      │                    │                    │                    │
6. Data Architecture
6.1 Data Flow Architecture
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   DATA INGESTION                DATA PROCESSING            DATA STORAGE    │
│   ┌──────────────────┐         ┌──────────────────┐      ┌───────────────┐ │
│   │  Scraped Data    │────────►│  Raw Storage    │─────►│  S3 Bucket    │ │
│   │  (External)      │         │  (JSON)         │      │  (Raw)        │ │
│   └──────────────────┘         └──────────────────┘      └───────────────┘ │
│           │                            │                         │         │
│           │                            ▼                         ▼         │
│   ┌──────────────────┐         ┌──────────────────┐      ┌───────────────┐ │
│   │  API Data        │────────►│  AI Processing   │─────►│  PostgreSQL   │ │
│   │  (External)      │         │  (Extraction)    │      │  (Normalized) │ │
│   └──────────────────┘         └──────────────────┘      └───────────────┘ │
│           │                            │                         │         │
│           │                            ▼                         ▼         │
│   ┌──────────────────┐         ┌──────────────────┐      ┌───────────────┐ │
│   │  RSS/Webhook     │────────►│  Normalization   │─────►│  Vector Store │ │
│   │  (External)      │         │  (Validation)    │      │  (pgvector)   │ │
│   └──────────────────┘         └──────────────────┘      └───────────────┘ │
│                                                                             │
│   DATA QUERY                    DATA DELIVERY                              │
│   ┌──────────────────┐         ┌──────────────────┐                        │
│   │  User Query      │────────►│  Search Engine   │───► Response           │
│   └──────────────────┘         └──────────────────┘                        │
│           │                             │                                  │
│           ▼                             ▼                                  │
│   ┌──────────────────┐         ┌──────────────────┐                        │
│   │  Cache Lookup    │         │  Notification    │───► Delivery           │
│   │  (Redis)         │         │  Engine          │                        │
│   └──────────────────┘         └──────────────────┘                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
6.2 Caching Strategy
yaml
Cache Layers:
  Application Cache:
    - Search Results: TTL=1 minute
    - User Profiles: TTL=5 minutes
    - AI Responses: TTL=10 minutes
    
  Database Cache:
    - Query Cache: TTL=30 seconds
    - Vector Cache: TTL=5 minutes
    - Lookup Tables: TTL=1 hour
    
  Content Cache:
    - Static Assets: TTL=24 hours
    - API Responses: TTL=5 minutes
    - Image Assets: TTL=7 days
    
  Cache Invalidation:
    - Write-through for user changes
    - Cache-aside for search
    - Event-based invalidation
7. Monitoring Architecture
7.1 Monitoring Stack
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MONITORING STACK                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   METRICS                    LOGS                     TRACES               │
│   ┌──────────────────┐      ┌──────────────────┐    ┌──────────────────┐   │
│   │  Prometheus      │      │  Loki            │    │  Tempo           │   │
│   │                  │      │                  │    │                  │   │
│   │  • System        │      │  • Application   │    │  • Distributed   │   │
│   │  • Application   │      │  • Access        │    │  • Performance   │   │
│   │  • Business      │      │  • Error         │    │  • Bottlenecks   │   │
│   └──────────────────┘      └──────────────────┘    └──────────────────┘   │
│            │                         │                        │            │
│            ▼                         ▼                        ▼            │
│   ┌──────────────────────────────────────────────────────────────────┐    │
│   │                          Grafana                                 │    │
│   │  • Dashboards                                                   │    │
│   │  • Alerts                                                       │    │
│   │  • Visualization                                                │    │
│   └──────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
7.2 Key Metrics
yaml
System Metrics:
  - CPU Usage per service
  - Memory Usage per service
  - Network I/O
  - Disk I/O
  - File Descriptors

Application Metrics:
  - Request Rate
  - Error Rate
  - Response Time (P50, P95, P99)
  - Active Users
  - Session Duration

Business Metrics:
  - Search Rate
  - Notification Rate
  - Click-Through Rate
  - User Acquisition Rate
  - Revenue per User

AI Metrics:
  - Model Latency
  - Token Usage
  - Cost per Request
  - Accuracy Metrics
  - Fallback Rate
