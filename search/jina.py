"""Jina Search (s.jina.ai) — Railway-safe, works on datacenter IPs."""
from __future__ import annotations
import logging
import os
from typing import List
from urllib.parse import quote_plus
import httpx
from search.base import SearchResult

logger = logging.getLogger(__name__)


async def search(client: httpx.AsyncClient, query: str) -> List[SearchResult]:
    try:
        headers = {"Accept": "application/json"}
        if key := os.getenv("JINA_API_KEY", ""):
            headers["Authorization"] = f"Bearer {key}"
        r = await client.get(
            f"https://s.jina.ai/{quote_plus(query)}",
            headers=headers, timeout=20)
        if r.status_code != 200:
            return []
        try:
            data = r.json()
            items = data.get("data") or data.get("results") or []
            if items:
                out = []
                for item in items:
                    url = (item.get("url") or "").strip()
                    title = (item.get("title") or "").strip()
                    snippet = (item.get("content") or item.get("description") or "")[:500]
                    if url.startswith("http") and title:
                        out.append(SearchResult(title=title, url=url, snippet=snippet,
                                                source="jina", score=0.7))
                if out:
                    logger.info("jina: %d results for '%s'", len(out), query[:50])
                    return out
        except Exception:
            pass
        # markdown fallback
        import re
        from urllib.parse import unquote
        text = r.content.decode("utf-8", errors="ignore")
        out, blocks = [], re.split(r'\n(?=\[\d+\]|\*\*\[)', text)
        for block in blocks:
            tm = re.search(
                r'\*?\*?\[?([^\]\n]+)\]?\*?\*?\s*\n.*?(?:URL|Source).*?:\s*(https?://[^\s\n]+)',
                block, re.I)
            if not tm:
                tm = re.search(r'(?:Title|##)[:\s]+([^\n]+)\n.*?(https?://[^\s\n]+)', block, re.I)
            if tm:
                title = tm.group(1).strip().strip('*[]')
                url = tm.group(2).strip()
                snip_m = re.search(r'(?:Description|Content|Snippet)[:\s]+([^\n]+)', block, re.I)
                snippet = snip_m.group(1).strip()[:300] if snip_m else ""
                if title and url:
                    out.append(SearchResult(title=title, url=url, snippet=snippet,
                                            source="jina", score=0.7))
        if out:
            logger.info("jina markdown: %d results for '%s'", len(out), query[:50])
        return out
    except Exception as exc:
        logger.debug("jina search failed: %s", exc)
        return []
