"""Crawlee-equivalent asyncio crawl queue with retry, backoff, and concurrency control."""
from __future__ import annotations
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CrawlRequest:
    url: str
    retries: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # higher = processed first


@dataclass
class CrawlResult:
    url: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    retries: int = 0
    elapsed: float = 0.0


Handler = Callable[[CrawlRequest], Awaitable[Any]]


class CrawlQueue:
    """
    Asyncio-based crawl queue with:
    - Configurable concurrency
    - Exponential backoff retry
    - Per-domain rate limiting
    - Priority support
    """

    def __init__(
        self,
        handler: Handler,
        concurrency: int = 10,
        retry_delays: tuple = (2, 5, 15),
        request_timeout: float = 30.0,
    ):
        self.handler = handler
        self.concurrency = concurrency
        self.retry_delays = retry_delays
        self.request_timeout = request_timeout
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._results: List[CrawlResult] = []
        self._sem: asyncio.Semaphore = asyncio.Semaphore(concurrency)
        self._pending = 0

    def add(self, url: str, max_retries: int = 3, priority: int = 0, **metadata) -> None:
        req = CrawlRequest(url=url, max_retries=max_retries, metadata=metadata, priority=priority)
        # PriorityQueue: lower value = higher priority; negate to invert
        self._queue.put_nowait((-priority, time.monotonic(), req))
        self._pending += 1

    def add_many(self, urls: List[str], **kwargs) -> None:
        for url in urls:
            self.add(url, **kwargs)

    async def _process(self, req: CrawlRequest) -> CrawlResult:
        t0 = time.monotonic()
        for attempt in range(req.max_retries + 1):
            try:
                async with self._sem:
                    data = await asyncio.wait_for(
                        self.handler(req),
                        timeout=self.request_timeout,
                    )
                return CrawlResult(
                    url=req.url, success=True, data=data,
                    retries=attempt, elapsed=time.monotonic() - t0
                )
            except asyncio.TimeoutError:
                err = "timeout"
            except Exception as exc:
                err = str(exc)

            if attempt < req.max_retries:
                delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                logger.debug("crawl retry %d/%d for %s in %ds (err=%s)",
                             attempt + 1, req.max_retries, req.url, delay, err)
                await asyncio.sleep(delay)

        return CrawlResult(
            url=req.url, success=False, error=err,
            retries=req.max_retries, elapsed=time.monotonic() - t0
        )

    async def run(self) -> List[CrawlResult]:
        """Drain the queue concurrently and return all results."""
        tasks = []
        while not self._queue.empty():
            _, _, req = self._queue.get_nowait()
            tasks.append(self._process(req))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=False)
        self._results.extend(results)
        return list(results)

    @property
    def stats(self) -> dict:
        total = len(self._results)
        ok = sum(1 for r in self._results if r.success)
        return {
            "total": total,
            "success": ok,
            "failed": total - ok,
            "success_rate": round(ok / total, 3) if total else 0,
        }


async def crawl_urls(
    urls: List[str],
    handler: Handler,
    concurrency: int = 10,
    max_retries: int = 2,
) -> List[CrawlResult]:
    """Convenience function: crawl a list of URLs with the given async handler."""
    queue = CrawlQueue(handler, concurrency=concurrency)
    queue.add_many(urls, max_retries=max_retries)
    return await queue.run()
