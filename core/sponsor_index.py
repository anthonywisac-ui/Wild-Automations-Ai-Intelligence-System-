"""
Sponsor Index — the visa-intelligence moat.

Downloads the FULL official UK licensed-sponsor register (reusing the gov.uk CSV
locator from uk_jobs_client), builds a canonical-name → sponsor lookup, and
persists it to SQLite so it's fetched at most weekly (the register's cadence).

    await ensure_loaded()             # load cache (fetch if empty/stale)
    lookup("Google UK Ltd")           # -> {matched, name, city, county, routes[], confidence, evidence}

Government data only: a match is confidence 1.0 (exact canonical) or lower for a
fuzzy token match. Never guesses — no match => matched=False ("Not Verified").
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_DB = Path(__file__).resolve().parent.parent / "data" / "crm_store.sqlite3"
_LOCK = threading.Lock()
_REFRESH_SECONDS = 7 * 24 * 3600  # weekly

_index: Dict[str, Dict[str, Any]] = {}   # canon -> {name, city, county, routes[set]}
_loaded_at = 0.0
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; WildAutomations/1.0)"}

_SUFFIX = re.compile(r"\b(ltd|limited|llc|inc|plc|llp|co|company|group|holdings|uk|"
                     r"services|solutions|international|the)\b", re.I)


def _canon(name: str) -> str:
    n = (name or "").lower()
    n = re.sub(r"[^a-z0-9&\s]", " ", n)
    n = _SUFFIX.sub(" ", n)
    return re.sub(r"\s+", " ", n).strip()


def _init() -> None:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS uk_sponsors ("
                     "canon TEXT PRIMARY KEY, name TEXT, city TEXT, county TEXT, "
                     "routes TEXT, first_seen TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS uk_sponsors_meta (k TEXT PRIMARY KEY, v TEXT)")
        conn.commit()


_init()


async def _find_csv_url(client: httpx.AsyncClient) -> str:
    try:
        r = await client.get("https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers",
                             headers=_HEADERS, timeout=20)
        if r.status_code == 200:
            m = re.findall(r'href="(https://assets\.publishing\.service\.gov\.uk[^"]+\.csv)"', r.text)
            if m:
                return m[0]
    except Exception as exc:
        logger.warning("sponsor_index: csv url find failed: %s", exc)
    return ""


async def refresh() -> int:
    """Download the full register and (re)build the index + SQLite cache."""
    global _index, _loaded_at
    try:
        async with httpx.AsyncClient(timeout=60, headers=_HEADERS, follow_redirects=True) as client:
            url = await _find_csv_url(client)
            if not url:
                return len(_index)
            r = await client.get(url, timeout=90)
            if r.status_code != 200:
                return len(_index)
        idx: Dict[str, Dict[str, Any]] = {}
        reader = csv.DictReader(io.StringIO(r.text))
        for row in reader:
            org = (row.get("Organisation Name") or row.get("name") or "").strip()
            if not org:
                continue
            canon = _canon(org)
            if not canon:
                continue
            route = (row.get("Route") or row.get("route") or "").strip()
            e = idx.setdefault(canon, {"name": org, "city": (row.get("Town/City") or "").strip(),
                                       "county": (row.get("County") or "").strip(), "routes": set()})
            if route:
                e["routes"].add(route)
        _index = idx
        _loaded_at = time.time()
        _persist(idx)
        logger.info("sponsor_index: refreshed %d sponsors", len(idx))
        return len(idx)
    except Exception as exc:
        logger.warning("sponsor_index: refresh failed: %s", exc)
        return len(_index)


def _persist(idx: Dict[str, Dict[str, Any]]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=30) as conn:
            conn.execute("DELETE FROM uk_sponsors")
            conn.executemany(
                "INSERT OR REPLACE INTO uk_sponsors (canon,name,city,county,routes,first_seen) "
                "VALUES (?,?,?,?,?,?)",
                [(c, e["name"], e["city"], e["county"], json.dumps(sorted(e["routes"])), now)
                 for c, e in idx.items()])
            conn.execute("INSERT OR REPLACE INTO uk_sponsors_meta (k,v) VALUES ('loaded_at',?)",
                         (str(time.time()),))
            conn.commit()
    except Exception as exc:
        logger.warning("sponsor_index: persist failed: %s", exc)


def _load_cache() -> None:
    global _index, _loaded_at
    if _index:
        return
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            rows = conn.execute("SELECT canon,name,city,county,routes FROM uk_sponsors").fetchall()
            for c, name, city, county, routes in rows:
                _index[c] = {"name": name, "city": city, "county": county,
                             "routes": set(json.loads(routes or "[]"))}
            m = conn.execute("SELECT v FROM uk_sponsors_meta WHERE k='loaded_at'").fetchone()
            _loaded_at = float(m[0]) if m else 0.0
    except Exception:
        pass


async def ensure_loaded() -> None:
    """Load from SQLite; fetch fresh if empty or stale (>1 week)."""
    _load_cache()
    if not _index or (time.time() - _loaded_at) > _REFRESH_SECONDS:
        await refresh()


def lookup(company: str) -> Dict[str, Any]:
    """Return the sponsor match for a company (gov-verified). Never guesses."""
    _load_cache()
    canon = _canon(company)
    if not canon:
        return {"matched": False, "reason": "no company name"}
    # 1. exact canonical match (confidence 1.0)
    hit = _index.get(canon)
    conf = 1.0
    if not hit:
        # 2. token-subset fuzzy (all query tokens present in a sponsor canon)
        toks = [t for t in canon.split() if len(t) > 2]
        if toks:
            for c, e in _index.items():
                cset = set(c.split())
                if all(t in cset for t in toks):
                    hit = e
                    conf = round(0.75 + 0.05 * min(4, len(toks)), 2)
                    break
    if not hit:
        return {"matched": False, "status": "Not Verified"}
    return {
        "matched": True, "status": "Verified", "name": hit["name"],
        "city": hit.get("city", ""), "county": hit.get("county", ""),
        "routes": sorted(hit.get("routes", [])), "confidence": conf,
        "evidence": {"source": "UK Gov Register of Licensed Sponsors",
                     "url": "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers",
                     "match_type": "exact" if conf == 1.0 else "fuzzy"},
    }


def stats() -> Dict[str, Any]:
    _load_cache()
    age = int(time.time() - _loaded_at) if _loaded_at else None
    return {"sponsors_indexed": len(_index), "last_refresh_age_s": age}
