-- Migration 005: Materialized Views + Utility Functions
-- Run AFTER 001–004
-- Optional — improves analytics and search performance

-- ─────────────────────────────────────────────────────────────────────────────
-- FULL-TEXT SEARCH HELPER
-- ─────────────────────────────────────────────────────────────────────────────

-- Fast text search across opportunities
CREATE OR REPLACE FUNCTION search_opportunities(
    p_query    TEXT,
    p_domain   VARCHAR(50) DEFAULT NULL,
    p_location TEXT        DEFAULT NULL,
    p_limit    INTEGER     DEFAULT 20
)
RETURNS TABLE (
    opportunity_id UUID,
    title          TEXT,
    domain         VARCHAR(50),
    source         VARCHAR(50),
    source_url     TEXT,
    normalized_data JSONB,
    score          FLOAT,
    posted_date    TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        o.opportunity_id,
        o.title,
        o.domain,
        o.source,
        o.source_url,
        o.normalized_data,
        o.score,
        o.posted_date
    FROM opportunities o
    WHERE
        o.status = 'active'
        AND (p_domain IS NULL OR o.domain = p_domain)
        AND (
            p_query IS NULL OR p_query = ''
            OR to_tsvector('english', COALESCE(o.title,'') || ' ' || COALESCE(o.description,''))
               @@ plainto_tsquery('english', p_query)
        )
        AND (
            p_location IS NULL OR p_location = ''
            OR o.normalized_data->>'location' ILIKE '%' || p_location || '%'
            OR o.description ILIKE '%' || p_location || '%'
        )
    ORDER BY
        o.score DESC NULLS LAST,
        o.posted_date DESC NULLS LAST
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- ─────────────────────────────────────────────────────────────────────────────
-- DOMAIN STATS — refreshable materialized view
-- ─────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_domain_stats AS
SELECT
    domain,
    source,
    COUNT(*)             AS total_count,
    COUNT(*) FILTER (WHERE status = 'active') AS active_count,
    AVG(score)           AS avg_score,
    MAX(created_at)      AS last_scraped_at
FROM opportunities
GROUP BY domain, source
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_domain_stats ON mv_domain_stats (domain, source);

-- Refresh command (run periodically via cron or pg_cron):
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_domain_stats;

-- ─────────────────────────────────────────────────────────────────────────────
-- USER ENGAGEMENT VIEW
-- ─────────────────────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_user_engagement AS
SELECT
    u.user_id,
    u.email,
    COUNT(DISTINCT sh.search_id)  AS total_searches,
    COUNT(DISTINCT sh.executed_at::DATE) AS active_days,
    COUNT(DISTINCT nl.notification_id)  AS total_notifications,
    COUNT(DISTINCT CASE WHEN nl.status = 'read' THEN nl.notification_id END) AS read_notifications,
    MAX(sh.executed_at) AS last_seen
FROM users u
LEFT JOIN search_history   sh ON u.user_id = sh.user_id
LEFT JOIN notification_logs nl ON u.user_id = nl.user_id
GROUP BY u.user_id, u.email
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_user_engagement ON mv_user_engagement (user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- DATA RETENTION CLEANUP
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS retention_policy (
    domain         VARCHAR(50) PRIMARY KEY,
    retention_days INTEGER NOT NULL,
    archive_enabled BOOLEAN DEFAULT TRUE,
    delete_enabled  BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO retention_policy (domain, retention_days) VALUES
    ('jobs',         180),
    ('real_estate',   90),
    ('vehicles',      60),
    ('immigration',  365),
    ('education',    365)
ON CONFLICT (domain) DO NOTHING;

CREATE OR REPLACE FUNCTION cleanup_expired_opportunities()
RETURNS INTEGER AS $$
DECLARE
    policy  RECORD;
    deleted INTEGER := 0;
    cnt     INTEGER;
BEGIN
    FOR policy IN SELECT * FROM retention_policy WHERE delete_enabled = TRUE
    LOOP
        DELETE FROM opportunities
        WHERE domain = policy.domain
          AND (
              expiry_date  < NOW() - (policy.retention_days || ' days')::INTERVAL
              OR posted_date < NOW() - (policy.retention_days * 2 || ' days')::INTERVAL
          );
        GET DIAGNOSTICS cnt = ROW_COUNT;
        deleted := deleted + cnt;
    END LOOP;
    RETURN deleted;
END;
$$ LANGUAGE plpgsql;

-- Schedule via pg_cron (Supabase supports this):
-- SELECT cron.schedule('cleanup-daily', '0 3 * * *', 'SELECT cleanup_expired_opportunities()');
-- SELECT cron.schedule('refresh-stats', '*/30 * * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_domain_stats');
