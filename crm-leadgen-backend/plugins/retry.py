# Inspired By: browser-use/browser-use
# Repository: https://github.com/browser-use/browser-use
# Feature: Retry and timeout decorators for plugin methods
# Reason: Resilient plugin execution with fault tolerance
# ============================================================

import asyncio, functools
from typing import Type, Callable, Any, Optional, Tuple, Awaitable
from dataclasses import dataclass
import logging
from ..exceptions import PluginError
from ..utils.retry import RetryConfig

logger = logging.getLogger(__name__)

@dataclass
class PluginRetryConfig(RetryConfig):
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)

def with_retry(config: Optional[PluginRetryConfig] = None):
    def decorator(func: Callable[..., Awaitable[Any]]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cfg = config or PluginRetryConfig()
            last_exception: Optional[Exception] = None
            for attempt in range(cfg.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except cfg.retryable_exceptions as e:
                    last_exception = e
                    wait_time = min(cfg.base_delay * (cfg.backoff_multiplier ** attempt), cfg.max_delay)
                    if cfg.jitter:
                        import random
                        wait_time *= random.uniform(0.8, 1.2)
                    logger.warning("Retry %d/%d for %s after %.2fs: %s", attempt+1, cfg.max_attempts, func.__name__, wait_time, str(e))
                    await asyncio.sleep(wait_time)
            raise PluginError(f"All retries failed for {func.__name__}", cause=last_exception)
        return wrapper
    return decorator

def with_timeout(seconds: int):
    def decorator(func: Callable[..., Awaitable[Any]]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise PluginError(f"Function {func.__name__} timed out after {seconds}s")
        return wrapper
    return decorator
