"""
UK Sponsored Jobs Client.

Sources (from scrapers-info.md):
  - adityak74/only-sponsored-scraper → UK computer jobs with Skilled Worker visa sponsorship

FindAJob.dwp.gov.uk is now Next.js (JS-rendered, no accessible data).
UK Gov sponsor register CSV URL changes weekly.

This client uses:
  1. UK Gov sponsor register — scrapes gov.uk page to find current CSV URL dynamically
  2. Arbeitnow API — includes visa_sponsorship flag, many UK jobs

crawl_mode: "uk_sponsored_jobs"

Usage:
    {
        "portal_name": "UK Sponsored Jobs",
        "crawl_mode": "uk_sponsored_jobs",
        "uk_jobs_params": {
            "keywords": "software engineer",
            "max_pages": 1,
            "results_wanted": 30,
            "include_sponsor_list": True,
        }
    }
"""

import csv
import io
import logging
import re
from datetime import datetime
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_GOV_UK_SPONSOR_PAGE = "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"
_ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"


async def _find_sponsor_csv_url(client: httpx.AsyncClient) -> str:
    """Scrape gov.uk page to find current CSV download URL (it changes weekly)."""
    try:
        resp = await client.get(_GOV_UK_SPONSOR_PAGE, headers=_HEADERS, timeout=15)
        if resp.status_code == 200:
            csv_links = re.findall(
                r'href="(https://assets\.publishing\.service\.gov\.uk[^"]+\.csv)"',
                resp.text
            )
            if csv_links:
                return csv_links[0]
    except Exception as exc:
        logger.warning("uk_jobs_client: could not find CSV URL: %s", exc)
    return ""


async def _fetch_sponsor_list(
    client: httpx.AsyncClient,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Download official UK licensed sponsors list."""
    try:
        csv_url = await _find_sponsor_csv_url(client)
        if not csv_url:
            logger.warning("uk_jobs_client: sponsor CSV URL not found")
            return []

        resp = await client.get(csv_url, timeout=30)
        if resp.status_code != 200:
            logger.warning("uk_jobs_client: sponsor CSV status=%d", resp.status_code)
            return []

        reader = csv.DictReader(io.StringIO(resp.text))
        results = []
        for i, row in enumerate(reader):
            if i >= limit:
                break
            org = row.get("Organisation Name", "") or row.get("name", "") or ""
            city = row.get("Town/City", "") or row.get("city", "") or ""
            county = row.get("County", "") or ""
            route = row.get("Route", "") or row.get("route", "") or ""
            if not org:
                continue
            results.append({
                "title": f"{org} — UK Licensed Sponsor",
                "source_url": _GOV_UK_SPONSOR_PAGE,
                "description": f"UK Skilled Worker visa sponsor | City: {city}, {county} | Route: {route}",
                "location": f"{city}, United Kingdom",
                "price": "",
                "metadata": {
                    "type": "uk_sponsor",
                    "organisation": org,
                    "city": city,
                    "county": county,
                    "route": route,
                    "scraped_at": datetime.utcnow().isoformat(),
                }
            })
        logger.info("uk_jobs_client: sponsor list fetched count=%d", len(results))
        return results
    except Exception as exc:
        logger.error("uk_jobs_client: sponsor list error: %s", exc)
        return []


async def _fetch_arbeitnow_uk(
    client: httpx.AsyncClient,
    keywords: str = "",
    results_wanted: int = 30,
) -> List[Dict[str, Any]]:
    """Fetch UK jobs with visa sponsorship from Arbeitnow free API."""
    try:
        resp = await client.get(
            _ARBEITNOW_URL,
            headers={**_HEADERS, "Accept": "application/json"},
            timeout=20
        )
        resp.raise_for_status()
        data = resp.json()
        all_jobs = data.get("data", [])

        # Filter: visa_sponsorship=True + location contains UK/London/England
        uk_keywords = {"uk", "united kingdom", "london", "england", "scotland", "wales"}
        kw_lower = keywords.lower() if keywords else ""

        results = []
        for job in all_jobs:
            loc = (job.get("location", "") or "").lower()
            title = (job.get("title", "") or "").lower()
            remote = job.get("remote", False)
            visa = job.get("visa_sponsorship", False)

            # Include if UK location OR visa_sponsorship flag
            is_uk = any(kw in loc for kw in uk_keywords) or remote
            if not (is_uk or visa):
                continue
            if kw_lower and kw_lower not in title:
                continue

            results.append({
                "title": job.get("title", "Unknown"),
                "source_url": job.get("url", _ARBEITNOW_URL),
                "description": (
                    f"{job.get('company_name', '')} | "
                    f"{job.get('location', 'Remote')} | "
                    f"Visa sponsorship: {'Yes' if visa else 'No'}"
                ),
                "location": job.get("location", "United Kingdom"),
                "price": "",
                "metadata": {
                    "type": "uk_job",
                    "source": "arbeitnow",
                    "company": job.get("company_name", ""),
                    "visa_sponsorship": visa,
                    "remote": remote,
                    "tags": job.get("tags", []),
                    "scraped_at": datetime.utcnow().isoformat(),
                }
            })
            if len(results) >= results_wanted:
                break

        logger.info("uk_jobs_client: arbeitnow fetched count=%d", len(results))
        return results
    except Exception as exc:
        logger.error("uk_jobs_client: arbeitnow error: %s", exc)
        return []


async def fetch_uk_sponsored_jobs(portal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Entry point for crawl_mode='uk_sponsored_jobs'."""
    params = portal_config.get("uk_jobs_params") or {}
    keywords = params.get("keywords", "software engineer")
    results_wanted = int(params.get("results_wanted", 30))
    include_sponsor_list = params.get("include_sponsor_list", True)

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=35) as client:
        results: List[Dict[str, Any]] = []

        # Primary: Arbeitnow UK jobs
        arb_jobs = await _fetch_arbeitnow_uk(client, keywords=keywords, results_wanted=results_wanted)
        results.extend(arb_jobs)

        # Secondary: official sponsor register (if enabled)
        if include_sponsor_list:
            remaining = max(10, results_wanted - len(results))
            sponsor_items = await _fetch_sponsor_list(client, limit=remaining)
            results.extend(sponsor_items)

    logger.info("uk_jobs_client: total fetched=%d", len(results))
    return results[:results_wanted]
