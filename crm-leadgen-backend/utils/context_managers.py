# Inspired By: crawl4AI
# Repository: https://github.com/unclecode/crawl4AI
# Feature: Timing and exception suppression context managers
# Reason: Clean code for performance monitoring and fault tolerance
# ============================================================

import contextlib, logging, time
from typing import Optional, Type, Callable, Any

logger = logging.getLogger(__name__)

@contextlib.contextmanager
def timer(operation_name: str, logger: Optional[logging.Logger] = None):
    log = logger or logging.getLogger(__name__)
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        log.info("Operation '%s' completed in %.3fs", operation_name, elapsed)

@contextlib.contextmanager
def suppress_exceptions(exception_type: Type[Exception] = Exception, fallback: Optional[Callable[[Exception], Any]] = None, log_level: str = "error"):
    try:
        yield
    except exception_type as e:
        if fallback:
            fallback(e)
        else:
            log = logging.getLogger(__name__)
            getattr(log, log_level, log.error)("Suppressed exception: %s", e, exc_info=True)
