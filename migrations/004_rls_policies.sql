-- Migration 004: Row Level Security (RLS) Policies
-- Run AFTER 001, 002, 003
-- Supabase uses auth.uid() for the logged-in user

-- ─────────────────────────────────────────────────────────────────────────────
-- ENABLE RLS
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE users               ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles       ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences    ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_items         ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_logs   ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_history      ENABLE ROW LEVEL SECURITY;
ALTER TABLE opportunities       ENABLE ROW LEVEL SECURITY;

-- audit_logs and system_logs: admin only (no user RLS needed — access via service_role key)

-- ─────────────────────────────────────────────────────────────────────────────
-- USERS — can only see/edit their own row
-- ─────────────────────────────────────────────────────────────────────────────

CREATE POLICY users_select_own ON users
    FOR SELECT USING (user_id::text = auth.uid()::text);

CREATE POLICY users_update_own ON users
    FOR UPDATE USING (user_id::text = auth.uid()::text);

-- Service role (backend) bypasses RLS automatically — no policy needed

-- ─────────────────────────────────────────────────────────────────────────────
-- USER PROFILES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE POLICY profiles_select_own ON user_profiles
    FOR SELECT USING (user_id::text = auth.uid()::text);

CREATE POLICY profiles_insert_own ON user_profiles
    FOR INSERT WITH CHECK (user_id::text = auth.uid()::text);

CREATE POLICY profiles_update_own ON user_profiles
    FOR UPDATE USING (user_id::text = auth.uid()::text);

-- ─────────────────────────────────────────────────────────────────────────────
-- USER PREFERENCES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE POLICY prefs_select_own ON user_preferences
    FOR SELECT USING (user_id::text = auth.uid()::text);

CREATE POLICY prefs_insert_own ON user_preferences
    FOR INSERT WITH CHECK (user_id::text = auth.uid()::text);

CREATE POLICY prefs_update_own ON user_preferences
    FOR UPDATE USING (user_id::text = auth.uid()::text);

-- ─────────────────────────────────────────────────────────────────────────────
-- SAVED ITEMS — user_id is phone/string, not UUID
-- Use anon + service_role access (WhatsApp bot uses service_role key)
-- ─────────────────────────────────────────────────────────────────────────────

-- Anon select: disabled — bot uses service_role key, no RLS enforcement
-- If you add web UI login, replace with:
-- CREATE POLICY saved_select_own ON saved_items FOR SELECT USING (user_id = auth.uid()::text);

-- ─────────────────────────────────────────────────────────────────────────────
-- NOTIFICATION LOGS — users see own notifications
-- ─────────────────────────────────────────────────────────────────────────────

CREATE POLICY notif_select_own ON notification_logs
    FOR SELECT USING (user_id::text = auth.uid()::text);

-- ─────────────────────────────────────────────────────────────────────────────
-- SEARCH HISTORY — users see own searches
-- ─────────────────────────────────────────────────────────────────────────────

CREATE POLICY search_select_own ON search_history
    FOR SELECT USING (user_id::text = auth.uid()::text);

CREATE POLICY search_insert_own ON search_history
    FOR INSERT WITH CHECK (user_id::text = auth.uid()::text);

-- ─────────────────────────────────────────────────────────────────────────────
-- OPPORTUNITIES — public read (all scraped data is public)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE POLICY opp_public_read ON opportunities
    FOR SELECT USING (status = 'active');

-- Only service_role (backend) can insert/update opportunities
-- No INSERT/UPDATE policy for authenticated users

-- ─────────────────────────────────────────────────────────────────────────────
-- BOT ALERTS (existing table) — public read for now
-- ─────────────────────────────────────────────────────────────────────────────

-- If bot_alerts has RLS enabled already, add:
-- ALTER TABLE bot_alerts ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY bot_alerts_public_read ON bot_alerts FOR SELECT USING (true);
-- (service_role bypasses RLS for writes from the scraper pipeline)
