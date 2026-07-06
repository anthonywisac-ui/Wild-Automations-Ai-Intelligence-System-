"""
Subscriptions — 3 plans + 3-day trial (trial = 2 jobs/day cap).

Plans (prices are PLACEHOLDERS — set via env or data/plans.json later,
payment integration comes after pricing is final):

  sprint   — weekly   — urgent mode, 1 domain, 1-country visa alerts
  standard — monthly  — 1 domain (job OR admission), 2-country visa alerts
  premium  — monthly  — BOTH domains, all corridors, priority chat

Trial: 3 days from first start, hard cap TRIAL_JOBS_PER_DAY results/day.
Users are identified by a free-form `user` id (phone/email) — no auth yet;
WhatsApp number is the natural id since delivery already goes there.

Tables (data/crm_store.sqlite3): subscribers, sub_usage
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_DB = Path(__file__).resolve().parent.parent / "data" / "crm_store.sqlite3"
_LOCK = threading.Lock()

TRIAL_DAYS = 3
TRIAL_JOBS_PER_DAY = 2

# Prices intentionally None until final pricing is decided.
PLANS = {
    "sprint": {
        "id": "sprint", "name": "Sprint", "billing": "weekly", "price": None,
        "currency": "GBP",
        "tagline": "Urgent mode — deadline in weeks, not months",
        "features": [
            "Unlimited matched jobs OR admissions (1 domain)",
            "Visa alerts for 1 country",
            "CV / profile analysis",
            "WhatsApp delivery",
            "AI chat follow-up (limited)",
        ],
    },
    "standard": {
        "id": "standard", "name": "Standard", "billing": "monthly", "price": None,
        "currency": "GBP",
        "tagline": "Steady search — one goal, fully covered",
        "features": [
            "Unlimited matched jobs OR admissions (1 domain)",
            "Visa alerts for 2 countries",
            "CV / profile analysis",
            "WhatsApp delivery",
            "AI chat follow-up",
        ],
    },
    "premium": {
        "id": "premium", "name": "Premium", "billing": "monthly", "price": None,
        "currency": "GBP",
        "tagline": "Jobs + admissions + every visa corridor",
        "features": [
            "Unlimited matched jobs AND admissions (both domains)",
            "Visa alerts — all supported corridors",
            "CV / profile analysis (priority)",
            "WhatsApp delivery + daily digest",
            "Unlimited AI chat follow-up",
        ],
    },
}


def _init() -> None:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS subscribers ("
            "user_id TEXT PRIMARY KEY, plan TEXT NOT NULL, "
            "trial_started_at TEXT, trial_ends_at TEXT, "
            "activated_at TEXT, expires_at TEXT, created_at TEXT NOT NULL)")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sub_usage ("
            "user_id TEXT NOT NULL, day TEXT NOT NULL, jobs_used INTEGER NOT NULL DEFAULT 0, "
            "PRIMARY KEY (user_id, day))")
        conn.commit()


_init()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _norm_user(user_id: str) -> str:
    return (user_id or "").strip().lower()


def plans() -> Dict[str, Any]:
    """Public plan catalogue + trial terms (for /api/plans and the UI)."""
    return {
        "plans": list(PLANS.values()),
        "trial": {"days": TRIAL_DAYS, "jobs_per_day": TRIAL_JOBS_PER_DAY,
                  "note": "Free trial — top matches only, delivered instantly."},
        "pricing_status": "to_be_announced",
    }


def start_trial(user_id: str) -> Dict[str, Any]:
    """Start (or return the existing) 3-day trial for a user."""
    uid = _norm_user(user_id)
    if not uid:
        return {"error": "user id (phone/email) required"}
    now = _now()
    with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
        row = conn.execute(
            "SELECT plan, trial_started_at, trial_ends_at, expires_at "
            "FROM subscribers WHERE user_id=?", (uid,)).fetchone()
        if row is None:
            ends = now + timedelta(days=TRIAL_DAYS)
            conn.execute(
                "INSERT INTO subscribers (user_id, plan, trial_started_at, trial_ends_at, created_at) "
                "VALUES (?,?,?,?,?)",
                (uid, "trial", now.isoformat(), ends.isoformat(), now.isoformat()))
            conn.commit()
            return {"user": uid, "plan": "trial", "trial_ends_at": ends.isoformat(),
                    "jobs_per_day": TRIAL_JOBS_PER_DAY, "started": True}
    return get_status(uid)


def activate(user_id: str, plan: str, days: Optional[int] = None) -> Dict[str, Any]:
    """Activate a paid plan (manual/admin for now — payment gateway comes later)."""
    uid = _norm_user(user_id)
    if plan not in PLANS:
        return {"error": f"unknown plan '{plan}'"}
    now = _now()
    period = days or (7 if PLANS[plan]["billing"] == "weekly" else 30)
    expires = now + timedelta(days=period)
    with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
        conn.execute(
            "INSERT INTO subscribers (user_id, plan, activated_at, expires_at, created_at) "
            "VALUES (?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET "
            "plan=excluded.plan, activated_at=excluded.activated_at, expires_at=excluded.expires_at",
            (uid, plan, now.isoformat(), expires.isoformat(), now.isoformat()))
        conn.commit()
    logger.info("subscriptions: activated user=%s plan=%s until=%s", uid, plan, expires)
    return get_status(uid)


def get_status(user_id: str) -> Dict[str, Any]:
    """Current subscription state: none | trial | trial_expired | active | expired."""
    uid = _norm_user(user_id)
    if not uid:
        return {"state": "none"}
    now = _now()
    with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
        row = conn.execute(
            "SELECT plan, trial_started_at, trial_ends_at, activated_at, expires_at "
            "FROM subscribers WHERE user_id=?", (uid,)).fetchone()
        if row is None:
            return {"user": uid, "state": "none", "plans": list(PLANS)}
        plan, t_start, t_end, act, exp = row
        day = now.date().isoformat()
        used_row = conn.execute(
            "SELECT jobs_used FROM sub_usage WHERE user_id=? AND day=?", (uid, day)).fetchone()
        used = used_row[0] if used_row else 0

    if plan in PLANS:  # paid
        if exp and datetime.fromisoformat(exp) > now:
            return {"user": uid, "state": "active", "plan": plan, "expires_at": exp}
        return {"user": uid, "state": "expired", "plan": plan, "expired_at": exp,
                "plans": list(PLANS)}
    # trial
    if t_end and datetime.fromisoformat(t_end) > now:
        return {"user": uid, "state": "trial", "trial_ends_at": t_end,
                "jobs_per_day": TRIAL_JOBS_PER_DAY,
                "jobs_used_today": used,
                "jobs_left_today": max(0, TRIAL_JOBS_PER_DAY - used)}
    return {"user": uid, "state": "trial_expired", "trial_ended_at": t_end,
            "plans": list(PLANS)}


def allowed_results(user_id: str, requested: int) -> Dict[str, Any]:
    """Quota gate for a match run. Returns how many results the user may receive
    and consumes trial quota. Paid/active => unlimited. No user id => legacy
    behaviour (ungated) so the existing dashboard keeps working."""
    uid = _norm_user(user_id)
    if not uid:
        return {"allowed": requested, "state": "anonymous"}
    st = get_status(uid)
    state = st.get("state")
    if state == "active":
        return {"allowed": requested, "state": "active", "plan": st.get("plan")}
    if state == "none":
        return {"allowed": 0, "state": "none",
                "message": "Start your free 3-day trial to receive matches.",
                "plans": plans()}
    if state in ("trial_expired", "expired"):
        return {"allowed": 0, "state": state,
                "message": "Your access has ended — pick a plan to continue.",
                "plans": plans()}
    # trial: consume up to remaining daily quota
    left = int(st.get("jobs_left_today", 0))
    grant = max(0, min(requested, left))
    if grant:
        day = _now().date().isoformat()
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            conn.execute(
                "INSERT INTO sub_usage (user_id, day, jobs_used) VALUES (?,?,?) "
                "ON CONFLICT(user_id, day) DO UPDATE SET jobs_used = jobs_used + ?",
                (uid, day, grant, grant))
            conn.commit()
    out = {"allowed": grant, "state": "trial", "trial_ends_at": st.get("trial_ends_at"),
           "jobs_left_today": max(0, left - grant)}
    if grant < requested:
        out["message"] = (f"Trial gives {TRIAL_JOBS_PER_DAY} matches/day — "
                          "upgrade for unlimited matches.")
        out["plans"] = plans()
    return out
