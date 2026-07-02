# Inspired By: browser-use/browser-use
# Repository: https://github.com/browser-use/browser-use
# Feature: UTC time helpers with ISO formatting
# Reason: Consistent time handling across services
# ============================================================

from datetime import datetime, timezone
from typing import Optional

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def format_iso(dt: Optional[datetime] = None) -> str:
    if dt is None:
        dt = now_utc()
    return dt.isoformat()

def parse_iso(iso_str: str) -> datetime:
    try:
        return datetime.fromisoformat(iso_str)
    except ValueError:
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"
        return datetime.fromisoformat(iso_str)
