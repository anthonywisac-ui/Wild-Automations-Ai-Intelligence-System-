"""
Proxy Pool — free rotating HTTP proxies (GitHub lists) with liveness validation.

Free proxies are mostly dead/slow/short-lived, so this NEVER trusts a list blindly:
it fetches candidates from public GitHub proxy lists, validates each by actually
reaching Google through it (HTTP, no TLS/credentials), and keeps only the live
ones. The scrapers rotate through these to dodge Google's per-IP CAPTCHA wall.

Only non-sensitive Google SERP traffic is routed through them — never LinkedIn
cookies, never any credential. Dead proxies are dropped on use.

    await refresh()          # fetch + validate, cache working ones
    await get_working()      # a live proxy 'http://ip:port' (refreshes if needed)
    mark_bad(proxy)          # drop a proxy that failed at scrape time
    stats()
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from pathlib import Path
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_CACHE = Path(__file__).resolve().parent.parent / "data" / "proxies.json"

# public GitHub proxy lists (HTTP proxies, ip:port per line)
_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
]
_TEST_URL = "http://www.google.com/generate_204"   # HTTP → 204, no TLS needed
_TEST_TIMEOUT = 6.0
_VALIDATE_CAP = 500          # max candidates to test per refresh
_TARGET_LIVE = 25            # stop validating once we have this many
_STALE_SECONDS = 1800        # re-validate the cache after 30 min

_working: List[str] = []
_last_refresh = 0.0
_lock = asyncio.Lock()


def _parse(text: str) -> List[str]:
    out = []
    for line in text.splitlines():
        line = line.strip().split()[0] if line.strip() else ""
        if line.count(":") == 1 and line.replace(":", "").replace(".", "").isdigit():
            out.append(line)
    return out


async def _fetch_candidates() -> List[str]:
    cands: List[str] = []
    async with httpx.AsyncClient(timeout=15, verify=False) as client:
        for url in _SOURCES:
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    cands.extend(_parse(r.text))
            except Exception as exc:
                logger.info("proxy_pool: source failed %s (%s)", url, exc)
    random.shuffle(cands)
    # dedupe preserving order
    seen, uniq = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c); uniq.append(c)
    return uniq[:_VALIDATE_CAP]


async def _validate_one(proxy: str, sem: asyncio.Semaphore) -> Optional[str]:
    async with sem:
        url = f"http://{proxy}"
        try:
            # httpx >=0.28 uses proxy= (singular); older uses proxies=
            try:
                client = httpx.AsyncClient(proxy=url, timeout=_TEST_TIMEOUT, verify=False)
            except TypeError:
                client = httpx.AsyncClient(proxies=url, timeout=_TEST_TIMEOUT, verify=False)
            async with client:
                r = await client.get(_TEST_URL)
                if r.status_code in (204, 200):
                    return proxy
        except Exception:
            return None
    return None


async def refresh() -> int:
    """Fetch candidates and validate them concurrently; cache the live ones."""
    global _working, _last_refresh
    async with _lock:
        cands = await _fetch_candidates()
        if not cands:
            logger.warning("proxy_pool: no candidates fetched")
            return len(_working)
        logger.info("proxy_pool: validating %d candidates…", len(cands))
        sem = asyncio.Semaphore(60)
        live: List[str] = []
        tasks = [asyncio.create_task(_validate_one(p, sem)) for p in cands]
        for fut in asyncio.as_completed(tasks):
            res = await fut
            if res:
                live.append(res)
                if len(live) >= _TARGET_LIVE:
                    break
        for t in tasks:
            t.cancel()
        _working = live
        _last_refresh = time.time()
        try:
            _CACHE.write_text(json.dumps({"working": live, "ts": _last_refresh},
                                         ensure_ascii=False))
        except Exception:
            pass
        logger.info("proxy_pool: %d live proxies", len(live))
        return len(live)


def _load_cache() -> None:
    global _working, _last_refresh
    if _working:
        return
    try:
        d = json.loads(_CACHE.read_text(encoding="utf-8"))
        _working = list(d.get("working") or [])
        _last_refresh = float(d.get("ts") or 0)
    except Exception:
        pass


async def get_working() -> Optional[str]:
    """Return a live proxy 'http://ip:port', refreshing the pool if empty/stale."""
    _load_cache()
    if not _working or (time.time() - _last_refresh) > _STALE_SECONDS:
        await refresh()
    if not _working:
        return None
    return "http://" + random.choice(_working)


def mark_bad(proxy: Optional[str]) -> None:
    if not proxy:
        return
    p = proxy.replace("http://", "").replace("https://", "")
    try:
        _working.remove(p)
    except ValueError:
        pass


def stats() -> Dict:
    _load_cache()
    age = int(time.time() - _last_refresh) if _last_refresh else None
    return {"live_proxies": len(_working), "last_refresh_age_s": age}
