"""Greenhouse public API — no auth, no rate limit for small scale."""
from __future__ import annotations
import asyncio
import logging
from typing import List
import httpx
from search.base import SearchResult

logger = logging.getLogger(__name__)

_COMPANIES = [
    "airbnb", "stripe", "shopify", "notion", "figma", "coinbase", "datadog",
    "gitlab", "dropbox", "cloudflare", "twilio", "asana", "brex", "reddit",
    "pinterest", "affirm", "coursera", "databricks", "benchling", "samsara",
    "flexport", "gusto", "deel", "lattice", "rippling", "retool", "vercel",
    "linear", "loom", "mercury", "dbt-labs", "posthog", "clerk", "resend",
    "segment", "mixpanel", "amplitude", "contentful", "sanity", "hasura",
    "supabase-io", "fly", "railway", "render", "neon", "turso", "xata",
    "hubspot", "zendesk", "intercom", "freshworks", "sendgrid", "twilio",
]


async def _fetch_company(client: httpx.AsyncClient, company: str,
                         query: str) -> List[SearchResult]:
    try:
        r = await client.get(
            f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs",
            params={"content": "false"},
            timeout=10)
        if r.status_code != 200:
            return []
        qtoks = set(t for t in query.lower().split() if len(t) > 2)
        out = []
        for job in r.json().get("jobs", []):
            title = (job.get("title") or "").strip()
            if not any(t in title.lower() for t in qtoks):
                continue
            url = (job.get("absolute_url") or "").strip()
            offices = job.get("offices") or []
            location = ""
            if isinstance(offices, list) and offices:
                o = offices[0]
                location = o.get("name", "") if isinstance(o, dict) else ""
            out.append(SearchResult(
                title=title, url=url,
                snippet=f"Greenhouse · {company} · {location}",
                source="greenhouse", score=0.95,
                raw={"company": company, "location": location,
                     "updated_at": job.get("updated_at", ""),
                     "job_id": job.get("id")}))
        return out
    except Exception as exc:
        logger.debug("greenhouse[%s]: %s", company, exc)
        return []


async def search(client: httpx.AsyncClient, query: str) -> List[SearchResult]:
    results = await asyncio.gather(
        *[_fetch_company(client, c, query) for c in _COMPANIES],
        return_exceptions=True)
    out = [r for batch in results if isinstance(batch, list) for r in batch]
    if out:
        logger.info("greenhouse: %d relevant jobs for '%s'", len(out), query[:50])
    return out
