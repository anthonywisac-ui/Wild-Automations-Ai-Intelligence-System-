# Inspired By: browser-use/browser-use, TADD (Temporal workflows)
# Repository: https://github.com/browser-use/browser-use
# Feature: Application lifecycle hooks (startup/shutdown)
# Reason: Graceful initialisation and termination
# ============================================================

import asyncio, logging
from typing import List, Callable, Awaitable
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class ApplicationLifecycle:
    def __init__(self) -> None:
        self._startup_tasks: List[Callable[[], Awaitable[None]]] = []
        self._shutdown_tasks: List[Callable[[], Awaitable[None]]] = []

    def on_startup(self, func: Callable[[], Awaitable[None]]) -> Callable[[], Awaitable[None]]:
        self._startup_tasks.append(func)
        return func

    def on_shutdown(self, func: Callable[[], Awaitable[None]]) -> Callable[[], Awaitable[None]]:
        self._shutdown_tasks.append(func)
        return func

    async def startup(self) -> None:
        logger.info("Running %d startup tasks...", len(self._startup_tasks))
        for task in self._startup_tasks:
            await task()
        logger.info("Startup complete.")

    async def shutdown(self) -> None:
        logger.info("Running %d shutdown tasks...", len(self._shutdown_tasks))
        for task in reversed(self._shutdown_tasks):
            try:
                await task()
            except Exception as e:
                logger.exception("Shutdown task failed: %s", e)
        logger.info("Shutdown complete.")

_lifecycle: Optional[ApplicationLifecycle] = None

def lifecycle() -> ApplicationLifecycle:
    global _lifecycle
    if _lifecycle is None:
        _lifecycle = ApplicationLifecycle()
    return _lifecycle

@asynccontextmanager
async def app_context():
    lc = lifecycle()
    await lc.startup()
    try:
        yield
    finally:
        await lc.shutdown()
