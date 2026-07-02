# Inspired By: browser-use/browser-use
# Repository: https://github.com/browser-use/browser-use
# Feature: Async and sync retry with exponential backoff and jitter
# Reason: Production-grade resilience for external calls
# ============================================================

import asyncio, time, random, logging
from typing import Type, Callable, Any, Optional, Tuple, TypeVar, Awaitable
from dataclasses import dataclass

T = TypeVar("T")
logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    jitter: bool = True


async def async_retry(func: Callable[..., Awaitable[T]], *args, config: Optional[RetryConfig] = None, **kwargs) -> T:
    config = config or RetryConfig()
    last_exception: Optional[Exception] = None
    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e
            wait_time = min(config.base_delay * (config.backoff_multiplier ** attempt), config.max_delay)
            if config.jitter:
                wait_time *= random.uniform(0.8, 1.2)
            logger.warning("Retry %d/%d for %s after %.2fs: %s", attempt+1, config.max_attempts, func.__name__, wait_time, str(e))
            await asyncio.sleep(wait_time)
    raise last_exception


def sync_retry(func: Callable[..., T], *args, config: Optional[RetryConfig] = None, **kwargs) -> T:
    config = config or RetryConfig()
    last_exception: Optional[Exception] = None
    for attempt in range(config.max_attempts):
        try:
            return func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e
            wait_time = min(config.base_delay * (config.backoff_multiplier ** attempt), config.max_delay)
            if config.jitter:
                wait_time *= random.uniform(0.8, 1.2)
            logger.warning("Retry %d/%d for %s after %.2fs: %s", attempt+1, config.max_attempts, func.__name__, wait_time, str(e))
            time.sleep(wait_time)
    raise last_exception
