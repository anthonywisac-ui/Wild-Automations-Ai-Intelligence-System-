"""
University Data Client — integrates GitHub university scrapers + official APIs.

Sources (from scrapers-info.md):
  - HIPO Labs API          → universities.hipolabs.com (no key, global)
  - College Scorecard API  → collegescorecard.ed.gov  (free key)
  - c3nk/THE-World-University-Rankings → THE backend JSON (direct endpoint)
  - lowweihong/university_ranking_scraper logic → US News / QS / THE rankings

crawl_mode: "university_api"

Usage (set in portal_config):
    {
        "portal_name": "University Rankings",
        "crawl_mode": "university_api",
        "university_params": {
            "source": "hipo" | "scorecard" | "the_rankings" | "all",
            "country": "United Arab Emirates",
            "search": "engineering",
            "limit": 20,
            "scorecard_api_key": "YOUR_KEY",  # or from env COLLEGE_SCORECARD_KEY
        }
    }
"""

import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

_HIPO_URL = "http://universities.hipolabs.com/search"
_SCORECARD_URL = "https://api.data.gov/ed/collegescorecard/v1/schools"
# THE scrapes from Wikipedia ARWU ranking page (always public)
_THE_WIKI_URL = "https://en.wikipedia.org/wiki/Times_Higher_Education_World_University_Rankings"
# Webometrics open ranking (plain HTTP, no JS)
_WEBOMETRICS_URL = "https://www.webometrics.info/en/world?offset=0"

_SCORECARD_KEY = os.getenv("COLLEGE_SCORECARD_KEY", "DEMO_KEY")


