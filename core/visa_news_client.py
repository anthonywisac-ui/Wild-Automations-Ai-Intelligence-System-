"""
Visa & Immigration News — latest policy changes, rule updates, announcements.

Sources (all fail-soft, keyword-filtered):
  - gov.uk UK Visas & Immigration (Atom)   — official UK policy announcements
  - gov.uk Home Office (Atom)              — UK immigration rule changes
  - PIE News RSS                           — international education/visa news
  - ICEF Monitor RSS                       — visa policy + enrollment news

crawl_mode: "visa_news"

Usage:
    {
        "portal_name": "Visa News", "crawl_mode": "visa_news",
        "news_params": {"sources": ["ukvi", "home_office", "pie", "icef"],
                        "limit": 20}
    }
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Dict, List

import httpx

from core import freshness

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/atom+xml, application/rss+xml, text/xml, */*",
}

_FEEDS = {
    "ukvi": ("https://www.gov.uk/government/organisations/uk-visas-and-immigration.atom",
             "UK Visas & Immigration", "UK"),
    "home_office": ("https://www.gov.uk/government/organisations/home-office.atom",
                    "Home Office", "UK"),
    "pie": ("https://thepienews.com/feed/", "PIE News", "Global"),
    "icef": ("https://monitor.icef.com/feed/", "ICEF Monitor", "Global"),
}

_VISA_KEYWORDS = {
    "visa", "immigration", "sponsor", "sponsorship", "skilled worker",
    "student route", "graduate route", "work permit", "permit", "asylum",
    "settlement", "citizenship", "border", "biometric", "salary threshold",
    "points-based", "dependant", "dependent", "ilr", "study permit",
    "express entry", "green card", "h-1b", "schengen", "residence",
}


def _parse_feed(xml: str, source_name: str, country: str,
                feed_url: str) -> List[Dict[str, Any]]:
    """Parse RSS <item> or Atom <entry> blocks into structured news records."""
    blocks = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL) or \
             re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL)
    results = []
    for block in blocks:
        title_m = re.search(r"<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>",
                            block, re.DOTALL)
        title = re.sub(r"<[^>]+>", "", (title_m.group(1) if title_m else "")).strip()
        if not title:
            continue
        # RSS <link>url</link> vs Atom <link href="url"/>
        link_m = re.search(r'<link[^>]*href="([^"]+)"', block) or \
                 re.search(r"<link>([^<]+)</link>", block)
        link = (link_m.group(1) if link_m else feed_url).strip()
        desc_m = re.search(
            r"<(?:description|summary|content)[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?"
            r"</(?:description|summary|content)>", block, re.DOTALL | re.I)
        desc = re.sub(r"<[^>]+>", " ", (desc_m.group(1) if desc_m else "")).strip()[:300]
        date_m = re.search(r"<(?:pubDate|published|updated)>([^<]+)<", block)
        raw_date = (date_m.group(1) if date_m else "").strip()
        posted_iso = freshness.parse(raw_date)

        results.append({
            "title": title,
            "source_url": link,
            "description": f"[{source_name}] {desc or title}",
            "location": country,
            "price": "",
            "metadata": {
                "type": "visa_news",
                "source": source_name,
                "country": country,
                "published": raw_date,
                "posted_iso": posted_iso,
                "posted_ago": freshness.ago(posted_iso),
                "fresh": freshness.is_fresh(posted_iso, hours=72),
                "scraped_at": datetime.utcnow().isoformat(),
            },
        })
    return results


def _is_visa_related(item: Dict[str, Any]) -> bool:
    text = (item["title"] + " " + item["description"]).lower()
    return any(kw in text for kw in _VISA_KEYWORDS)


async def _fetch_one(client: httpx.AsyncClient, key: str) -> List[Dict[str, Any]]:
    url, name, country = _FEEDS[key]
    try:
        resp = await client.get(url, timeout=20, headers=_HEADERS)
        resp.raise_for_status()
        items = _parse_feed(resp.text, name, country, url)
        # official UK feeds carry mixed Home Office news — keyword-filter all
        items = [i for i in items if _is_visa_related(i)]
        logger.info("visa_news: %s -> %d visa-related items", key, len(items))
        return items
    except Exception as exc:
        logger.warning("visa_news: %s failed: %s", key, exc)
        return []


def _static_fallback() -> List[Dict[str, Any]]:
    now = datetime.utcnow().isoformat()
    return [{
        "title": "Visa news temporarily unavailable — check official sources",
        "source_url": "https://www.gov.uk/government/organisations/uk-visas-and-immigration",
        "description": "Live feeds unreachable. Official sources: gov.uk (UK), "
                       "canada.ca/immigration (Canada), travel.state.gov (US).",
        "location": "Global", "price": "",
        "metadata": {"type": "visa_news", "source": "fallback", "scraped_at": now},
    }]


async def fetch_visa_news(portal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Entry point for crawl_mode='visa_news'."""
    params = portal_config.get("news_params") or {}
    sources = params.get("sources") or list(_FEEDS)
    if sources == "all":
        sources = list(_FEEDS)
    limit = int(params.get("limit", 20))

    async with httpx.AsyncClient(verify=False, follow_redirects=True,
                                 timeout=30) as client:
        lists = await asyncio.gather(
            *[_fetch_one(client, k) for k in sources if k in _FEEDS])
    items = [i for lst in lists for i in lst]
    if not items:
        return _static_fallback()
    # newest first — the whole point is "latest policies"
    items.sort(key=lambda i: i["metadata"].get("posted_iso") or "", reverse=True)
    return items[:limit]
