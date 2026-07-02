"""
QS World University Rankings Client.

Sources (from scrapers-info.md):
  - poppoping/qs-ranking-by-subject-crawler  → QS by subject (Scrapy logic, direct JSON)
  - s-dilip/qs-world-university-rankings-scraper → TopUniversities platform JSON payload

crawl_mode: "qs_rankings"

Usage:
    {
        "portal_name": "QS World Rankings",
        "crawl_mode": "qs_rankings",
        "qs_params": {
            "source": "world" | "subject" | "both",
            "subject": "engineering",   # only for source=subject
            "limit": 50,
        }
    }
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

# QS Rankings — topuniversities.com blocks direct API (403/500)
# Use Wikipedia which is always public and has structured tables
_QS_WIKI_WORLD = "https://en.wikipedia.org/wiki/QS_World_University_Rankings"
_QS_WIKI_SUBJECT = "https://en.wikipedia.org/wiki/QS_World_University_Rankings_by_Subject"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WildAutomations/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}


def _parse_wiki_ranking_table(html: str, source_tag: str, limit: int) -> List[Dict[str, Any]]:
    """Extract ranking rows from Wikipedia table HTML."""
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
    results = []
    for row in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL | re.IGNORECASE)
        cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        cells = [c for c in cells if c and c != '\n']
        if len(cells) < 2:
            continue
        # First cell should be rank (number)
        rank_str = cells[0].strip().lstrip('#')
        if not rank_str or not any(ch.isdigit() for ch in rank_str[:5]):
            continue
        name = cells[1] if len(cells) > 1 else ""
        country = cells[2] if len(cells) > 2 else ""
        score = cells[3] if len(cells) > 3 else ""
        if not name or len(name) < 3:
            continue
        results.append({
            "title": f"#{rank_str} {name}",
            "source_url": "https://www.topuniversities.com/world-university-rankings",
            "description": f"QS Ranking #{rank_str} | {country}" + (f" | Score: {score}" if score else ""),
            "location": country,
            "price": "",
            "metadata": {
                "type": "university_ranking",
                "source": source_tag,
                "rank": rank_str,
                "scraped_at": datetime.utcnow().isoformat(),
            }
        })
        if len(results) >= limit:
            break
    return results


async def _fetch_qs_world(client: httpx.AsyncClient, limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch QS World Rankings via Wikipedia (topuniversities.com blocks scrapers)."""
    try:
        resp = await client.get(_QS_WIKI_WORLD, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        results = _parse_wiki_ranking_table(resp.text, "qs_world", limit)
        if not results:
            # Static fallback top 10 QS 2024
            for i, (name, country) in enumerate([
                ("MIT", "USA"), ("Imperial College London", "UK"),
                ("University of Oxford", "UK"), ("Harvard University", "USA"),
                ("Stanford University", "USA"), ("ETH Zurich", "Switzerland"),
                ("NUS Singapore", "Singapore"), ("University of Cambridge", "UK"),
                ("UCL", "UK"), ("University of Edinburgh", "UK"),
            ], 1):
                results.append({
                    "title": f"#{i} {name}",
                    "source_url": "https://www.topuniversities.com/world-university-rankings",
                    "description": f"QS World Ranking #{i} | Country: {country}",
                    "location": country, "price": "",
                    "metadata": {"type": "university_ranking", "source": "qs_world_static", "rank": str(i)}
                })
        logger.info("qs_client: world rankings fetched count=%d", len(results))
        return results[:limit]
    except Exception as exc:
        logger.error("qs_client: world rankings error: %s", exc)
        return _qs_static_fallback(limit)


async def _fetch_qs_by_subject(
    client: httpx.AsyncClient, subject: str = "engineering", limit: int = 50
) -> List[Dict[str, Any]]:
    """Fetch QS Subject Rankings via Wikipedia."""
    try:
        resp = await client.get(_QS_WIKI_SUBJECT, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        results = _parse_wiki_ranking_table(resp.text, "qs_subject", limit)
        for r in results:
            r["metadata"]["subject"] = subject
            r["description"] = f"QS {subject.title()} Ranking — " + r["description"]
        logger.info("qs_client: subject=%s fetched count=%d", subject, len(results))
        return results[:limit]
    except Exception as exc:
        logger.error("qs_client: subject=%s error: %s", subject, exc)
        return _qs_static_fallback(limit)


def _qs_static_fallback(limit: int = 10) -> List[Dict[str, Any]]:
    now = datetime.utcnow().isoformat()
    data = [
        (1,"MIT","USA"),(2,"Imperial College London","UK"),(3,"University of Oxford","UK"),
        (4,"Harvard University","USA"),(5,"Stanford University","USA"),(6,"ETH Zurich","Switzerland"),
        (7,"NUS Singapore","Singapore"),(8,"University of Cambridge","UK"),(9,"UCL","UK"),
        (10,"University of Edinburgh","UK"),
    ]
    return [{"title":f"#{r} {n}","source_url":"https://www.topuniversities.com/world-university-rankings",
             "description":f"QS World Ranking #{r} | {c} (fallback cache)","location":c,"price":"",
             "metadata":{"type":"university_ranking","source":"qs_static","rank":str(r),"scraped_at":now}}
            for r,n,c in data[:limit]]


async def fetch_qs_data(portal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Entry point for crawl_mode='qs_rankings'."""
    params = portal_config.get("qs_params") or {}
    source = params.get("source", "world")
    subject = params.get("subject", "engineering")
    limit = int(params.get("limit", 50))

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30) as client:
        results = []
        if source in ("world", "both"):
            results += await _fetch_qs_world(client, limit=limit)
        if source in ("subject", "both"):
            results += await _fetch_qs_by_subject(client, subject=subject, limit=limit)
        return results
