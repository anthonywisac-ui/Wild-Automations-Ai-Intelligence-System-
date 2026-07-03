"""
LinkedIn Collector Store — persistent accumulation of qualified LinkedIn leads.

The continuous background collector (scripts/linkedin_collector.py) writes here.
Deduplicated by LinkedIn profile URL, so running forever never creates dupes —
each new run only adds genuinely new decision-makers or refreshes existing ones.

Table (data/crm_store.sqlite3): linkedin_collected
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_DB = Path(__file__).resolve().parent.parent / "data" / "crm_store.sqlite3"
_LOCK = threading.Lock()


def _init() -> None:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS linkedin_collected ("
            "profile_url TEXT PRIMARY KEY, name TEXT, headline TEXT, company TEXT, "
            "location TEXT, category TEXT, query TEXT, qualified INTEGER, "
            "qualification_score REAL, decision TEXT, dimensions TEXT, explanation TEXT, "
            "first_seen TEXT, last_seen TEXT, times_seen INTEGER DEFAULT 1)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lic_qual "
                     "ON linkedin_collected(qualified, qualification_score)")
        conn.commit()


_init()


def upsert(lead: Dict[str, Any]) -> bool:
    """Insert or refresh one collected lead (dedup by profile_url).
    Returns True if this was a brand-new profile."""
    url = lead.get("profile_url")
    if not url:
        return False
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            row = conn.execute("SELECT times_seen FROM linkedin_collected WHERE profile_url=?",
                               (url,)).fetchone()
            if row:
                conn.execute(
                    "UPDATE linkedin_collected SET last_seen=?, times_seen=times_seen+1, "
                    "qualified=?, qualification_score=?, decision=?, dimensions=?, "
                    "explanation=?, headline=?, company=? WHERE profile_url=?",
                    (now, int(lead.get("qualified", 0)), lead.get("qualification_score", 0.0),
                     lead.get("decision", ""), json.dumps(lead.get("dimensions", {}), ensure_ascii=False),
                     json.dumps(lead.get("explanation", {}), ensure_ascii=False),
                     lead.get("headline", ""), lead.get("company", ""), url))
                conn.commit()
                return False
            conn.execute(
                "INSERT INTO linkedin_collected (profile_url,name,headline,company,location,"
                "category,query,qualified,qualification_score,decision,dimensions,explanation,"
                "first_seen,last_seen,times_seen) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
                (url, lead.get("name", ""), lead.get("headline", ""), lead.get("company", ""),
                 lead.get("location", ""), lead.get("category", ""), lead.get("query", ""),
                 int(lead.get("qualified", 0)), lead.get("qualification_score", 0.0),
                 lead.get("decision", ""), json.dumps(lead.get("dimensions", {}), ensure_ascii=False),
                 json.dumps(lead.get("explanation", {}), ensure_ascii=False), now, now))
            conn.commit()
            return True
    except Exception as exc:
        logger.warning("linkedin_collector_store: upsert failed: %s", exc)
        return False


def qualified(limit: int = 100) -> List[Dict[str, Any]]:
    """Return accumulated QUALIFIED leads, best score first."""
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM linkedin_collected WHERE qualified=1 "
                "ORDER BY qualification_score DESC LIMIT ?", (limit,)).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["dimensions"] = json.loads(d.get("dimensions") or "{}")
                d["explanation"] = json.loads(d.get("explanation") or "{}")
                out.append(d)
            return out
    except Exception:
        return []


def stats() -> Dict[str, Any]:
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            total = conn.execute("SELECT COUNT(*) FROM linkedin_collected").fetchone()[0]
            q = conn.execute("SELECT COUNT(*) FROM linkedin_collected WHERE qualified=1").fetchone()[0]
            last = conn.execute("SELECT MAX(last_seen) FROM linkedin_collected").fetchone()[0]
            by_cat = dict(conn.execute(
                "SELECT category, COUNT(*) FROM linkedin_collected WHERE qualified=1 "
                "GROUP BY category").fetchall())
        return {"total_collected": total, "qualified": q, "rejected": total - q,
                "last_activity": last, "qualified_by_category": by_cat}
    except Exception:
        return {"total_collected": 0, "qualified": 0}
