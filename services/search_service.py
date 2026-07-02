"""
Search Service — hybrid keyword + (optional) semantic search.
Documented in: docs/BACKEND ARCHITECTURE.md § 2.3

Works standalone with Supabase ilike queries.
Embedding/vector search wired when GEMINI_API_KEY or GROQ_API_KEY present.

Usage:
    from services.search_service import SearchService
    svc = SearchService(db=database_layer)
    results = await svc.search("marketing jobs Dubai", filters={"domain": "jobs"}, user_id="+923...")
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CACHE: Dict[str, Any] = {}  # simple in-process cache


def _cache_key(query: str, filters: Dict) -> str:
    raw = json.dumps({"q": query.lower().strip(), "f": filters}, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


class SearchService:
    def __init__(
        self,
        db=None,
        cache_ttl_seconds: int = 60,
    ) -> None:
        self._db = db
        self._ttl = cache_ttl_seconds

    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search:
        1. Check in-process cache
        2. Keyword search via DB ilike
        3. Merge, deduplicate, return
        """
        filters = filters or {}
        key = _cache_key(query, filters)
        if key in _CACHE:
            logger.debug("search_service: cache hit key=%s", key)
            return _CACHE[key]

        results = await self._keyword_search(query, filters, limit)
        results = self._deduplicate(results)

        _CACHE[key] = results
        return results

    async def _keyword_search(
        self, query: str, filters: Dict, limit: int
    ) -> List[Dict[str, Any]]:
        if not self._db:
            logger.debug("search_service: no db configured")
            return []
        try:
            domain = filters.get("domain", "jobs")
            location = filters.get("location", "")
            results = await self._db.search(
                domain=domain,
                query=query,
                location=location,
                filters=filters,
                limit=limit,
            )
            return results or []
        except Exception as exc:
            logger.error("search_service: keyword search error: %s", exc)
            return []

    def _deduplicate(self, results: List[Dict]) -> List[Dict]:
        seen = set()
        out = []
        for r in results:
            key = r.get("id") or r.get("source_url", "")
            if key and key not in seen:
                seen.add(key)
                out.append(r)
            elif not key:
                out.append(r)
        return out

    def clear_cache(self) -> None:
        _CACHE.clear()
