"""
Canonical Entity Store — Wave 3 adjustment: persistence.

SQLite-backed store for canonical entities so the registry survives across runs
and future learning modules can reuse it. Every canonical entity carries a
stable UUID, created/updated timestamps, and full histories (merge, source,
confidence, evidence).

Shares the CRM SQLite file (data/crm_store.sqlite3), separate `canonical_entities`
table. Thread-safe; degrades gracefully (all writes wrapped).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

_DB = Path(__file__).resolve().parent.parent / "data" / "crm_store.sqlite3"
_LOCK = threading.Lock()
_HISTORY_CAP = 50   # keep the most recent N history entries per field


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
            CREATE TABLE IF NOT EXISTS canonical_entities (
                canonical_id       TEXT PRIMARY KEY,
                uuid               TEXT NOT NULL,
                entity_type        TEXT,
                name               TEXT,
                location           TEXT,
                created_at         TEXT NOT NULL,
                updated_at         TEXT NOT NULL,
                data               TEXT NOT NULL,
                merge_history      TEXT NOT NULL,
                source_history     TEXT NOT NULL,
                confidence_history TEXT NOT NULL,
                evidence_history   TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ce_type ON canonical_entities(entity_type)")
        conn.commit()


_init()


def _cap(seq: List[Any]) -> List[Any]:
    return seq[-_HISTORY_CAP:]


def upsert(entity: Any) -> Dict[str, Any]:
    """Insert or merge a ResolvedEntity by canonical_id, maintaining histories.

    `entity` is a core.domain.ResolvedEntity (or anything with .canonical_id,
    .entity_type, .name, .location, .confidence, .source_reliability, .sources,
    .evidence, .model_dump()).
    """
    try:
        cid = entity.canonical_id
        etype = getattr(entity.entity_type, "value", str(entity.entity_type))
        data = entity.model_dump(mode="json") if hasattr(entity, "model_dump") else dict(entity)
        now = _now()
        conf = float(getattr(entity, "confidence", 0.0) or 0.0)
        sources = list(getattr(entity, "sources", []) or [])
        ev_summary = [getattr(n, "type", None).value if hasattr(getattr(n, "type", None), "value")
                      else str(getattr(n, "type", "")) for n in getattr(entity, "evidence", [])]

        with _LOCK, _connect() as conn:
            row = conn.execute("SELECT * FROM canonical_entities WHERE canonical_id = ?",
                               (cid,)).fetchone()
            if row is None:
                rec = {
                    "canonical_id": cid, "uuid": uuid4().hex,
                    "entity_type": etype, "name": entity.name, "location": getattr(entity, "location", ""),
                    "created_at": now, "updated_at": now,
                    "data": json.dumps(data, ensure_ascii=False),
                    "merge_history": json.dumps([{"ts": now, "event": "created", "sources": sources}]),
                    "source_history": json.dumps([{"ts": now, "sources": sources}]),
                    "confidence_history": json.dumps([{"ts": now, "confidence": conf}]),
                    "evidence_history": json.dumps([{"ts": now, "evidence": ev_summary}]),
                }
                conn.execute(
                    "INSERT INTO canonical_entities "
                    "(canonical_id,uuid,entity_type,name,location,created_at,updated_at,"
                    "data,merge_history,source_history,confidence_history,evidence_history) "
                    "VALUES (:canonical_id,:uuid,:entity_type,:name,:location,:created_at,"
                    ":updated_at,:data,:merge_history,:source_history,:confidence_history,:evidence_history)",
                    rec)
                conn.commit()
                return rec

            # merge into existing
            mh = _cap(json.loads(row["merge_history"]) + [{"ts": now, "event": "merged", "sources": sources}])
            sh = _cap(json.loads(row["source_history"]) + [{"ts": now, "sources": sources}])
            ch = _cap(json.loads(row["confidence_history"]) + [{"ts": now, "confidence": conf}])
            eh = _cap(json.loads(row["evidence_history"]) + [{"ts": now, "evidence": ev_summary}])
            conn.execute(
                "UPDATE canonical_entities SET updated_at=?, name=?, location=?, data=?, "
                "merge_history=?, source_history=?, confidence_history=?, evidence_history=? "
                "WHERE canonical_id=?",
                (now, entity.name, getattr(entity, "location", ""), json.dumps(data, ensure_ascii=False),
                 json.dumps(mh), json.dumps(sh), json.dumps(ch), json.dumps(eh), cid))
            conn.commit()
            return {"canonical_id": cid, "uuid": row["uuid"], "created_at": row["created_at"],
                    "updated_at": now, "merged": True}
    except Exception as exc:
        logger.warning("canonical_store: upsert failed: %s", exc)
        return {}


def get(canonical_id: str) -> Optional[Dict[str, Any]]:
    try:
        with _LOCK, _connect() as conn:
            row = conn.execute("SELECT * FROM canonical_entities WHERE canonical_id=?",
                               (canonical_id,)).fetchone()
            return dict(row) if row else None
    except Exception as exc:
        logger.warning("canonical_store: get failed: %s", exc)
        return None


def stats() -> Dict[str, Any]:
    try:
        with _LOCK, _connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM canonical_entities").fetchone()[0]
            return {"persisted_entities": total}
    except Exception:
        return {"persisted_entities": 0}
