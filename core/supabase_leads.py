"""
Supabase Leads — push FINAL qualified leads to a dedicated Supabase table.

The main records store (core/store.py) holds raw scraped data; this module writes
the *outcome* — qualified leads with their scores, ticket, contact channel, and
AI explanation — into a `qualified_leads` table so you can query/export them
straight from the Supabase dashboard.

Best-effort: if Supabase isn't configured or a write fails, it silently no-ops so
the pipeline is never affected. Deduped by a stable lead key (upsert).
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_TABLE = "qualified_leads"
_client = None
_checked = False


def _get_client():
    global _client, _checked
    if _checked:
        return _client
    _checked = True
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
    if not (url and key):
        return None
    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("supabase_leads: enabled (table=%s)", _TABLE)
    except Exception as exc:
        logger.warning("supabase_leads: disabled: %s", exc)
        _client = None
    return _client


def _lead_key(row: Dict[str, Any]) -> str:
    basis = f"{row.get('name','')}|{row.get('location','')}|{row.get('category','')}".lower()
    return hashlib.md5(basis.encode("utf-8")).hexdigest()


def _to_supabase_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map a lead_export row into the qualified_leads table shape."""
    return {
        "lead_key": _lead_key(row),
        "name": row.get("name", ""),
        "category": row.get("category", ""),
        "location": row.get("location", ""),
        "ticket": row.get("ticket", ""),
        "qualification_score": row.get("qualification_score") or 0,
        "decision": row.get("decision", ""),
        "buyer_score": row.get("buyer_score") or 0,
        "service_score": row.get("service_score") or 0,
        "website": row.get("website", ""),
        "phone": row.get("phone", ""),
        "email": row.get("email", ""),
        "whatsapp": row.get("whatsapp", ""),
        "instagram": row.get("instagram", ""),
        "what_to_sell": row.get("what_to_sell", ""),
        "who_to_contact": row.get("who_to_contact", ""),
        "outreach_channel": row.get("outreach_channel", ""),
        "expected_close_probability": row.get("expected_close_probability") or 0,
        "why_buyer": row.get("why_buyer", ""),
        "opportunity_evidence": row.get("opportunity_evidence", ""),
        "trace_id": row.get("trace_id", ""),
        "canonical_id": row.get("canonical_id", ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def push_leads(rows: List[Dict[str, Any]]) -> int:
    """Upsert qualified-lead rows (from lead_export.rows) into Supabase.
    Returns number pushed (0 if disabled/failed). Never raises."""
    client = _get_client()
    if not client or not rows:
        return 0
    payload = [_to_supabase_row(r) for r in rows]
    try:
        client.table(_TABLE).upsert(payload, on_conflict="lead_key").execute()
        logger.info("supabase_leads: pushed %d qualified leads", len(payload))
        return len(payload)
    except Exception as exc:
        logger.warning("supabase_leads: push failed (table missing?): %s", exc)
        return 0
