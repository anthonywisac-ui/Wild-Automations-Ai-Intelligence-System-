"""Company Hiring Velocity — jobs posted in last N days from DB or ATS APIs."""
from __future__ import annotations
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# In-memory velocity cache: company_name.lower() -> {"count": int, "window_days": int, "ts": float}
_CACHE: Dict[str, dict] = {}
_CACHE_TTL = 3600  # 1 hour


def _cache_key(company: str) -> str:
    return company.lower().strip()


def record_jobs(company: str, job_count: int, window_days: int = 30) -> None:
    """Store observed job count for a company (call after each search run)."""
    import time
    _CACHE[_cache_key(company)] = {
        "count": job_count,
        "window_days": window_days,
        "ts": time.time(),
    }


def get_velocity(company: str) -> Optional[dict]:
    """
    Returns hiring velocity data or None.
    {
      "company": "Acme",
      "jobs_in_window": 15,
      "window_days": 30,
      "velocity": "high" | "medium" | "low" | "unknown",
      "label": "15 jobs in 30 days"
    }
    """
    import time
    key = _cache_key(company)
    entry = _CACHE.get(key)
    if not entry:
        return None
    # Check TTL
    if time.time() - entry["ts"] > _CACHE_TTL:
        del _CACHE[key]
        return None

    count = entry["count"]
    window = entry["window_days"]
    if count >= 10:
        velocity = "high"
    elif count >= 3:
        velocity = "medium"
    elif count >= 1:
        velocity = "low"
    else:
        velocity = "unknown"

    return {
        "company": company,
        "jobs_in_window": count,
        "window_days": window,
        "velocity": velocity,
        "label": f"{count} jobs in {window} days",
    }


def batch_record(jobs: list[dict], window_days: int = 30) -> None:
    """
    Aggregate a list of job dicts (must have "company" key) and
    record per-company count into the velocity cache.
    """
    counts: Dict[str, int] = defaultdict(int)
    for job in jobs:
        company = (job.get("company") or "").strip()
        if company:
            counts[company] += 1
    for company, count in counts.items():
        record_jobs(company, count, window_days)


def velocity_label(company: str) -> str:
    """Quick label for display — 'High hiring', 'Medium hiring', etc."""
    data = get_velocity(company)
    if not data:
        return ""
    v = data["velocity"]
    return {"high": "High hiring", "medium": "Medium hiring",
            "low": "Low hiring", "unknown": ""}.get(v, "")
