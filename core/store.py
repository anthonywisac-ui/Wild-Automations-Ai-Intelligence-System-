"""
Unified persistence store for the CRM pipeline.

Design goals:
  - RELIABLE by default: local SQLite is the primary store (zero-setup, no
    network, survives restarts) — this is what powers historical baselines for
    accurate deal-scoring and job-age detection.
  - Supabase is an OPTIONAL best-effort mirror: if SUPABASE_URL/KEY are present
    AND reachable AND the table exists, batches are also pushed there. Any
    Supabase failure is swallowed — it never breaks the pipeline.

Public interface (async):
    store = get_store()
    await store.save_batch(records)          # dedup-persist by content hash
    history = await store.load_recent(days=30, category="Automobiles")
    await store.count()

Each record is a scraper result dict (title, description, source_url,
location, price, metadata{...}). We add: hash, category, source, scraped_at.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "crm_store.sqlite3"
_LOCK = threading.Lock()


def _record_hash(rec: Dict[str, Any]) -> str:
    """Stable identity hash = source_url + title composite (matches pipeline dedup).

    Using both fields means items that share a landing page but differ in title
    (e.g. car trims, gov register entries) are stored as distinct records, while
    an exact re-scrape of the same listing collapses to one row.
    """
    url = (rec.get("source_url") or "").strip().lower()
    title = (rec.get("title") or "").strip().lower()
    basis = f"{url}||{title}" if (url or title) else \
        f"{rec.get('_source','')}|{rec.get('location','')}|{(rec.get('description') or '')[:80]}".lower()
    return hashlib.md5(basis.encode("utf-8")).hexdigest()


class LocalStore:
    """SQLite-backed persistence. Thread-safe via a module lock + per-call connection."""

    def __init__(self, path: Path = _DB_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path), timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with _LOCK, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    hash        TEXT PRIMARY KEY,
                    category    TEXT,
                    source      TEXT,
                    title       TEXT,
                    data        TEXT NOT NULL,
                    scraped_at  TEXT NOT NULL,
                    first_seen  TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cat ON records(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_seen ON records(first_seen)")
            conn.commit()

    # ── sync internals (run in executor) ────────────────────────────────────

    def _save_batch_sync(self, records: List[Dict[str, Any]]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        rows = []
        for r in records:
            h = _record_hash(r)
            rows.append((
                h,
                r.get("_category", "") or (r.get("metadata") or {}).get("type", ""),
                r.get("_source", "") or (r.get("metadata") or {}).get("source", ""),
                (r.get("title") or "")[:400],
                json.dumps(r, ensure_ascii=False),
                (r.get("metadata") or {}).get("scraped_at", now),
                now,
            ))
        inserted = 0
        with _LOCK, self._connect() as conn:
            for row in rows:
                # INSERT OR IGNORE keeps the earliest first_seen (historical anchor)
                cur = conn.execute(
                    "INSERT OR IGNORE INTO records "
                    "(hash,category,source,title,data,scraped_at,first_seen) "
                    "VALUES (?,?,?,?,?,?,?)", row,
                )
                inserted += cur.rowcount
            conn.commit()
        return inserted

    def _load_recent_sync(self, days: int, category: Optional[str]) -> List[Dict[str, Any]]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        q = "SELECT data, first_seen FROM records WHERE first_seen >= ?"
        args: List[Any] = [cutoff]
        if category:
            q += " AND category = ?"
            args.append(category)
        out = []
        with _LOCK, self._connect() as conn:
            for row in conn.execute(q, args):
                try:
                    rec = json.loads(row["data"])
                    rec["_first_seen"] = row["first_seen"]
                    out.append(rec)
                except (ValueError, TypeError):
                    continue
        return out

    def _count_sync(self) -> int:
        with _LOCK, self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]

    # ── async public API ────────────────────────────────────────────────────

    async def save_batch(self, records: List[Dict[str, Any]]) -> int:
        if not records:
            return 0
        return await asyncio.get_event_loop().run_in_executor(None, self._save_batch_sync, records)

    async def load_recent(self, days: int = 30, category: Optional[str] = None) -> List[Dict[str, Any]]:
        return await asyncio.get_event_loop().run_in_executor(None, self._load_recent_sync, days, category)

    async def count(self) -> int:
        return await asyncio.get_event_loop().run_in_executor(None, self._count_sync)


class SupabaseMirror:
    """Best-effort Supabase mirror. Every method swallows errors — never fatal."""

    def __init__(self, url: str, key: str, table: str = "crm_records"):
        self.enabled = False
        self._db = None
        try:
            from core.database_layer import SupabaseDB
            self._db = SupabaseDB(url, key, table_name=table)
            self.enabled = True
            logger.info("store: Supabase mirror enabled (table=%s)", table)
        except Exception as exc:
            logger.warning("store: Supabase mirror disabled: %s", exc)

    async def save_batch(self, records: List[Dict[str, Any]]) -> None:
        if not self.enabled or not self._db:
            return
        for r in records:
            try:
                await self._db.insert(raw_data=r, normalized_data=r, skip_if_exists=True)
            except Exception as exc:
                # One failure (e.g. missing table) disables further attempts this run
                logger.warning("store: Supabase insert failed, disabling mirror: %s", exc)
                self.enabled = False
                return

    async def load_all(self) -> List[Dict[str, Any]]:
        if not self.enabled or not self._db:
            return []
        try:
            return await self._db.load_all()
        except Exception as exc:
            logger.warning("store: Supabase load_all failed: %s", exc)
            return []


class UnifiedStore:
    """Primary = LocalStore (reliable). Secondary = Supabase mirror (best-effort)."""

    def __init__(self):
        self.local = LocalStore()
        self.mirror: Optional[SupabaseMirror] = None
        self._hydrated = False
        url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
        if url and key:
            self.mirror = SupabaseMirror(url, key)

    async def _hydrate_if_needed(self) -> None:
        """Cold-start durability: on a fresh container (empty local SQLite) pull
        everything back from Supabase so data survives Railway redeploys. Runs
        once, best-effort — never fatal."""
        if self._hydrated or not (self.mirror and self.mirror.enabled):
            return
        self._hydrated = True
        try:
            if await self.local.count() > 0:
                return  # local already has data (local dev / mounted volume)
            records = await self.mirror.load_all()
            if records:
                n = await self.local.save_batch(records)
                logger.info("store: hydrated %d records from Supabase (cold start)", n)
        except Exception as exc:
            logger.warning("store: hydrate skipped: %s", exc)

    async def save_batch(self, records: List[Dict[str, Any]]) -> int:
        inserted = await self.local.save_batch(records)
        if self.mirror and self.mirror.enabled:
            try:
                await self.mirror.save_batch(records)
            except Exception:
                pass
        return inserted

    async def load_recent(self, days: int = 30, category: Optional[str] = None) -> List[Dict[str, Any]]:
        await self._hydrate_if_needed()
        return await self.local.load_recent(days=days, category=category)

    async def count(self) -> int:
        await self._hydrate_if_needed()
        return await self.local.count()

    def backend_name(self) -> str:
        if self.mirror and self.mirror.enabled:
            return "Supabase (durable) + SQLite cache"
        return "SQLite (local)"


_STORE_SINGLETON: Optional[UnifiedStore] = None


def get_store() -> UnifiedStore:
    global _STORE_SINGLETON
    if _STORE_SINGLETON is None:
        _STORE_SINGLETON = UnifiedStore()
    return _STORE_SINGLETON
