"""
Freshness — posting-time intelligence for the "sniper" requirement:
job posted somewhere → visible here immediately, every record stamped with
WHEN it was posted and HOW fresh it is.

parse(raw)            -> ISO string or ""     (many formats, fail-soft)
age_hours(iso)        -> float hours since posted (None if unknown)
ago(iso)              -> "2h ago" / "3d ago" human string ("" if unknown)
is_fresh(iso, hours)  -> bool, posted within the window
stamp(job)            -> adds posted_iso / posted_ago / fresh to a job dict
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
    "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",  # RSS pubDate
    "%d %b %Y", "%b %d, %Y", "%d/%m/%Y", "%m/%d/%Y",
)

_REL_RE = re.compile(
    r"(\d+)\s*(minute|min|hour|hr|day|week|month)s?\s*ago", re.I)


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse(raw: Any) -> str:
    """Any date-ish input -> ISO-8601 UTC string, or "" if unparseable."""
    if raw is None:
        return ""
    if isinstance(raw, datetime):
        return _utc(raw).isoformat()
    s = str(raw).strip()
    if not s:
        return ""
    # relative: "3 days ago", "2 hours ago" (job boards love these)
    m = _REL_RE.search(s)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        hours = {"minute": n / 60, "min": n / 60, "hour": n, "hr": n,
                 "day": n * 24, "week": n * 168, "month": n * 720}[unit]
        return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    if s.lower() in ("today", "just posted", "new"):
        return datetime.now(timezone.utc).isoformat()
    if s.lower() == "yesterday":
        return (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    # ISO with trailing Z
    iso_try = s.replace("Z", "+00:00")
    try:
        return _utc(datetime.fromisoformat(iso_try)).isoformat()
    except ValueError:
        pass
    for fmt in _FORMATS:
        try:
            return _utc(datetime.strptime(s, fmt)).isoformat()
        except ValueError:
            continue
    return ""


def age_hours(iso: str) -> Optional[float]:
    if not iso:
        return None
    try:
        dt = _utc(datetime.fromisoformat(iso))
    except ValueError:
        return None
    return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)


def ago(iso: str) -> str:
    h = age_hours(iso)
    if h is None:
        return ""
    if h < 1:
        return f"{max(1, int(h * 60))}m ago"
    if h < 24:
        return f"{int(h)}h ago"
    if h < 24 * 30:
        return f"{int(h / 24)}d ago"
    return f"{int(h / 720)}mo ago"


def is_fresh(iso: str, hours: float = 48) -> bool:
    h = age_hours(iso)
    return h is not None and h <= hours


def stamp(job: Dict[str, Any], raw_posted: Any = None) -> Dict[str, Any]:
    """Return a copy of the job dict with posted_iso / posted_ago / fresh set."""
    iso = parse(raw_posted if raw_posted is not None else job.get("posted"))
    return {**job, "posted_iso": iso, "posted_ago": ago(iso),
            "fresh": is_fresh(iso)}
