"""
Remote Companies — scrape jobs straight from remote-first companies' own ATS.

Most companies on the well-known remote-companies list publish jobs through a
public ATS JSON API (Greenhouse / Lever / Ashby). We hit those directly — fast,
global, and NOT rate-limited/blocked like Indeed/LinkedIn on datacenter IPs. Any
company whose slug is wrong simply 404s and is skipped.

    await fetch("project manager", limit=60)  ->  [normalized job records]
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

# Remote-first companies (slug = ATS handle). Wrong slugs 404 gracefully.
_COMPANIES = [
    "gitlab", "automattic", "zapier", "doist", "buffer", "hotjar", "1password",
    "coinbase", "cloudflare", "hashicorp", "elastic", "canonical", "fastly",
    "gitpod", "vercel", "supabase", "remotecom", "close", "mattermost", "postman",
    "sourcegraph", "netlify", "planetscale", "circleci", "grafana", "confluent",
    "webflow", "loom", "airbyte", "dbtlabs", "temporaltechnologies", "cockroachlabs",
    "clickup", "monday", "hopin", "deel", "rippling", "brex", "ramp", "notion",
    "figma", "linear", "retool", "render", "railway", "fly", "chainlink", "kraken",
    "digitalocean", "twilio", "stripe", "shopify", "reddit", "discord", "asana",
    "aircall", "pleo", "personio", "contentful", "algolia", "sentry", "auth0",
    "okta", "hashnode", "typeform", "miro", "pitch", "loket", "float", "toggl",
    "andela", "toptal", "crossover", "x-team", "gun-io", "arc-dev", "turing",
]

_UA = {"User-Agent": "Mozilla/5.0 (compatible; WildAutomations/1.0)"}


def _rec(title, company, location, url, desc):
    return {"title": (title or "").strip(),
            "source_url": url or "", "location": location or "Remote",
            "description": (desc or "")[:500], "price": "",
            "metadata": {"type": "job", "company": company, "source": "RemoteCo ATS",
                         "remote": "remote" in (location or "").lower()}}


async def _lever(client, co) -> List[Dict[str, Any]]:
    try:
        r = await client.get(f"https://api.lever.co/v0/postings/{co}?mode=json", timeout=10)
        if r.status_code != 200:
            return []
        out = []
        for j in r.json()[:40]:
            cats = j.get("categories") or {}
            out.append(_rec(j.get("text"), co.title(), cats.get("location", "Remote"),
                            j.get("hostedUrl"), j.get("descriptionPlain")))
        return out
    except Exception:
        return []


async def _greenhouse(client, co) -> List[Dict[str, Any]]:
    try:
        r = await client.get(
            f"https://boards-api.greenhouse.io/v1/boards/{co}/jobs?content=true", timeout=10)
        if r.status_code != 200:
            return []
        out = []
        for j in (r.json().get("jobs") or [])[:40]:
            loc = (j.get("location") or {}).get("name", "Remote")
            out.append(_rec(j.get("title"), co.title(), loc, j.get("absolute_url"),
                            (j.get("content") or "").replace("&lt;", "<")[:500]))
        return out
    except Exception:
        return []


async def _ashby(client, co) -> List[Dict[str, Any]]:
    try:
        r = await client.get(
            f"https://api.ashbyhq.com/posting-api/job-board/{co}", timeout=10)
        if r.status_code != 200:
            return []
        out = []
        for j in (r.json().get("jobs") or [])[:40]:
            out.append(_rec(j.get("title"), co.title(), j.get("locationName", "Remote"),
                            j.get("jobUrl"), j.get("descriptionPlain")))
        return out
    except Exception:
        return []


async def fetch(query: str = "", limit: int = 60, companies: List[str] = None) -> List[Dict[str, Any]]:
    """Pull jobs from every configured company's ATS, filter by the query keyword."""
    cos = companies or _COMPANIES
    q = (query or "").lower()
    qtoks = [t for t in q.split() if len(t) > 2]
    out: List[Dict[str, Any]] = []
    sem = asyncio.Semaphore(20)

    async def one(client, co):
        async with sem:
            for fn in (_greenhouse, _lever, _ashby):
                jobs = await fn(client, co)
                if jobs:
                    return jobs
            return []

    try:
        async with httpx.AsyncClient(headers=_UA, verify=False, follow_redirects=True) as client:
            results = await asyncio.gather(*[one(client, c) for c in cos], return_exceptions=True)
        for lst in results:
            if isinstance(lst, list):
                for j in lst:
                    title = (j.get("title") or "").lower()
                    blob = f"{title} {j.get('description','')}".lower()
                    if not qtoks or any(t in blob for t in qtoks):
                        out.append(j)
                        if len(out) >= limit:
                            return out
    except Exception as exc:
        logger.info("remote_companies fetch failed: %s", exc)
    return out
