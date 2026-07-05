"""
Job Tracker — save jobs + application status (Supabase, fail-soft).

The retention layer: a user saves a job from the match results, then moves it
through a tiny pipeline of statuses. Mirrors supabase_leads.py conventions —
best-effort, never raises, silently degrades to an in-memory store when
Supabase isn't configured (so local dev still works; memory resets on restart).

    saved = save_job(job)                     # upsert, dedup by job_key
    rows  = list_jobs(status="")              # newest first
    ok    = set_status(job_key, "applied")    # saved|applied|interview|offer|rejected

Supabase table (run once in the SQL editor):

    create table if not exists tracked_jobs (
      job_key text primary key,
      title text, company text, location text, url text,
      salary text, source text, match numeric, why_match text,
      status text default 'saved',
      saved_at timestamptz default now(),
      updated_at timestamptz
    );
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_TABLE = "tracked_jobs"
STATUSES = ["saved", "applied", "interview", "offer", "rejected"]

_client = None
_checked = False
_mem: Dict[str, Dict[str, Any]] = {}   # fallback store (no Supabase)


def _get_client():
    global _client, _checked
    if _checked:
        return _client
    _checked = True
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
    if not (url and key):
        logger.info("job_tracker: Supabase not configured — using in-memory store")
        return None
    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("job_tracker: enabled (table=%s)", _TABLE)
    except Exception as exc:
        logger.warning("job_tracker: disabled: %s", exc)
        _client = None
    return _client


def job_key(job: Dict[str, Any]) -> str:
    basis = f"{job.get('title','')}|{job.get('company','')}|{job.get('url','')}".lower()
    return hashlib.md5(basis.encode("utf-8")).hexdigest()


def _row(job: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_key": job_key(job),
        "title": (job.get("title") or "")[:200],
        "company": (job.get("company") or "")[:120],
        "location": (job.get("location") or "")[:120],
        "url": job.get("url") or "",
        "salary": (job.get("salary") or "")[:80],
        "source": (job.get("source") or "")[:60],
        "match": float(job.get("match") or 0),
        "why_match": (job.get("why_match") or "")[:400],
        "status": "saved",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert one job as 'saved'. Returns {ok, job_key}. Never raises."""
    if not (job.get("title") and job.get("company")):
        return {"ok": False, "error": "title and company required"}
    row = _row(job)
    client = _get_client()
    if client:
        try:
            client.table(_TABLE).upsert(row, on_conflict="job_key").execute()
            return {"ok": True, "job_key": row["job_key"]}
        except Exception as exc:
            logger.warning("job_tracker: save failed (table missing?): %s", exc)
            return {"ok": False, "error": "tracking store unavailable"}
    _mem[row["job_key"]] = row
    return {"ok": True, "job_key": row["job_key"], "store": "memory"}


def list_jobs(status: str = "") -> List[Dict[str, Any]]:
    """All tracked jobs, newest first; optional status filter. Never raises."""
    client = _get_client()
    if client:
        try:
            q = client.table(_TABLE).select("*").order("updated_at", desc=True).limit(200)
            if status in STATUSES:
                q = q.eq("status", status)
            return q.execute().data or []
        except Exception as exc:
            logger.warning("job_tracker: list failed: %s", exc)
            return []
    rows = list(_mem.values())
    if status in STATUSES:
        rows = [r for r in rows if r.get("status") == status]
    return sorted(rows, key=lambda r: r.get("updated_at", ""), reverse=True)


def set_status(key: str, status: str) -> Dict[str, Any]:
    """Move a tracked job to a new status. Never raises."""
    if status not in STATUSES:
        return {"ok": False, "error": f"status must be one of {STATUSES}"}
    now = datetime.now(timezone.utc).isoformat()
    client = _get_client()
    if client:
        try:
            client.table(_TABLE).update({"status": status, "updated_at": now}) \
                .eq("job_key", key).execute()
            return {"ok": True}
        except Exception as exc:
            logger.warning("job_tracker: set_status failed: %s", exc)
            return {"ok": False, "error": "tracking store unavailable"}
    if key in _mem:
        _mem[key]["status"] = status
        _mem[key]["updated_at"] = now
        return {"ok": True, "store": "memory"}
    return {"ok": False, "error": "job not found"}
