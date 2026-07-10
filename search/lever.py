"""Lever public API — no auth needed."""
from __future__ import annotations
import asyncio
import logging
from typing import List
import httpx
from search.base import SearchResult

logger = logging.getLogger(__name__)

_COMPANIES = [
    "netflix", "uber", "square", "palantir", "plaid", "scale-ai", "anduril",
    "robinhood", "chime", "carta", "checkr", "sendbird", "mux", "watershed",
    "hex-technology", "dbt-labs", "census", "hightouch", "fivetran", "airbyte",
    "rudderstack", "metabase", "mode", "looker", "preset", "lightdash",
    "grafana", "pagerduty", "incident-io", "rootly", "firehydrant",
    "temporal", "inngest", "trigger", "windmill", "prefect", "dagster",
]


async def _fetch_company(client: httpx.AsyncClient, company: str,
                         query: str) -> List[SearchResult]:
    try:
        r = await client.get(
            f"https://api.lever.co/v0/postings/{company}",
            params={"mode": "json", "limit": 50},
            timeout=10)
        if r.status_code != 200:
            return []
        qtoks = set(t for t in query.lower().split() if len(t) > 2)
        out = []
        for job in r.json():
            title = (job.get("text") or "").strip()
            if not any(t in title.lower() for t in qtoks):
                continue
            cats = job.get("categories") or {}
            location = cats.get("location") or cats.get("allLocations") or ""
            if isinstance(location, list):
                location = location[0] if location else ""
            out.append(SearchResult(
                title=title,
                url=job.get("hostedUrl") or job.get("applyUrl") or "",
                snippet=f"Lever · {company} · {cats.get('team','')}",
                source="lever", score=0.95,
                raw={"company": company, "location": location,
                     "team": cats.get("team", ""),
                     "commitment": cats.get("commitment", ""),
                     "created_at": job.get("createdAt")}))
        return out
    except Exception as exc:
        logger.debug("lever[%s]: %s", company, exc)
        return []


async def search(client: httpx.AsyncClient, query: str) -> List[SearchResult]:
    results = await asyncio.gather(
        *[_fetch_company(client, c, query) for c in _COMPANIES],
        return_exceptions=True)
    out = [r for batch in results if isinstance(batch, list) for r in batch]
    if out:
        logger.info("lever: %d relevant jobs for '%s'", len(out), query[:50])
    return out
