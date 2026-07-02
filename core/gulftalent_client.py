"""
GulfTalent / Gulf Jobs Client.

GulfTalent.com blocks HTTP scrapers (403). This client uses working alternatives:
  1. Remotive API  — free, no auth, returns remote/global tech jobs
  2. Arbeitnow API — free, no auth, European + worldwide remote jobs

crawl_mode: "gulftalent"

Usage:
    {
        "portal_name": "GulfTalent",
        "crawl_mode": "gulftalent",
        "gulftalent_params": {
            "category": "software-dev",   # remotive category
            "location": "",               # location keyword filter
            "max_pages": 1,
            "results_wanted": 30,
        }
    }
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# Remotive — free remote jobs API (no key needed)
_REMOTIVE_URL = "https://remotive.com/api/remote-jobs"

# Arbeitnow — free European + worldwide jobs API (no key needed)
_ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"


async def _fetch_remotive(
    client: httpx.AsyncClient,
    category: str = "software-dev",
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """Fetch remote jobs from Remotive API."""
    params: Dict[str, Any] = {"limit": min(limit, 50)}
    if category:
        params["category"] = category

    try:
        resp = await client.get(_REMOTIVE_URL, params=params, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", [])
        results = []
        for job in jobs[:limit]:
            results.append({
                "title": job.get("title", "Unknown"),
                "source_url": job.get("url", _REMOTIVE_URL),
                "description": (
                    f"{job.get('company_name', '')} | "
                    f"{job.get('candidate_required_location', 'Remote')} | "
                    f"{job.get('job_type', '')}"
                ),
                "location": job.get("candidate_required_location", "Remote"),
                "price": job.get("salary", ""),
                "metadata": {
                    "type": "job",
                    "source": "remotive",
                    "company": job.get("company_name", ""),
                    "category": job.get("category", category),
                    "job_type": job.get("job_type", ""),
                    "tags": job.get("tags", []),
                    "scraped_at": datetime.utcnow().isoformat(),
                }
            })
        logger.info("gulftalent_client: remotive fetched count=%d", len(results))
        return results
    except Exception as exc:
        logger.error("gulftalent_client: remotive error: %s", exc)
        return []


async def _fetch_arbeitnow(
    client: httpx.AsyncClient,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Fetch jobs from Arbeitnow API (European + global remote)."""
    try:
        resp = await client.get(_ARBEITNOW_URL, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("data", [])
        results = []
        for job in jobs[:limit]:
            results.append({
                "title": job.get("title", "Unknown"),
                "source_url": job.get("url", _ARBEITNOW_URL),
                "description": (
                    f"{job.get('company_name', '')} | "
                    f"{', '.join(job.get('tags', [])[:3])}"
                ),
                "location": job.get("location", "Remote"),
                "price": "",
                "metadata": {
                    "type": "job",
                    "source": "arbeitnow",
                    "company": job.get("company_name", ""),
                    "remote": job.get("remote", False),
                    "visa_sponsorship": job.get("visa_sponsorship", False),
                    "tags": job.get("tags", []),
                    "scraped_at": datetime.utcnow().isoformat(),
                }
            })
        logger.info("gulftalent_client: arbeitnow fetched count=%d", len(results))
        return results
    except Exception as exc:
        logger.error("gulftalent_client: arbeitnow error: %s", exc)
        return []


async def fetch_gulftalent(portal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Entry point for crawl_mode='gulftalent'.
    GulfTalent.com blocks scrapers (403) — uses Remotive + Arbeitnow free APIs instead.
    """
    params = portal_config.get("gulftalent_params") or {}
    category = params.get("category", "software-dev")
    results_wanted = int(params.get("results_wanted", 30))

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30) as client:
        results: List[Dict[str, Any]] = []

        # Primary: Remotive
        remotive_jobs = await _fetch_remotive(client, category=category, limit=results_wanted)
        results.extend(remotive_jobs)

        # Secondary: Arbeitnow (fill remaining slots)
        remaining = results_wanted - len(results)
        if remaining > 0:
            arb_jobs = await _fetch_arbeitnow(client, limit=remaining)
            results.extend(arb_jobs)

    logger.info("gulftalent_client: total fetched=%d", len(results))
    return results[:results_wanted]
