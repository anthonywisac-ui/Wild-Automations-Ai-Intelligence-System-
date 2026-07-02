# Supabase Migrations

## Run Order

Run each file **in order** in Supabase → SQL Editor:

| File | Tables Created |
|------|---------------|
| `001_users.sql` | `users`, `user_profiles`, `user_preferences`, `saved_items` |
| `002_opportunities.sql` | `opportunities`, `job_opportunities`, `real_estate_opportunities`, `vehicle_opportunities`, `immigration_opportunities` |
| `003_audit_logs.sql` | `notification_logs`, `search_history`, `audit_logs`, `system_logs` |
| `004_rls_policies.sql` | RLS policies on all tables |
| `005_views_and_functions.sql` | `search_opportunities()`, `mv_domain_stats`, `mv_user_engagement`, `cleanup_expired_opportunities()` |

## How to Run

1. Open [Supabase Dashboard](https://app.supabase.com) → your project
2. Go to **SQL Editor**
3. Copy-paste each `.sql` file content and click **Run**
4. Repeat in order: 001 → 002 → 003 → 004 → 005

## After Running

Verify tables exist:
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

Expected tables:
- audit_logs
- bot_alerts (existing — from scraper pipeline)
- immigration_opportunities
- job_opportunities
- notification_logs
- opportunities
- real_estate_opportunities
- retention_policy
- saved_items
- search_history
- system_logs
- user_preferences
- user_profiles
- users
- vehicle_opportunities

## Notes

- `bot_alerts` already exists — scraper pipeline writes to it
- `opportunities` is the new normalized table — future scrapers will write here
- `saved_items.user_id` is a TEXT field (phone number like `+923351021321`)
- RLS: backend uses `SUPABASE_KEY` (service_role) which bypasses all RLS
- WhatsApp bot → `saved_items` via service_role (no auth required)
- Web users → own rows only (via JWT in future)
