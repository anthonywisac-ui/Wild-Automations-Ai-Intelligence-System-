"""
Concierge Run Log — QA debug store for the last N concierge/CV-match runs.

Every run records: persona, the answers (CV TEXT EXCLUDED — privacy),
per-source result counts, and the top matches with score/source/eligibility.
`GET /api/concierge/recent` exposes it so match quality can be audited
without asking the user to paste screenshots. Feeds the future M5 QA harness.

Table (data/crm_store.sqlite3): concierge_runs — capped at _KEEP rows.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DB = Path(__file__).resolve().parent.parent / "data" / "crm_store.sqlite3"
_LOCK = threading.Lock()
_KEEP = 20


def _init() -> None:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS concierge_runs ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, "
            "kind TEXT NOT NULL, persona TEXT, answers TEXT, "
            "source_counts TEXT, total INTEGER, matches TEXT)")
        conn.commit()


_init()


def log_run(kind: str, persona: str, answers: Dict[str, Any],
            source_counts: Optional[Dict[str, int]],
            matches: List[Dict[str, Any]], total: int) -> None:
    """Persist one run (fail-soft — logging must never break a search)."""
    try:
        safe_answers = {k: v for k, v in (answers or {}).items()
                        if k not in ("cv_text",)}
        slim = []
        for m in (matches or [])[:20]:
            md = m.get("metadata") or {}
            slim.append({
                "title": m.get("title"), "company": md.get("company") or m.get("company"),
                "url": m.get("source_url") or m.get("url"),
                "match": m.get("_match_score") or m.get("match"),
                "source": md.get("source") or m.get("source"),
                "eligibility": m.get("eligibility"),
                "eligibility_reasons": m.get("eligibility_reasons"),
                "posted_ago": md.get("posted_ago") or m.get("posted_ago"),
            })
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            conn.execute(
                "INSERT INTO concierge_runs (ts,kind,persona,answers,"
                "source_counts,total,matches) VALUES (?,?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), kind, persona or "",
                 json.dumps(safe_answers, ensure_ascii=False, default=str)[:2000],
                 json.dumps(source_counts or {}, ensure_ascii=False),
                 int(total or 0),
                 json.dumps(slim, ensure_ascii=False, default=str)[:20000]))
            conn.execute(
                "DELETE FROM concierge_runs WHERE id NOT IN "
                "(SELECT id FROM concierge_runs ORDER BY id DESC LIMIT ?)",
                (_KEEP,))
            conn.commit()
    except Exception as exc:
        logger.info("concierge_log failed: %s", exc)


def recent(n: int = _KEEP) -> List[Dict[str, Any]]:
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            rows = conn.execute(
                "SELECT ts,kind,persona,answers,source_counts,total,matches "
                "FROM concierge_runs ORDER BY id DESC LIMIT ?", (n,)).fetchall()
        out = []
        for ts, kind, persona, answers, counts, total, matches in rows:
            out.append({"ts": ts, "kind": kind, "persona": persona,
                        "answers": json.loads(answers or "{}"),
                        "source_counts": json.loads(counts or "{}"),
                        "total": total,
                        "matches": json.loads(matches or "[]")})
        return out
    except Exception as exc:
        logger.info("concierge_log recent failed: %s", exc)
        return []
