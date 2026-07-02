"""
Rejection Store — rejected/blacklisted businesses are persisted, never dropped.

Every business the Qualification Engine rejects is stored with its structured
reason codes, overall score, decision, and the full dimension breakdown, so the
CRM can display them and future learning can audit qualification quality.

Table (data/crm_store.sqlite3): rejected_leads
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
            "CREATE TABLE IF NOT EXISTS rejected_leads ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, location TEXT, "
            "category TEXT, service TEXT, decision TEXT NOT NULL, overall REAL, "
            "reasons TEXT NOT NULL, dimensions TEXT, rejected_at TEXT NOT NULL, "
            "trace_id TEXT)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rej_decision "
                     "ON rejected_leads(decision, rejected_at)")
        conn.commit()


_init()


def record(record_: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Persist one rejected business with its structured reasons."""
    try:
        md = record_.get("metadata") or {}
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            conn.execute(
                "INSERT INTO rejected_leads (name,location,category,service,decision,"
                "overall,reasons,dimensions,rejected_at,trace_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (record_.get("title", "") or md.get("name", ""),
                 md.get("location", ""), md.get("category", ""),
                 result.get("service", ""), result.get("decision", ""),
                 result.get("overall", 0.0),
                 json.dumps(result.get("rejection_reasons", []), ensure_ascii=False),
                 json.dumps(result.get("dimensions", {}), ensure_ascii=False),
                 datetime.now(timezone.utc).isoformat(), md.get("trace_id", "")))
            conn.commit()
    except Exception as exc:
        logger.warning("rejection_store: record failed: %s", exc)


def recent(limit: int = 100, decision: str = "") -> List[Dict[str, Any]]:
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            conn.row_factory = sqlite3.Row
            if decision:
                rows = conn.execute(
                    "SELECT * FROM rejected_leads WHERE decision=? "
                    "ORDER BY id DESC LIMIT ?", (decision, limit)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM rejected_leads ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["reasons"] = json.loads(d.get("reasons") or "[]")
                d["dimensions"] = json.loads(d.get("dimensions") or "{}")
                out.append(d)
            return out
    except Exception:
        return []


def stats() -> Dict[str, Any]:
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            total = conn.execute("SELECT COUNT(*) FROM rejected_leads").fetchone()[0]
            by_dec = dict(conn.execute(
                "SELECT decision, COUNT(*) FROM rejected_leads GROUP BY decision").fetchall())
            # top reason codes
            reason_counts: Dict[str, int] = {}
            for (rj,) in conn.execute("SELECT reasons FROM rejected_leads").fetchall():
                for code in json.loads(rj or "[]"):
                    reason_counts[code] = reason_counts.get(code, 0) + 1
        return {"total_rejected": total, "by_decision": by_dec,
                "by_reason": dict(sorted(reason_counts.items(), key=lambda x: -x[1]))}
    except Exception:
        return {"total_rejected": 0, "by_decision": {}, "by_reason": {}}
