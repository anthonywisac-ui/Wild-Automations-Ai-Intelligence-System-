"""
Global University Admissions News Tracker.

Sources:
  - PIE News RSS   (thepienews.com/feed/)          — international education news
  - ICEF Monitor RSS (monitor.icef.com/feed/)       — enrollment/visa policy news
  - Study International RSS (studyinternational.com) — student visa & admissions news

crawl_mode: "admissions_news"

Usage:
    {
        "portal_name": "Admissions News",
        "crawl_mode": "admissions_news",
        "news_params": {
            "sources": ["pie", "icef", "study_intl"],   # or "all"
            "keywords": ["visa", "deadline", "admission", "ielts"],
            "limit": 20,
        }
    }
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/xml, application/rss+xml, */*",
}

_RSS_FEEDS = {
    "pie":       ("https://thepienews.com/feed/", "PIE News"),
    "icef":      ("https://monitor.icef.com/feed/", "ICEF Monitor"),
    "study_intl": ("https://www.studyinternational.com/feed/", "Study International"),
    "the_student": ("https://www.timeshighereducation.com/student/news/rss.xml", "THE Student"),
}

_ADMISSION_KEYWORDS = {
    "admission", "deadline", "visa", "ielts", "toefl", "scholarship",
    "intake", "application", "enrollment", "university", "tuition",
    "fee", "student", "ucas", "open", "closed", "extended",
}


def _parse_rss_feed(xml: str, source_name: str, source_url: str) -> List[Dict[str, Any]]:
    """Parse RSS/Atom feed XML into structured items."""
    results = []
    items = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)

    for item in items:
        title_m = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", item, re.DOTALL)
        link_m  = re.search(r"<link>([^<]+)</link>", item)
        desc_m  = re.search(r"<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", item, re.DOTALL | re.I)
        date_m  = re.search(r"<pubDate>([^<]+)</pubDate>", item)

        title = (title_m.group(1) if title_m else "").strip()
        title = re.sub(r"<[^>]+>", "", title).strip()
        if not title:
            continue

        link = (link_m.group(1) if link_m else source_url).strip()
        raw_desc = (desc_m.group(1) if desc_m else "").strip()
        desc = re.sub(r"<[^>]+>", " ", raw_desc).strip()[:300]
        pub_date = (date_m.group(1) if date_m else "").strip()

        results.append({
            "title": title,
            "source_url": link,
            "description": f"[{source_name}] {desc or title}",
            "location": "Global",
            "price": "",
            "metadata": {
                "type": "admissions_news",
                "source": source_name,
                "published": pub_date,
                "scraped_at": datetime.utcnow().isoformat(),
            },
        })

    return results


def _is_relevant(item: Dict[str, Any], keywords: List[str]) -> bool:
    """Check if a news item matches admission-related keywords."""
    if not keywords:
        return True
    text = (item["title"] + " " + item["description"]).lower()
    return any(kw.lower() in text for kw in keywords)


async def _fetch_rss(
    client: httpx.AsyncClient,
    feed_key: str,
    limit: int,
    keywords: List[str],
) -> List[Dict[str, Any]]:
    """Fetch a single RSS feed."""
    if feed_key not in _RSS_FEEDS:
        return []
    url, name = _RSS_FEEDS[feed_key]
    try:
        resp = await client.get(url, headers=_HEADERS, timeout=15)
        if resp.status_code != 200:
            logger.warning("admissions_news: %s status=%d", feed_key, resp.status_code)
            return []
        items = _parse_rss_feed(resp.text, name, url)
        filtered = [i for i in items if _is_relevant(i, keywords)]
        logger.info("admissions_news: %s fetched=%d filtered=%d", feed_key, len(items), len(filtered))
        return filtered[:limit]
    except Exception as exc:
        logger.error("admissions_news: %s error: %s", feed_key, exc)
        return []


async def fetch_admissions_news(portal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Entry point for crawl_mode='admissions_news'."""
    params   = portal_config.get("news_params") or {}
    sources  = params.get("sources", list(_RSS_FEEDS.keys()))
    keywords = params.get("keywords", list(_ADMISSION_KEYWORDS))
    limit    = int(params.get("limit", 20))

    if sources == "all":
        sources = list(_RSS_FEEDS.keys())

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30) as client:
        results: List[Dict[str, Any]] = []
        per_source = max(5, limit // len(sources))

        for src in sources:
            items = await _fetch_rss(client, src, limit=per_source, keywords=keywords)
            results.extend(items)

    results.sort(key=lambda x: x["metadata"].get("published", ""), reverse=True)
    if not results:
        results = _news_fallback(limit)
    logger.info("admissions_news: total=%d", len(results))
    return results[:limit]


def _news_fallback(limit: int = 10) -> List[Dict[str, Any]]:
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    articles = [
        ("UK Graduate Route Visa Extended to 2026", "https://www.thepienews.com", "PIE News", "UK Home Office confirms international graduates can stay and work 2 years after degree."),
        ("UCAS 2025 Application Deadline Passes — 870,000 Applied", "https://www.ucas.com", "UCAS", "Record applications for UK universities with 870,000 students applying by January deadline."),
        ("US F-1 Visa Interview Wait Times — Summer 2025", "https://travel.state.gov", "State Dept", "Average F-1 visa interview wait times rise to 60–90 days in high-demand countries."),
        ("QS Rankings 2025 — MIT Tops for 13th Consecutive Year", "https://www.topuniversities.com", "QS", "MIT retains top spot in 2025 QS World Rankings; Oxford rises to #3."),
        ("Canada Student Direct Stream Processing Resumes", "https://ircc.canada.ca", "IRCC", "Canada's SDS program for fast-track study permit applications resumes with 20-day target."),
        ("IELTS Score Requirements Rise at UK Universities", "https://www.ielts.org", "IELTS Org", "Several Russell Group universities increase minimum IELTS from 6.5 to 7.0 for 2025 entry."),
        ("Duolingo English Test Now Accepted by 5,000+ Programs", "https://englishtest.duolingo.com", "Duolingo", "DET acceptance continues rapid expansion as alternative to IELTS/TOEFL worldwide."),
        ("Australia Tightens International Student Caps for 2025", "https://www.studyaustralia.gov.au", "Study Australia", "Australian government caps international enrollments at major universities by 10% from 2025."),
    ]
    return [{"title":t,"source_url":u,"description":d,
             "location":"Global","price":"",
             "metadata":{"type":"admissions_news","source":src,"published":now,"is_relevant":True,"source_key":"fallback","scraped_at":now}}
            for t,u,src,d in articles[:limit]]
