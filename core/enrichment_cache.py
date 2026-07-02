"""
Enrichment Cache — Wave-Enrichment scalability.

Persists each business's enrichment so re-runs don't re-crawl unchanged sites.
Keyed by a stable business key (name+location) — carries:

    last_enriched · etag · content_hash · next_refresh · change_detected · enrichment

If the cache is fresh (now < next_refresh) the crawl is skipped entirely; on a
refresh, an unchanged content_hash extends next_refresh (back-off). This is what
lets the platform scale to tens of thousands of leads.

SQLite (data/crm_store.sqlite3, `enrichment_cache`). Thread-safe, fail-soft.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_DB = Path(__file__).resolve().parent.parent / "data" / "crm_store.sqlite3"
_LOCK = threading.Lock()

_DEFAULT_TTL_DAYS = 7
_MAX_TTL_DAYS = 30      # unchanged sites back off up to this


def business_key(name: str, location: str = "") -> str:
    basis = f"{(name or '').strip().lower()}|{(location or '').strip().lower()}"
    return hashlib.md5(basis.encode("utf-8")).hexdigest()[:16]


def content_hash(text: str) -> str:
    return hashlib.md5((text or "").encode("utf-8", "ignore")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _init() -> None:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS enrichment_cache (
                key             TEXT PRIMARY KEY,
                website         TEXT,
                last_enriched   TEXT NOT NULL,
                etag            TEXT,
                content_hash    TEXT,
                next_refresh    TEXT NOT NULL,
                change_detected INTEGER DEFAULT 0,
                enrichment      TEXT NOT NULL
            )
            """
        )
        conn.commit()


_init()


def get(key: str) -> Optional[Dict[str, Any]]:
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM enrichment_cache WHERE key=?", (key,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["enrichment"] = json.loads(d["enrichment"]) if d["enrichment"] else {}
            return d
    except Exception as exc:
        logger.warning("enrichment_cache: get failed: %s", exc)
        return None


def should_refresh(key: str) -> bool:
    """True if there is no cache or the refresh window has elapsed."""
    row = get(key)
    if not row:
        return True
    try:
        return _now() >= datetime.fromisoformat(row["next_refresh"])
    except (ValueError, TypeError):
        return True


def _next_refresh(prev_hash: Optional[str], new_hash: Optional[str]) -> str:
    """Back off unchanged sites; reset to base TTL when content changed."""
    ttl = _DEFAULT_TTL_DAYS
    if prev_hash and new_hash and prev_hash == new_hash:
        ttl = min(_MAX_TTL_DAYS, _DEFAULT_TTL_DAYS * 2)
    return (_now() + timedelta(days=ttl)).isoformat()


def store(key: str, *, website: Optional[str], enrichment: Dict[str, Any],
          etag: Optional[str] = None, new_content_hash: Optional[str] = None,
          change_detected: bool = False, prev_content_hash: Optional[str] = None) -> None:
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            conn.execute(
                "INSERT INTO enrichment_cache "
                "(key,website,last_enriched,etag,content_hash,next_refresh,change_detected,enrichment) "
                "VALUES (?,?,?,?,?,?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET website=excluded.website, "
                "last_enriched=excluded.last_enriched, etag=excluded.etag, "
                "content_hash=excluded.content_hash, next_refresh=excluded.next_refresh, "
                "change_detected=excluded.change_detected, enrichment=excluded.enrichment",
                (key, website, _now().isoformat(), etag, new_content_hash,
                 _next_refresh(prev_content_hash, new_content_hash), 1 if change_detected else 0,
                 json.dumps(enrichment, ensure_ascii=False)))
            conn.commit()
    except Exception as exc:
        logger.warning("enrichment_cache: store failed: %s", exc)


def stats() -> Dict[str, Any]:
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            total = conn.execute("SELECT COUNT(*) FROM enrichment_cache").fetchone()[0]
            changed = conn.execute(
                "SELECT COUNT(*) FROM enrichment_cache WHERE change_detected=1").fetchone()[0]
            return {"cached_businesses": total, "changed_last_run": changed}
    except Exception:
        return {"cached_businesses": 0, "changed_last_run": 0}
