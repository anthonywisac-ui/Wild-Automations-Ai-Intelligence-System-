"""
Search Orchestrator — runs all providers concurrently, merges and deduplicates.
Entry point: await search_all(job, location, job_type)
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import List, Dict
from urllib.parse import urlparse

import httpx

from search.base import SearchResult
from search import jina, tavily, serper, greenhouse, lever, ashby

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ATS site-targeted queries — go straight to CAPTCHA-free job pages
_ATS_SITES = [
    "site:boards.greenhouse.io",
    "site:jobs.lever.co",
    "site:jobs.ashby.com",
    "site:apply.workable.com",
    "site:jobs.eu.lever.co",
    "site:boards.eu.greenhouse.io",
    "site:recruitee.com",
    "site:teamtailor.com",
    "site:bamboohr.com",
    "site:smartrecruiters.com",
]

_SYNONYMS: Dict[str, List[str]] = {
    "software engineer": ["backend engineer", "software developer"],
    "frontend": ["react developer", "ui engineer"],
    "data scientist": ["ml engineer", "machine learning engineer"],
    "project manager": ["program manager", "delivery manager"],
    "devops": ["platform engineer", "sre"],
    "designer": ["ux designer", "product designer"],
    "data analyst": ["business analyst", "bi analyst"],
}


def _expand(job: str, location: str, job_type: str) -> Dict[str, List[str]]:
    """Returns {'ats': [...], 'general': [...]} query lists."""
    loc = location.strip()
    jt = "remote" if job_type.lower() == "remote" else ""

    ats_queries = []
    for site in _ATS_SITES[:6]:   # top 6 ATS sites
        q = " ".join(x for x in (f'"{job}"', loc, jt, site) if x)
        ats_queries.append(q)

    general_queries = []
    for suffix in ["hiring", "apply now", "job opening"]:
        q = " ".join(x for x in (job, loc, jt, suffix) if x)
        general_queries.append(q)

    # synonym expansion
    for base, syns in _SYNONYMS.items():
        if base in job.lower():
            for syn in syns[:1]:
                q = " ".join(x for x in (syn, loc, jt) if x)
                general_queries.append(q)
            break

    return {"ats": ats_queries, "general": general_queries}


def _dedup(results: List[SearchResult]) -> List[SearchResult]:
    """Keep highest-score result per normalized URL."""
    seen: Dict[str, SearchResult] = {}
    for r in results:
        key = r.url.rstrip("/").split("?")[0].lower()
        if key not in seen or r.score > seen[key].score:
            seen[key] = r
    return sorted(seen.values(), key=lambda x: x.score, reverse=True)


async def search_all(job: str, location: str = "",
                     job_type: str = "") -> List[SearchResult]:
    """
    Runs all search providers concurrently.
    Returns merged, deduplicated, scored SearchResult list.
    """
    queries = _expand(job, location, job_type)
    primary_q = " ".join(x for x in (job, location, job_type) if x)
    ats_q = f'{job} {location} site:greenhouse.io OR site:lever.co OR site:ashby.com'.strip()

    async with httpx.AsyncClient(
        headers=_UA, follow_redirects=True, verify=False, timeout=25
    ) as client:
        tasks = [
            # Jina: ATS-targeted queries (Railway-safe primary)
            *[jina.search(client, q) for q in queries["ats"]],
            # Jina: general queries
            *[jina.search(client, q) for q in queries["general"][:2]],
            # Tavily: primary + ATS combo
            tavily.search(client, primary_q),
            tavily.search(client, ats_q),
            # Serper: Google results for ATS + general
            serper.search(client, ats_q),
            serper.search(client, primary_q),
            # ATS direct APIs — no search needed, structured data
            greenhouse.search(client, job),
            lever.search(client, job),
            ashby.search(client, job),
        ]

        try:
            raw = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=28)
        except asyncio.TimeoutError:
            logger.warning("search_all: timed out")
            return []

    all_results: List[SearchResult] = []
    for batch in raw:
        if isinstance(batch, list):
            all_results.extend(batch)

    deduped = _dedup(all_results)
    logger.info("search_all: %d raw → %d unique for '%s'",
                len(all_results), len(deduped), job[:40])
    return deduped