# ─────────────────────────────────────────────────────────────────────────────
# HIPO Labs — global university name + domain list
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_hipo(
    client: httpx.AsyncClient,
    country: str = "",
    search: str = "",
    limit: int = 20,
) -> List[Dict[str, Any]]:
    params: Dict[str, str] = {}
    if country:
        params["country"] = country
    if search:
        params["name"] = search

    try:
        resp = await client.get(_HIPO_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for uni in data[:limit]:
            web = (uni.get("web_pages") or [""])[0]
            results.append({
                "title": uni.get("name", "Unknown University"),
                "source_url": web,
                "description": f"University in {uni.get('country', 'Unknown')} — {uni.get('state-province', '')}",
                "location": f"{uni.get('country', '')}, {uni.get('state-province', '')}".strip(", "),
                "price": "",
                "metadata": {
                    "type": "university",
                    "source": "hipo_api",
                    "country": uni.get("country", ""),
                    "domains": uni.get("domains", []),
                    "alpha_two_code": uni.get("alpha_two_code", ""),
                    "scraped_at": datetime.utcnow().isoformat(),
                }
            })
        logger.info("university_client: HIPO fetched count=%d", len(results))
        return results
    except Exception as exc:
        logger.error("university_client: HIPO error: %s", exc)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# College Scorecard API — US universities official data
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_scorecard(
    client: httpx.AsyncClient,
    search: str = "",
    limit: int = 20,
    api_key: str = "",
) -> List[Dict[str, Any]]:
    key = api_key or _SCORECARD_KEY
    params = {
        "api_key": key,
        "fields": "school.name,school.city,school.state,school.school_url,latest.admissions.admission_rate.overall,latest.cost.tuition.in_state,latest.cost.tuition.out_of_state",
        "per_page": min(limit, 100),
    }
    if search:
        params["school.name"] = search

    for attempt in range(2):
        try:
            resp = await client.get(_SCORECARD_URL, params=params, timeout=20)
            if resp.status_code == 429:
                logger.warning("university_client: Scorecard rate-limited (DEMO_KEY), waiting 5s")
                await asyncio.sleep(5)
                continue
            resp.raise_for_status()
            data = resp.json()
            results = []
            for school in (data.get("results") or []):
                name = school.get("school.name", "Unknown")
                city = school.get("school.city", "")
                state = school.get("school.state", "")
                url = school.get("school.school_url", "")
                admit_rate = school.get("latest.admissions.admission_rate.overall")
                tuition_out = school.get("latest.cost.tuition.out_of_state")

                admit_str = f"{round(admit_rate * 100)}% admission" if admit_rate else "N/A"
                tuition_str = f"${tuition_out:,.0f}/yr" if tuition_out else "N/A"

                results.append({
                    "title": name,
                    "source_url": f"https://{url}" if url and not url.startswith("http") else url,
                    "description": f"{city}, {state} | Admission rate: {admit_str} | Out-of-state tuition: {tuition_str}",
                    "location": f"{city}, {state}, USA",
                    "price": str(tuition_out or ""),
                    "metadata": {
                        "type": "university",
                        "source": "college_scorecard",
                        "admission_rate": admit_rate,
                        "tuition_out_of_state": tuition_out,
                        "scraped_at": datetime.utcnow().isoformat(),
                    }
                })
            logger.info("university_client: Scorecard fetched count=%d", len(results))
            return results
        except Exception as exc:
            logger.error("university_client: Scorecard error: %s", exc)
            return []
    return []


def _scorecard_fallback() -> List[Dict[str, Any]]:
    """Static fallback when DEMO_KEY is rate-limited (429) or returns 0 results."""
    now = datetime.utcnow().isoformat()
    data = [
        ("Harvard University",              "Cambridge", "MA", "https://www.harvard.edu",   0.04, 54768),
        ("MIT",                             "Cambridge", "MA", "https://web.mit.edu",       0.07, 55878),
        ("Stanford University",             "Stanford",  "CA", "https://www.stanford.edu",  0.04, 56169),
        ("California Institute of Technology","Pasadena","CA", "https://www.caltech.edu",  0.06, 60864),
        ("Princeton University",            "Princeton", "NJ", "https://www.princeton.edu", 0.06, 57690),
    ]
    results = []
    for name, city, state, url, admit, tuition in data:
        results.append({
            "title": name,
            "source_url": url,
            "description": f"{city}, {state} | Admission rate: {int(admit*100)}% | Tuition: ${tuition:,}/yr (fallback cache)",
            "location": f"{city}, {state}, USA",
            "price": str(tuition),
            "metadata": {
                "type": "university",
                "source": "college_scorecard_fallback",
                "admission_rate": admit,
                "tuition_out_of_state": tuition,
                "scraped_at": now,
            },
        })
    logger.info("university_client: using Scorecard fallback cache (%d items)", len(results))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# THE World University Rankings (c3nk/THE-World-University-Rankings logic)
# Direct JSON endpoint — no browser needed
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_the_rankings(
    client: httpx.AsyncClient,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Fetch THE rankings via Wikipedia (always public, no JS needed)."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; WildAutomations/1.0)", "Accept-Language": "en-US,en;q=0.9"}
        resp = await client.get(_THE_WIKI_URL, headers=headers, timeout=20)
        resp.raise_for_status()
        html = resp.text

        # Extract table rows from Wikipedia ranking table
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
        results = []
        rank = 0
        for row in rows:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL | re.IGNORECASE)
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            cells = [c for c in cells if c]
            if len(cells) >= 2 and any(c.isdigit() for c in cells[0][:3]):
                rank_str = cells[0].strip()
                name = cells[1] if len(cells) > 1 else ""
                country = cells[2] if len(cells) > 2 else ""
                if not name:
                    continue
                rank += 1
                results.append({
                    "title": f"#{rank_str} {name}",
                    "source_url": "https://www.timeshighereducation.com/world-university-rankings",
                    "description": f"THE World University Ranking #{rank_str} | Country: {country}",
                    "location": country,
                    "price": "",
                    "metadata": {
                        "type": "university_ranking",
                        "source": "the_rankings",
                        "rank": rank_str,
                        "scraped_at": datetime.utcnow().isoformat(),
                    }
                })
                if len(results) >= limit:
                    break

        if not results:
            # Fallback: static top 10 THE 2024
            for i, (name, country) in enumerate([
                ("University of Oxford", "UK"), ("Stanford University", "USA"),
                ("MIT", "USA"), ("Harvard University", "USA"),
                ("University of Cambridge", "UK"), ("Princeton University", "USA"),
                ("Caltech", "USA"), ("Imperial College London", "UK"),
                ("UC Berkeley", "USA"), ("Yale University", "USA"),
            ], 1):
                results.append({
                    "title": f"#{i} {name}",
                    "source_url": "https://www.timeshighereducation.com/world-university-rankings",
                    "description": f"THE World Ranking #{i} | Country: {country}",
                    "location": country, "price": "",
                    "metadata": {"type": "university_ranking", "source": "the_rankings_static", "rank": str(i)}
                })

        logger.info("university_client: THE rankings fetched count=%d", len(results))
        return results[:limit]
    except Exception as exc:
        logger.error("university_client: THE rankings error: %s", exc)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_university_data(portal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Main entry point for crawl_mode="university_api".

    portal_config keys:
        university_params:
            source: "hipo" | "scorecard" | "the_rankings" | "all"
            country: "United Arab Emirates"
            search: "engineering"
            limit: 20
            scorecard_api_key: "..."
    """
    params = portal_config.get("university_params") or {}
    source = params.get("source", "hipo")
    country = params.get("country", "")
    # accept both "search" and "keyword" param names
    search = params.get("search") or params.get("keyword", "")
    limit = int(params.get("limit", 20))
    api_key = params.get("scorecard_api_key", "")

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30) as client:
        results = []

        if source in ("hipo", "all"):
            results += await _fetch_hipo(client, country=country, search=search, limit=limit)

        if source in ("scorecard", "all"):
            sc = await _fetch_scorecard(client, search=search, limit=limit, api_key=api_key)
            if not sc:
                sc = _scorecard_fallback()
            results += sc

        if source in ("the_rankings", "all"):
            results += await _fetch_the_rankings(client, limit=limit)

        return results
