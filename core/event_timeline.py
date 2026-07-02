"""
Event Timeline — Wave 5 spine.

Everything is an event. Events are appended (never recreated) to a persistent
log keyed by canonical_id, so the Evidence Graph evolves over time and the
Learning Engine has a single source of truth to learn from.

Event categories: discovery (search/query/source), entity signals (hiring,
expansion, funding, complaint, review, website/technology/leadership change),
and CRM interactions (contact, call, reply, meeting, booking, sale, conversion,
revenue, won, lost).

Persistent (data/crm_store.sqlite3, `events` table). Thread-safe, fail-soft.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

_DB = Path(__file__).resolve().parent.parent / "data" / "crm_store.sqlite3"
_LOCK = threading.Lock()


class EventType(str, Enum):
    # discovery
    SEARCH = "search"
    QUERY = "query"
    SOURCE = "source"
    # entity signals (evidence-evolving)
    HIRING = "hiring"
    EXPANSION = "expansion"
    FUNDING = "funding"
    COMPLAINT = "complaint"
    REVIEW = "review"
    WEBSITE_CHANGE = "website_change"
    TECHNOLOGY_CHANGE = "technology_change"
    LEADERSHIP_CHANGE = "leadership_change"
    # CRM interactions
    CAMPAIGN = "campaign"
    RECOMMENDATION = "recommendation"
    CONTACT = "contact"
    CALL = "call"
    REPLY = "reply"
    MEETING = "meeting"
    BOOKING = "booking"
    SALE = "sale"
    CONVERSION = "conversion"
    REVENUE = "revenue"
    WON = "won"
    LOST = "lost"


# Outcome events that carry a success signal for the Learning Engine.
OUTCOME_EVENTS = {
    EventType.CONTACT, EventType.CALL, EventType.REPLY, EventType.MEETING,
    EventType.BOOKING, EventType.SALE, EventType.CONVERSION, EventType.REVENUE,
    EventType.WON, EventType.LOST,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB), timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def _init() -> None:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id      TEXT PRIMARY KEY,
                canonical_id  TEXT,
                event_type    TEXT NOT NULL,
                ts            TEXT NOT NULL,
                outcome       REAL,              -- success signal in [0,1] (nullable)
                value         REAL,              -- monetary/other value (nullable)
                payload       TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ev_cid ON events(canonical_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ev_type ON events(event_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ev_ts ON events(ts)")
        conn.commit()


_init()


def record(event_type: EventType, *, canonical_id: str = "",
           payload: Optional[Dict[str, Any]] = None,
           outcome: Optional[float] = None, value: Optional[float] = None) -> Optional[str]:
    """Append an event. Returns event_id (or None on failure). Never raises."""
    try:
        eid = uuid4().hex
        with _LOCK, _connect() as conn:
            conn.execute(
                "INSERT INTO events (event_id,canonical_id,event_type,ts,outcome,value,payload) "
                "VALUES (?,?,?,?,?,?,?)",
                (eid, canonical_id, event_type.value, _now(), outcome, value,
                 json.dumps(payload or {}, ensure_ascii=False)))
            conn.commit()
        return eid
    except Exception as exc:
        logger.warning("event_timeline: record failed: %s", exc)
        return None


def record_many(events: List[Dict[str, Any]]) -> int:
    """Bulk-append events (each: {event_type, canonical_id?, payload?, outcome?, value?})."""
    n = 0
    for e in events:
        et = e.get("event_type")
        if isinstance(et, str):
            try:
                et = EventType(et)
            except ValueError:
                continue
        if record(et, canonical_id=e.get("canonical_id", ""),
                  payload=e.get("payload"), outcome=e.get("outcome"), value=e.get("value")):
            n += 1
    return n


def timeline(canonical_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    """Chronological event timeline for an entity."""
    try:
        with _LOCK, _connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE canonical_id=? ORDER BY ts ASC LIMIT ?",
                (canonical_id, limit)).fetchall()
            return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("event_timeline: timeline failed: %s", exc)
        return []


def recent(event_type: Optional[EventType] = None, days: int = 90,
           limit: int = 2000) -> List[Dict[str, Any]]:
    """Recent events, optionally filtered by type — used by the Learning Engine."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        with _LOCK, _connect() as conn:
            if event_type:
                rows = conn.execute(
                    "SELECT * FROM events WHERE event_type=? AND ts>=? ORDER BY ts DESC LIMIT ?",
                    (event_type.value, cutoff, limit)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM events WHERE ts>=? ORDER BY ts DESC LIMIT ?",
                    (cutoff, limit)).fetchall()
            return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("event_timeline: recent failed: %s", exc)
        return []


def stats() -> Dict[str, Any]:
    try:
        with _LOCK, _connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            by_type = {r[0]: r[1] for r in conn.execute(
                "SELECT event_type, COUNT(*) FROM events GROUP BY event_type").fetchall()}
            return {"total_events": total, "by_type": by_type}
    except Exception:
        return {"total_events": 0, "by_type": {}}
