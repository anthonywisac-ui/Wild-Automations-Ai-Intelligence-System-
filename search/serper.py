"""Serper.dev — Google Search API. Railway-safe. $0.001/query, 2500 free."""
from __future__ import annotations
import logging
import os
from typing import List
import httpx
from search.base import SearchResult

logger = logging.getLogger(__name__)


async def search(client: httpx.AsyncClient, query: str, num: int = 10) -> List[SearchResult]:
    key = os.getenv("SERPER_API_KEY", "")
    if not key:
        return []
    try:
        r = await client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            json={"q": query, "num": num, "gl": "us", "hl": "en"},
            timeout=15)
        if r.status_code != 200:
            return []
        out = []
        for item in r.json().get("organic", []):
            url = (item.get("link") or "").strip()
            title = (item.get("title") or "").strip()
            snippet = (item.get("snippet") or "")[:500]
            if url.startswith("http") and title:
                out.append(SearchResult(title=title, url=url, snippet=snippet,
                                        source="serper", score=0.8))
        logger.info("serper: %d results for '%s'", len(out), query[:50])
        return out
    except Exception as exc:
        logger.debug("serper search failed: %s", exc)
        return []
