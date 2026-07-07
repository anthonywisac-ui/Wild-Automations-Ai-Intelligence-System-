"""
Careers Pages — jobs from the user's companies that have NO public ATS API.

The user's list (data/remote_companies.csv) has a careers_url for every
company. 51 of them expose Greenhouse/Lever/Ashby/... APIs (handled by
remote_companies_client). THIS module covers the rest: it opens each
careers page like a person would, pulls the job links off it, and lets the
LLM separate real postings from navigation noise (same adaptive pattern as
board_scraper — survives redesigns, no per-site parsers).

111 pages can't be fetched on every search, so a ROTATING BATCH keeps it
fast: each search scrapes the next `_BATCH` un-cached companies and serves
everything else from a 12 h cache. Within ~10 searches the whole list is
warm and stays warm.

    records = await fetch("engineer")   # normalized job records
"""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
       "Accept": "text/html,application/xhtml+xml"}

_ROOT = os.path.dirname(os.path.dirname(__file__))
_CSV = os.path.join(_ROOT, "data", "remote_companies.csv")
_ATS_CACHE = os.path.join(_ROOT, "data", "company_boards_cache.json")

_BATCH = 12          # fresh careers pages fetched per search
_TTL = 12 * 3600     # per-company cache
_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_ROTOR = {"i": 0}

_JOB_LINK = re.compile(
    r"/jobs?[/-]|/careers?/|/vacanc|/positions?|/openings?|/apply|"
    r"greenhouse\.io|lever\.co|workable|ashbyhq|smartrecruiters|recruitee|"
    r"jobvite|icims|bamboohr|teamtailor|personio|/join", re.I)
_NOISE = re.compile(
    r"^(about|contact|blog|faq|pricing|home|privacy|terms|login|sign|read more|"
    r"learn more|our (team|story|values)|benefits|perks|culture|view all|see all)\b",
    re.I)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def _targets() -> List[Dict[str, str]]:
    """Companies WITH a careers_url but WITHOUT a working ATS board."""
    ats: Dict[str, str] = {}
    try:
        with open(_ATS_CACHE, encoding="utf-8") as f:
            ats = json.load(f)
    except Exception:
        pass
    rows = []
    try:
        with open(_CSV, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                name = (r.get("company_name") or "").strip()
                url = (r.get("careers_url") or r.get("website") or "").strip()
                if not name or not url.startswith("http"):
                    continue
                if _slug(name) in ats:
                    continue  # ATS module already covers this company
                rows.append({"name": name, "url": url})
    except Exception as exc:
        logger.info("careers_pages: csv load failed: %s", exc)
    return rows


def _rec(title, company, location, url) -> Dict[str, Any]:
    return {"title": (title or "").strip()[:160], "source_url": url or "",
            "location": (location or "").strip()[:100] or "Remote",
            "description": "", "price": "",
            "metadata": {"type": "job", "company": company or "",
                         "source": "Company Careers Page", "remote": True}}


async def _get(client: httpx.AsyncClient, url: str) -> str:
    """Direct fetch, Jina Reader fallback (JS-rendered careers pages)."""
    try:
        r = await client.get(url, timeout=12)
        if r.status_code == 200 and len(r.content) > 800:
            return r.content.decode("utf-8", errors="ignore")
    except Exception:
        pass
    try:
        jheads = {"X-Return-Format": "html"}
        if os.getenv("JINA_API_KEY"):
            jheads["Authorization"] = f"Bearer {os.getenv('JINA_API_KEY')}"
        r = await client.get(f"https://r.jina.ai/{url}", headers=jheads, timeout=20)
        if r.status_code == 200 and len(r.content) > 500:
            return r.content.decode("utf-8", errors="ignore")
    except Exception:
        pass
    return ""


async def _one(client: httpx.AsyncClient, company: Dict[str, str]) -> List[Dict[str, Any]]:
    """Scrape one company's careers page -> job records (cached 12 h)."""
    key = company["name"]
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    html = await _get(client, company["url"])
    if not html:
        _CACHE[key] = (time.time(), [])
        return []
    from core.board_scraper import _anchors  # same battle-tested anchor parser
    picked = []
    for text, href in _anchors(html, company["url"]):
        if _JOB_LINK.search(href) and not _NOISE.match(text):
            picked.append((text, href))
    # dedup, keep it sane
    seen, links = set(), []
    for t, h in picked:
        if h not in seen:
            seen.add(h)
            links.append((t, h))
    links = links[:25]

    rows: List[Dict[str, Any]] = []
    if links:
        try:
            from core.llm_client import get_llm
            llm = get_llm()
            if llm:
                lines = "\n".join(f"[{i}] {t}" for i, (t, _) in enumerate(links))
                out = await llm.complete(
                    f"Link texts from the careers page of '{company['name']}'. "
                    "Which are REAL individual job postings (not navigation, not "
                    "'view all jobs', not benefits pages)? Return ONLY a JSON array "
                    "[{\"i\":<index>,\"title\":\"..\",\"location\":\"..\"}] "
                    f"(location \"\" if absent).\nLinks:\n{lines}",
                    system="You output only a JSON array.", max_tokens=600)
                m = re.search(r"\[.*\]", out, re.S)
                if m:
                    for s in json.loads(m.group(0)):
                        i = int(s.get("i", -1))
                        if 0 <= i < len(links) and s.get("title"):
                            rows.append(_rec(s["title"], company["name"],
                                             s.get("location"), links[i][1]))
        except Exception as exc:
            logger.info("careers_pages llm skipped (%s): %s", key, exc)
        if not rows:  # no-LLM fallback: link text as title
            rows = [_rec(t, company["name"], "", h) for t, h in links[:10]]
    _CACHE[key] = (time.time(), rows)
    logger.info("careers_pages: %s -> %d jobs", key, len(rows))
    return rows


async def fetch(query: str = "", limit: int = 40) -> List[Dict[str, Any]]:
    """Jobs from non-ATS companies: warm cache + a rotating fresh batch."""
    targets = _targets()
    if not targets:
        return []
    now = time.time()
    warm = [t for t in targets
            if t["name"] in _CACHE and now - _CACHE[t["name"]][0] < _TTL]
    cold = [t for t in targets if t not in warm]
    # rotate through cold companies so the whole list gets covered over time
    start = _ROTOR["i"] % max(1, len(cold)) if cold else 0
    batch = (cold[start:] + cold[:start])[:_BATCH]
    _ROTOR["i"] += _BATCH

    out: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(headers=_UA, verify=False,
                                     follow_redirects=True) as client:
            fresh = await asyncio.wait_for(
                asyncio.gather(*[_one(client, c) for c in batch],
                               return_exceptions=True), timeout=40)
        for lst in fresh:
            if isinstance(lst, list):
                out += lst
    except Exception as exc:
        logger.info("careers_pages batch failed: %s", exc)
    for t in warm:
        out += _CACHE[t["name"]][1]

    # query relevance filter (loose — title match on any token)
    qtoks = [t for t in re.split(r"\s+", (query or "").lower()) if len(t) > 2]
    if qtoks:
        out = [j for j in out
               if any(t in j["title"].lower() for t in qtoks)] or out[:10]
    return out[:limit]
