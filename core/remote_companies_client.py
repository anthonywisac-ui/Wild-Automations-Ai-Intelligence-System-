"""
Remote Jobs — keyless aggregator APIs (no per-company slugs, no 404s).

Instead of guessing each company's ATS handle (which 404s), we query public
remote-job aggregators that already index thousands of companies worldwide.
All are keyless JSON APIs, global, and NOT blocked on datacenter IPs:

    Remotive · RemoteOK · Jobicy · Arbeitnow · WeWorkRemotely(RSS)

    await fetch("project manager", limit=80)  ->  [normalized job records]

Each source is independent + fail-soft, so one being down never breaks the rest.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)
_UA = {"User-Agent": "Mozilla/5.0 (compatible; WildAutomations/1.0)",
       "Accept": "application/json"}


def _rec(title, company, location, url, desc, salary=""):
    loc = location or "Remote"
    return {"title": (title or "").strip(), "source_url": url or "",
            "location": loc, "description": re.sub(r"<[^>]+>", " ", desc or "")[:600],
            "price": salary or "",
            "metadata": {"type": "job", "company": company or "", "source": "Remote Aggregator",
                         "remote": True, "salary": salary or ""}}


async def _remotive(client, q) -> List[Dict[str, Any]]:
    try:
        u = "https://remotive.com/api/remote-jobs" + (f"?search={q}&limit=60" if q else "?limit=60")
        r = await client.get(u, timeout=15)
        return [_rec(j.get("title"), j.get("company_name"),
                     j.get("candidate_required_location", "Remote"), j.get("url"),
                     j.get("description"), j.get("salary", ""))
                for j in (r.json().get("jobs") or [])] if r.status_code == 200 else []
    except Exception:
        return []


async def _remoteok(client, q) -> List[Dict[str, Any]]:
    try:
        r = await client.get("https://remoteok.com/api", timeout=15)
        if r.status_code != 200:
            return []
        out = []
        for j in r.json():
            if not isinstance(j, dict) or not j.get("position"):
                continue
            out.append(_rec(j.get("position"), j.get("company"),
                            j.get("location") or "Remote", j.get("url") or j.get("apply_url"),
                            j.get("description"), (j.get("salary_min") and
                            f"{j.get('salary_min')}-{j.get('salary_max')} USD") or ""))
        return out
    except Exception:
        return []


async def _jobicy(client, q) -> List[Dict[str, Any]]:
    try:
        u = "https://jobicy.com/api/v2/remote-jobs?count=50" + (f"&tag={q}" if q else "")
        r = await client.get(u, timeout=15)
        return [_rec(j.get("jobTitle"), j.get("companyName"), j.get("jobGeo", "Remote"),
                     j.get("url"), j.get("jobExcerpt"), (j.get("annualSalaryMin") and
                     f"{j.get('annualSalaryMin')}-{j.get('annualSalaryMax')} {j.get('salaryCurrency','USD')}") or "")
                for j in (r.json().get("jobs") or [])] if r.status_code == 200 else []
    except Exception:
        return []


async def _arbeitnow(client, q) -> List[Dict[str, Any]]:
    try:
        r = await client.get("https://www.arbeitnow.com/api/job-board-api", timeout=15)
        if r.status_code != 200:
            return []
        return [_rec(j.get("title"), j.get("company_name"), j.get("location", "Remote"),
                     j.get("url"), j.get("description"))
                for j in (r.json().get("data") or []) if j.get("remote")]
    except Exception:
        return []


async def fetch(query: str = "", limit: int = 80, companies: List[str] = None) -> List[Dict[str, Any]]:
    """Pull remote jobs from all aggregators, filter by the query keyword, dedup."""
    q = (query or "").strip()
    qtoks = [t for t in re.split(r"\s+", q.lower()) if len(t) > 2]
    out, seen = [], set()
    try:
        async with httpx.AsyncClient(headers=_UA, verify=False, follow_redirects=True) as client:
            lists = await asyncio.gather(
                _remotive(client, q), _remoteok(client, q),
                _jobicy(client, q), _arbeitnow(client, q), return_exceptions=True)
        for lst in lists:
            if not isinstance(lst, list):
                continue
            for j in lst:
                title = (j.get("title") or "")
                if not title:
                    continue
                blob = f"{title} {j.get('description','')}".lower()
                if qtoks and not any(t in blob for t in qtoks):
                    continue
                key = (title.lower()[:60] + "|" + (j.get("metadata", {}).get("company", "")).lower())
                if key in seen:
                    continue
                seen.add(key)
                out.append(j)
                if len(out) >= limit:
                    return out
    except Exception as exc:
        logger.info("remote aggregators fetch failed: %s", exc)
    return out
