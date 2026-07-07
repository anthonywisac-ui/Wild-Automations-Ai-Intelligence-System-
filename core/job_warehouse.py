"""
Job Warehouse — every job the platform ever finds is SAVED, and every new
search checks the warehouse FIRST before hitting external sources.

Why: 4 users with similar requirements should not trigger 4 identical
external crawls — the first user's results serve the next three instantly,
and the warehouse keeps growing into a proprietary jobs dataset.

Storage: SQLite (data/crm_store.sqlite3, table jobs_warehouse) always;
best-effort mirror to Supabase table `jobs_found` when SUPABASE_URL/KEY are
set (survives Railway redeploys — same pattern as core/supabase_leads.py).

    save_jobs(jobs, query="project manager")     # after every search
    hits = search("senior project manager", days=14, limit=40)   # before
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_DB = Path(__file__).resolve().parent.parent / "data" / "crm_store.sqlite3"
_LOCK = threading.Lock()
_FRESH_DAYS = 14          # warehouse hits older than this are not served


def _init() -> None:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS jobs_warehouse ("
            "url TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT, "
            "location TEXT, job_type TEXT, salary TEXT, salary_usd REAL, "
            "description TEXT, source TEXT, posted_iso TEXT, "
            "query TEXT, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wh_seen "
                     "ON jobs_warehouse(last_seen)")
        conn.commit()


_init()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_jobs(jobs: List[Dict[str, Any]], query: str = "") -> int:
    """Upsert normalized job dicts (the shape job_search returns)."""
    if not jobs:
        return 0
    now = _now()
    n = 0
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            for j in jobs:
                url = (j.get("url") or j.get("source_url") or "").strip()
                title = (j.get("title") or "").strip()
                if not url or not title:
                    continue
                conn.execute(
                    "INSERT INTO jobs_warehouse (url,title,company,location,"
                    "job_type,salary,salary_usd,description,source,posted_iso,"
                    "query,first_seen,last_seen) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(url) DO UPDATE SET last_seen=excluded.last_seen, "
                    "salary=excluded.salary, posted_iso=excluded.posted_iso",
                    (url, title, j.get("company") or "", j.get("location") or "",
                     j.get("job_type") or "", str(j.get("salary") or ""),
                     j.get("salary_usd"), (j.get("description") or "")[:600],
                     j.get("source") or "", j.get("posted_iso") or "",
                     query[:120], now, now))
                n += 1
            conn.commit()
    except Exception as exc:
        logger.info("job_warehouse save failed: %s", exc)
    _mirror_supabase(jobs, query)
    return n


def search(query: str, days: int = _FRESH_DAYS, limit: int = 40) -> List[Dict[str, Any]]:
    """Recent warehouse jobs whose title matches the query tokens."""
    toks = [t for t in re.findall(r"[a-z]{3,}", (query or "").lower())
            if t not in ("job", "jobs", "remote")]
    if not toks:
        return []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    like = " OR ".join(["lower(title) LIKE ?"] * len(toks))
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            rows = conn.execute(
                f"SELECT url,title,company,location,job_type,salary,salary_usd,"
                f"description,source,posted_iso FROM jobs_warehouse "
                f"WHERE last_seen >= ? AND ({like}) "
                f"ORDER BY last_seen DESC LIMIT ?",
                [cutoff] + [f"%{t}%" for t in toks] + [limit]).fetchall()
    except Exception as exc:
        logger.info("job_warehouse search failed: %s", exc)
        return []
    out = []
    for (url, title, company, location, job_type, salary, salary_usd,
         desc, source, posted_iso) in rows:
        out.append({"title": title, "source_url": url, "location": location,
                    "description": desc, "price": salary or "",
                    "metadata": {"type": "job", "company": company,
                                 "source": source or "Warehouse",
                                 "from_warehouse": True,
                                 "salary": salary or "",
                                 "date_posted": posted_iso}})
    return out


def stats() -> Dict[str, Any]:
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            total = conn.execute("SELECT COUNT(*) FROM jobs_warehouse").fetchone()[0]
            recent = conn.execute(
                "SELECT COUNT(*) FROM jobs_warehouse WHERE last_seen >= ?",
                ((datetime.now(timezone.utc) - timedelta(days=_FRESH_DAYS)).isoformat(),)
            ).fetchone()[0]
        return {"total": total, f"fresh_{_FRESH_DAYS}d": recent}
    except Exception:
        return {"total": 0}


# ── Supabase mirror (best-effort, never blocks the search) ───────────────────

def _mirror_supabase(jobs: List[Dict[str, Any]], query: str) -> None:
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
    if not (url and key) or not jobs:
        return
    import threading as _t

    def _push():
        try:
            import httpx
            rows = []
            for j in jobs[:60]:
                u = (j.get("url") or j.get("source_url") or "").strip()
                if not u or not j.get("title"):
                    continue
                rows.append({
                    "url": u, "title": j["title"][:200],
                    "company": (j.get("company") or "")[:120],
                    "location": (j.get("location") or "")[:120],
                    "job_type": (j.get("job_type") or "")[:40],
                    "salary": str(j.get("salary") or "")[:80],
                    "source": (j.get("source") or "")[:60],
                    "posted_iso": j.get("posted_iso") or None,
                    "query": query[:120], "last_seen": _now(),
                })
            if not rows:
                return
            r = httpx.post(
                f"{url}/rest/v1/jobs_found?on_conflict=url",
                headers={"apikey": key, "Authorization": f"Bearer {key}",
                         "Content-Type": "application/json",
                         "Prefer": "resolution=merge-duplicates"},
                content=json.dumps(rows), timeout=15)
            if r.status_code >= 300:
                logger.info("job_warehouse supabase mirror: %s %s",
                            r.status_code, r.text[:150])
        except Exception as exc:
            logger.info("job_warehouse supabase mirror failed: %s", exc)

    _t.Thread(target=_push, daemon=True).start()
