"""
Universal Apify API client.

One API key runs any actor from config/apify_actors.py.
Set APIFY_API_KEY in .env — that's it.

Flow:
  run_actor(actor_id, input) → start run → poll until done → return results
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

APIFY_BASE = "https://api.apify.com/v2"
_POLL_INTERVAL = 5   # seconds between status checks
_DEFAULT_TIMEOUT = 300  # 5 minutes max per run


class ApifyClient:
    def __init__(self, api_key: str):
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def run_actor(
        self,
        actor_id: str,
        input_data: Dict[str, Any],
        max_results: int = 5,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> List[Dict[str, Any]]:
        """
        Run an Apify actor synchronously (start → wait → fetch results).
        Returns up to max_results items.
        """
        logger.info("apify:start actor=%s max_results=%d", actor_id, max_results)
        run_id = await self._start_run(actor_id, input_data)
        await self._wait_for_run(run_id, timeout=timeout)
        items = await self._fetch_dataset(run_id, limit=max_results)
        logger.info("apify:done actor=%s run_id=%s items=%d", actor_id, run_id, len(items))
        return items

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _start_run(self, actor_id: str, input_data: Dict[str, Any]) -> str:
        # username/actor-name format → username~actor-name
        # Raw hash IDs (e.g. Ibt7KM0rfn2XBfzEi) are used as-is
        encoded = actor_id.replace("/", "~")
        url = f"{APIFY_BASE}/acts/{encoded}/runs"
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, verify=False) as client:
            resp = await client.post(url, json=input_data, headers=self._headers)
            resp.raise_for_status()
            run_id = resp.json()["data"]["id"]
            logger.debug("apify:run_started run_id=%s", run_id)
            return run_id

    async def _wait_for_run(self, run_id: str, timeout: int) -> None:
        url = f"{APIFY_BASE}/actor-runs/{run_id}"
        deadline = asyncio.get_event_loop().time() + timeout
        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            while True:
                if asyncio.get_event_loop().time() > deadline:
                    raise TimeoutError(f"Apify run {run_id} timed out after {timeout}s")
                resp = await client.get(url, headers=self._headers)
                resp.raise_for_status()
                status = resp.json()["data"]["status"]
                logger.debug("apify:poll run_id=%s status=%s", run_id, status)
                if status == "SUCCEEDED":
                    return
                if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    raise RuntimeError(f"Apify run {run_id} ended with status={status}")
                await asyncio.sleep(_POLL_INTERVAL)

    async def _fetch_dataset(self, run_id: str, limit: int) -> List[Dict[str, Any]]:
        url = f"{APIFY_BASE}/actor-runs/{run_id}/dataset/items"
        params = {"limit": limit, "format": "json"}
        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            resp = await client.get(url, params=params, headers=self._headers)
            resp.raise_for_status()
            return resp.json()
