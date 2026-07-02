# Inspired By: crawl4AI, browser-use
# Repository: https://github.com/unclecode/crawl4AI
# Repository: https://github.com/browser-use/browser-use
# Feature: Plugin caching utilities
# Reason: Reduce redundant operations with Redis caching
# ============================================================

from typing import Optional, Any, Dict, Callable, Awaitable
import hashlib, json
from functools import wraps

from ..core.redis import get_redis_client
from ..logging import get_logger
from ..exceptions import RedisError

logger = get_logger(__name__)

class PluginCache:
    def __init__(self, prefix: str = "plugin_cache", default_ttl: int = 3600) -> None:
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.redis = get_redis_client()

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    def _hash_key(self, *args, **kwargs) -> str:
        data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        try:
            return await self.redis.get_json(self._key(key))
        except RedisError as e:
            logger.error("Cache get error: %s", e)
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            ttl = ttl or self.default_ttl
            return await self.redis.set_json(self._key(key), value, ex=ttl)
        except RedisError as e:
            logger.error("Cache set error: %s", e)
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self.redis.delete(self._key(key))
            return True
        except RedisError as e:
            logger.error("Cache delete error: %s", e)
            return False

def cached(ttl: Optional[int] = None, prefix: str = "plugin_cache"):
    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = PluginCache(prefix=prefix, default_ttl=ttl or 3600)
            cache_key = cache._hash_key(func.__name__, *args, **kwargs)
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator
