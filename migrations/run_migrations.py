"""
Run all Supabase migrations in order.

Usage:
    python migrations/run_migrations.py

Reads SUPABASE_URL and SUPABASE_KEY from environment (.env).
Uses supabase-py service_role key (has full DB access, bypasses RLS).
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY", "")

MIGRATIONS_DIR = Path(__file__).parent
MIGRATION_FILES = sorted(MIGRATIONS_DIR.glob("0*.sql"))

ORDER = [
    "001_users.sql",
    "002_opportunities.sql",
    "003_audit_logs.sql",
    "004_rls_policies.sql",
    "005_views_and_functions.sql",
]


def run_sql(client, sql: str) -> None:
    """Execute raw SQL via Supabase rpc or postgrest."""
    # supabase-py 2.x: use client.rpc for raw SQL via a helper function,
    # or the postgrest client directly.
    # Simplest: use httpx to hit the /rest/v1/rpc or pg endpoint.
    import httpx
    url = SUPABASE_URL.rstrip("/") + "/rest/v1/rpc/exec_sql"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    # Try via RPC helper (create once, then use)
    resp = httpx.post(url, json={"sql": sql}, headers=headers, verify=False, timeout=30)
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"SQL failed ({resp.status_code}): {resp.text[:300]}")


async def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in environment")
        sys.exit(1)

    print(f"Supabase: {SUPABASE_URL}")
    print(f"Running {len(ORDER)} migration(s)...\n")

    for fname in ORDER:
        fpath = MIGRATIONS_DIR / fname
        if not fpath.exists():
            print(f"  SKIP  {fname} (file not found)")
            continue

        sql = fpath.read_text(encoding="utf-8")
        print(f"  RUN   {fname} ({len(sql)} bytes)")
        try:
            run_sql(None, sql)
            print(f"  OK    {fname}")
        except Exception as exc:
            print(f"  WARN  {fname}: {exc}")
            print("        (Some statements may have already been applied — check Supabase manually)")

    print("\nDone. Verify tables in Supabase → Table Editor.")
    print("\nQuick SQL check:")
    print("  SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")


if __name__ == "__main__":
    asyncio.run(main())
