-- Migration 003: Audit, Notifications, Search History
-- Run AFTER 001 and 002

-- ─────────────────────────────────────────────────────────────────────────────
-- NOTIFICATION LOGS
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS notification_logs (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id        UUID REFERENCES users(user_id) ON DELETE CASCADE,
    opportunity_id UUID REFERENCES opportunities(opportunity_id),

    channel   VARCHAR(20) NOT NULL CHECK (channel IN ('email','whatsapp','web','push')),
    message   TEXT NOT NULL,
    template_id VARCHAR(100),

    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending','sent','delivered','read','failed')),
    error_message TEXT,

    scheduled_at  TIMESTAMP WITH TIME ZONE,
    sent_at       TIMESTAMP WITH TIME ZONE,
    delivered_at  TIMESTAMP WITH TIME ZONE,
    read_at       TIMESTAMP WITH TIME ZONE,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- SEARCH HISTORY
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS search_history (
    search_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID REFERENCES users(user_id) ON DELETE CASCADE,

    query      TEXT NOT NULL,
    query_type VARCHAR(50) DEFAULT 'text' CHECK (query_type IN ('text','voice','image')),
    filters    JSONB,
    intent     JSONB,

    result_ids    UUID[],
    result_count  INTEGER,

    session_id UUID,

    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- AUDIT LOGS
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id       UUID REFERENCES users(user_id),
    action        VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50)  NOT NULL,
    resource_id   UUID,

    details       JSONB,
    ip_address    INET,

    status VARCHAR(20) DEFAULT 'success'
        CHECK (status IN ('success','failure','pending')),
    error_message TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- SYSTEM LOGS  (runtime errors / scraper events)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS system_logs (
    log_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    level     VARCHAR(20) NOT NULL CHECK (level IN ('debug','info','warning','error','critical')),
    component VARCHAR(50) NOT NULL,
    message   TEXT NOT NULL,

    context     JSONB,
    request_id  UUID,

    exception   TEXT,
    stack_trace TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_notif_user_id    ON notification_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_notif_status     ON notification_logs(status);
CREATE INDEX IF NOT EXISTS idx_notif_channel    ON notification_logs(channel);
CREATE INDEX IF NOT EXISTS idx_notif_created    ON notification_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_search_user_id   ON search_history(user_id);
CREATE INDEX IF NOT EXISTS idx_search_executed  ON search_history(executed_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_user_id    ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action     ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_created    ON audit_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_syslog_level     ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_syslog_component ON system_logs(component);
CREATE INDEX IF NOT EXISTS idx_syslog_created   ON system_logs(created_at DESC);
