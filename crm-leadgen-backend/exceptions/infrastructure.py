# Inspired By: browser-use/browser-use, Firecrawl
# Repository: https://github.com/browser-use/browser-use
# Repository: https://github.com/firecrawl/firecrawl
# Feature: Infrastructure-level errors for databases, scraping, network
# Reason: Isolate external system failures from business logic
# ============================================================

from .base import PlatformException


class DatabaseError(PlatformException):
    pass


class RedisError(PlatformException):
    pass


class ElasticsearchError(PlatformException):
    pass


class ScrapingError(PlatformException):
    pass


class BrowserAutomationError(PlatformException):
    pass


class RateLimitExceededError(PlatformException):
    pass


class ExternalServiceError(PlatformException):
    pass


class NetworkError(PlatformException):
    pass


class TimeoutError(PlatformException):
    pass
