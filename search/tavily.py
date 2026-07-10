"""Tavily Search API — Railway-safe, designed for AI agents."""
from __future__ import annotations
import logging
import os
from typing import List
import httpx
from search.base import SearchResult

logger = logging.getLogger(__name__)


async def search(client: httpx.AsyncClient, query: str) -> List[SearchResult]:
    key = os.getenv("TAVILY_API_KEY", "")
    if not key:
        return []
    try:
        r = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": key,
                "query": query,
                "search_depth": "advanced",
                "max_results": 10,
                "include_answer": False,
                "exclude_domains": ["linkedin.com", "glassdoor.com",
                                    "facebook.com", "twitter.com", "x.com"],
            },
            timeout=20)
        if r.status_code != 200:
            logger.debug("tavily %s: %s", r.status_code, r.text[:100])
            return []
        out = []
        for item in r.json().get("results", []):
            url = (item.get("url") or "").strip()
            title = (item.get("title") or "").strip()
            snippet = (item.get("content") or "")[:500]
            if url.startswith("http") and title:
                out.append(SearchResult(title=title, url=url, snippet=snippet,
                                        source="tavily", score=0.75))
        logger.info("tavily: %d results for '%s'", len(out), query[:50])
        return out
    except Exception as exc:
        logger.debug("tavily search failed: %s", exc)
        return []
