-- Migration 001: Users Module
-- Run this in Supabase SQL Editor
-- Tables: users, user_profiles, user_preferences

-- ─────────────────────────────────────────────────────────────────────────────
-- USERS
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    user_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email     VARCHAR(255) UNIQUE NOT NULL,
    phone     VARCHAR(20)  UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    avatar_url VARCHAR(500),

    -- Status
    email_verified   BOOLEAN DEFAULT FALSE,
    phone_verified   BOOLEAN DEFAULT FALSE,
    active           BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    deleted_at   TIMESTAMP WITH TIME ZONE,

    -- Meta
    preferences JSONB,

    CONSTRAINT users_email_check CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- ─────────────────────────────────────────────────────────────────────────────
-- USER PROFILES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_profiles (
    profile_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Personal
    country     VARCHAR(100),
    city        VARCHAR(100),
    nationality VARCHAR(100),

    -- Education
    education_level   VARCHAR(50),
    degree            VARCHAR(100),
    field_of_study    VARCHAR(100),
    institution       VARCHAR(200),
    graduation_year   INTEGER,

    -- Professional
    experience_years  INTEGER,
    current_title     VARCHAR(100),
    current_company   VARCHAR(200),
    skills            TEXT[],
    languages         TEXT[],

    -- Preferences
    visa_status        VARCHAR(50),
    preferred_countries TEXT[],
    preferred_cities    TEXT[],
    budget_range       JSONB,
    salary_range       JSONB,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_id),
    CONSTRAINT valid_experience CHECK (experience_years IS NULL OR experience_years >= 0)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- USER PREFERENCES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_preferences (
    preference_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Notification channels
    notifications_enabled     BOOLEAN  DEFAULT TRUE,
    notification_channels     TEXT[]   DEFAULT ARRAY['email','whatsapp'],
    email_notifications       BOOLEAN  DEFAULT TRUE,
    whatsapp_notifications    BOOLEAN  DEFAULT TRUE,

    -- Frequency
    daily_summary    BOOLEAN DEFAULT TRUE,
    weekly_summary   BOOLEAN DEFAULT TRUE,
    real_time_alerts BOOLEAN DEFAULT TRUE,

    -- Domain interests
    domains TEXT[] DEFAULT ARRAY['jobs','real_estate','vehicles','education','immigration'],

    -- Custom
    custom_filters JSONB,
    saved_searches JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- SAVED ITEMS  (bookmarks from WhatsApp chatbot)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS saved_items (
    id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id  TEXT NOT NULL,   -- phone number or user_id string
    item_id  TEXT NOT NULL,   -- bot_alerts.id or opportunity id
    saved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_id, item_id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_users_email       ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_phone       ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_active      ON users(active) WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS idx_profiles_user_id  ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_prefs_user_id     ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_user_id     ON saved_items(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_item_id     ON saved_items(item_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- AUTO-UPDATE updated_at
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER trg_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER trg_prefs_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
