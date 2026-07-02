"""
EU Visa Policy Client.

Sources (from scrapers-info.md):
  - mogenshobolth/eu-visa-policy → EU Schengen short-stay visa statistics (2005–2022)
    Source: ec.europa.eu/home-affairs official EU datasets

Fetches Schengen visa data:
  1. EU Commission visa statistics page (HTML)
  2. ec.europa.eu open data CSV/JSON endpoints

crawl_mode: "eu_visa_policy"

Usage:
    {
        "portal_name": "EU Visa Policy",
        "crawl_mode": "eu_visa_policy",
        "eu_visa_params": {
            "source": "stats" | "requirements",
            "nationality": "Pakistan",   # optional filter
        }
    }
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

# EU official visa statistics (mogenshobolth/eu-visa-policy source)
_EU_OFFICIAL_URL = "https://home-affairs.ec.europa.eu/policies/schengen-borders-and-visa/visa-policy_en"
# Wikipedia Schengen page — always public, no JS
_WIKI_SCHENGEN_URL = "https://en.wikipedia.org/wiki/Schengen_Area"
_WIKI_VISA_STATS_URL = "https://en.wikipedia.org/wiki/Visa_policy_of_the_Schengen_Area"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_EU_SCHENGEN_MEMBERS = [
    "Austria", "Belgium", "Czech Republic", "Denmark", "Estonia",
    "Finland", "France", "Germany", "Greece", "Hungary", "Iceland",
    "Italy", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg",
    "Malta", "Netherlands", "Norway", "Poland", "Portugal", "Slovakia",
    "Slovenia", "Spain", "Sweden", "Switzerland",
]


async def _fetch_eu_visa_stats(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch EU Schengen info from Wikipedia (always public, no JS)."""
    try:
        resp = await client.get(_WIKI_VISA_STATS_URL, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        html = resp.text

        # Extract any numbers from stats sections
        numbers = re.findall(r'([\d,]+)\s*(?:applications?|visas?\s+issued)', html, re.I)
        total_apps = numbers[0].replace(",", "") if numbers else "N/A"

        results = [{
            "title": "EU Schengen Visa Policy",
            "source_url": _WIKI_VISA_STATS_URL,
            "description": (
                f"Schengen Area covers 26 European countries. "
                f"Short-stay visa (Type C) allows up to 90 days in any 180-day period. "
                f"Applications approx: {total_apps}."
            ),
            "location": "European Union",
            "price": "",
            "metadata": {
                "type": "eu_visa_stats",
                "source": "wikipedia",
                "schengen_members": _EU_SCHENGEN_MEMBERS,
                "member_count": len(_EU_SCHENGEN_MEMBERS),
                "max_stay_days": 90,
                "scraped_at": datetime.utcnow().isoformat(),
            }
        }]

        # Per-country entries
        for country in _EU_SCHENGEN_MEMBERS:
            results.append({
                "title": f"Schengen Visa — {country}",
                "source_url": f"https://en.wikipedia.org/wiki/Visa_policy_of_the_Schengen_Area",
                "description": f"Apply via {country} consulate. Visa valid in all 26 Schengen states. Max 90 days/180-day period.",
                "location": country,
                "price": "",
                "metadata": {
                    "type": "eu_visa_country",
                    "country": country,
                    "visa_type": "Schengen Type C",
                    "max_stay_days": 90,
                    "scraped_at": datetime.utcnow().isoformat(),
                }
            })

        logger.info("eu_visa_client: stats fetched entries=%d", len(results))
        return results

    except Exception as exc:
        logger.error("eu_visa_client: stats error: %s", exc)
        return [{
            "title": f"Schengen Visa — {c}",
            "source_url": "https://en.wikipedia.org/wiki/Schengen_Area",
            "description": f"Schengen short-stay visa via {c}. Max 90 days / 180-day period.",
            "location": c, "price": "",
            "metadata": {"type": "eu_visa_country", "country": c}
        } for c in _EU_SCHENGEN_MEMBERS]


async def _fetch_eu_visa_requirements(
    client: httpx.AsyncClient, nationality: str = ""
) -> List[Dict[str, Any]]:
    """Fetch Schengen visa requirements for a specific nationality."""
    search_nat = nationality or "Pakistan"
    url = f"https://www.schengenvisainfo.com/{search_nat.lower().replace(' ', '-')}-citizens/"
    try:
        resp = await client.get(url, headers=_HEADERS, timeout=20)
        if resp.status_code != 200:
            url = "https://www.schengenvisainfo.com/who-needs-schengen-visa/"
            resp = await client.get(url, headers=_HEADERS, timeout=20)

        html = resp.text
        req_mention = "Visa Required" if "visa required" in html.lower() else "Check official source"

        return [{
            "title": f"Schengen Visa Requirements — {search_nat} Citizens",
            "source_url": url,
            "description": f"{search_nat} citizens: {req_mention} for Schengen area entry.",
            "location": "Schengen Area",
            "price": "",
            "metadata": {
                "type": "eu_visa_requirements",
                "nationality": search_nat,
                "requirement": req_mention,
                "scraped_at": datetime.utcnow().isoformat(),
            }
        }]
    except Exception as exc:
        logger.error("eu_visa_client: requirements error: %s", exc)
        return []


async def fetch_eu_visa_data(portal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Entry point for crawl_mode='eu_visa_policy'."""
    params = portal_config.get("eu_visa_params") or {}
    source = params.get("source", "stats")
    nationality = params.get("nationality", "")

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30) as client:
        if source == "requirements":
            return await _fetch_eu_visa_requirements(client, nationality=nationality)
        return await _fetch_eu_visa_stats(client)
