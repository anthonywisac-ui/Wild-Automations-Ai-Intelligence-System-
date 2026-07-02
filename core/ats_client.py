"""
ATS (Applicant Tracking System) Job Board Aggregator.

Sources:
  - Greenhouse.io   → boards-api.greenhouse.io (public, no auth)
  - WeWorkRemotely  → RSS feed (public)
  - RemoteOK        → JSON API (public, no auth)

crawl_mode: "ats_jobs"

Usage:
    {
        "portal_name": "ATS Jobs",
        "crawl_mode": "ats_jobs",
        "ats_params": {
            "source": "greenhouse" | "wwr" | "remoteok" | "all",
            "companies": ["stripe", "airbnb", "shopify"],   # for greenhouse
            "limit": 30,
        }
    }
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html, */*",
}

# Well-known companies using Greenhouse (public boards)
_DEFAULT_GREENHOUSE_COMPANIES = [
    "airbnb", "stripe", "shopify", "dropbox", "spotify",
    "github", "figma", "notion", "airtable", "confluent",
]


async def _fetch_greenhouse(
    client: httpx.AsyncClient,
    companies: List[str],
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """Fetch jobs from multiple Greenhouse company boards (public API, no auth)."""
    results: List[Dict[str, Any]] = []

    for company in companies:
        if len(results) >= limit:
            break
        url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
        try:
            resp = await client.get(url, headers=_HEADERS, timeout=15)
            if resp.status_code != 200:
                logger.debug("ats_client: greenhouse/%s status=%d", company, resp.status_code)
                continue
            data = resp.json()
            jobs = data.get("jobs", [])
            for job in jobs[: max(1, limit // len(companies))]:
                location = job.get("location", {})
                loc_name = location.get("name", "") if isinstance(location, dict) else str(location)
                results.append({
                    "title": job.get("title", "Unknown"),
                    "source_url": job.get("absolute_url", f"https://boards.greenhouse.io/{company}"),
                    "description": f"{company.title()} | {loc_name} | via Greenhouse ATS",
                    "location": loc_name or "Remote",
                    "price": "",
                    "metadata": {
                        "type": "job",
                        "source": "greenhouse",
                        "company": company,
                        "job_id": str(job.get("id", "")),
                        "updated_at": job.get("updated_at", ""),
                        "scraped_at": datetime.utcnow().isoformat(),
                    },
                })
            logger.info("ats_client: greenhouse/%s fetched=%d", company, len(jobs))
        except Exception as exc:
            logger.debug("ats_client: greenhouse/%s error: %s", company, exc)

    return results[:limit]


async def _fetch_wwr(
    client: httpx.AsyncClient,
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """Fetch remote jobs from WeWorkRemotely RSS feed."""
    url = "https://weworkremotely.com/remote-jobs.rss"
    try:
        resp = await client.get(url, headers={**_HEADERS, "Accept": "text/xml"}, timeout=15)
        resp.raise_for_status()
        xml = resp.text

        items = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)
        results = []
        for item in items[:limit]:
            title_m = re.search(r"<title>([^<]+)</title>", item)
            link_m = re.search(r"<link>([^<]+)</link>", item)
            region_m = re.search(r"<region>([^<]*)</region>", item)
            pub_m = re.search(r"<pubDate>([^<]+)</pubDate>", item)

            raw_title = (title_m.group(1) if title_m else "").strip()
            if not raw_title or raw_title.startswith("We Work Remotely"):
                continue

            # Title format: "Company: Job Title"
            parts = raw_title.split(": ", 1)
            company = parts[0].strip() if len(parts) == 2 else ""
            job_title = parts[1].strip() if len(parts) == 2 else raw_title

            results.append({
                "title": job_title,
                "source_url": (link_m.group(1) if link_m else url).strip(),
                "description": f"{company} | {region_m.group(1).strip() if region_m else 'Remote'} | WeWorkRemotely",
                "location": (region_m.group(1) or "Remote").strip(),
                "price": "",
                "metadata": {
                    "type": "job",
                    "source": "weworkremotely",
                    "company": company,
                    "published": (pub_m.group(1) if pub_m else "").strip(),
                    "scraped_at": datetime.utcnow().isoformat(),
                },
            })

        logger.info("ats_client: wwr fetched=%d", len(results))
        return results
    except Exception as exc:
        logger.error("ats_client: wwr error: %s", exc)
        return []


async def _fetch_remoteok(
    client: httpx.AsyncClient,
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """Fetch remote tech jobs from RemoteOK JSON API."""
    url = "https://remoteok.com/api"
    try:
        resp = await client.get(
            url,
            headers={**_HEADERS, "Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        raw = resp.json()
        jobs = [x for x in raw if isinstance(x, dict) and x.get("position")]

        results = []
        for job in jobs[:limit]:
            tags = job.get("tags", []) or []
            results.append({
                "title": job.get("position", "Unknown"),
                "source_url": job.get("url", url),
                "description": f"{job.get('company', '')} | {', '.join(tags[:4])} | RemoteOK",
                "location": job.get("location", "Remote") or "Remote",
                "price": str(job.get("salary", "") or ""),
                "metadata": {
                    "type": "job",
                    "source": "remoteok",
                    "company": job.get("company", ""),
                    "tags": tags,
                    "date": str(job.get("date", "")),
                    "scraped_at": datetime.utcnow().isoformat(),
                },
            })

        logger.info("ats_client: remoteok fetched=%d", len(results))
        return results
    except Exception as exc:
        logger.error("ats_client: remoteok error: %s", exc)
        return []


async def fetch_ats_jobs(portal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Entry point for crawl_mode='ats_jobs'."""
    params = portal_config.get("ats_params") or {}
    source = params.get("source", "all")
    companies = params.get("companies", _DEFAULT_GREENHOUSE_COMPANIES)
    limit = int(params.get("limit", 30))

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30) as client:
        results: List[Dict[str, Any]] = []

        if source in ("greenhouse", "all"):
            results += await _fetch_greenhouse(client, companies=companies, limit=limit)

        if source in ("wwr", "all"):
            remaining = limit - len(results)
            results += await _fetch_wwr(client, limit=max(10, remaining))

        if source in ("remoteok", "all"):
            remaining = limit - len(results)
            results += await _fetch_remoteok(client, limit=max(10, remaining))

    logger.info("ats_client: total fetched=%d", len(results))
    return results[:limit]
