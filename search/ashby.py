"""Ashby public GraphQL API — no auth needed."""
from __future__ import annotations
import asyncio
import logging
from typing import List
import httpx
from search.base import SearchResult

logger = logging.getLogger(__name__)

_COMPANIES = [
    "openai", "anthropic", "mistral", "cohere", "huggingface", "ramp",
    "watershed", "hex", "posthog", "cal", "resend", "trigger",
    "inngest", "turso", "xata", "linear", "loom", "mercury", "deel",
    "remote", "oyster", "pilot", "gusto", "rippling", "lattice",
    "culture-amp", "leapsome", "15five", "betterworks", "reflektive",
]


async def _fetch_company(client: httpx.AsyncClient, company: str,
                         query: str) -> List[SearchResult]:
    try:
        r = await client.post(
            "https://api.ashbyhq.com/posting-api/job-board",
            json={"organizationHostedJobsPageName": company},
            timeout=10)
        if r.status_code != 200:
            return []
        qtoks = set(t for t in query.lower().split() if len(t) > 2)
        out = []
        for job in (r.json().get("jobs") or []):
            title = (job.get("title") or "").strip()
            if not any(t in title.lower() for t in qtoks):
                continue
            location = job.get("locationName") or ""
            is_remote = job.get("isRemote", False)
            out.append(SearchResult(
                title=title,
                url=job.get("jobUrl") or "",
                snippet=f"Ashby · {company} · {'Remote' if is_remote else location}",
                source="ashby", score=0.95,
                raw={"company": company, "location": location,
                     "remote": is_remote,
                     "department": job.get("departmentName", ""),
                     "employment_type": job.get("employmentType", "")}))
        return out
    except Exception as exc:
        logger.debug("ashby[%s]: %s", company, exc)
        return []


async def search(client: httpx.AsyncClient, query: str) -> List[SearchResult]:
    results = await asyncio.gather(
        *[_fetch_company(client, c, query) for c in _COMPANIES],
        return_exceptions=True)
    out = [r for batch in results if isinstance(batch, list) for r in batch]
    if out:
        logger.info("ashby: %d relevant jobs for '%s'", len(out), query[:50])
    return out
