# Inspired By: Redis client patterns in crawl4AI
# Repository: https://github.com/unclecode/crawl4AI
# Feature: Async Redis client with connection pooling
# Reason: Caching, rate limiting, session storage
# ============================================================

from typing import Optional, Any, Dict
import json, logging
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError as RedisException

from ..config import get_settings
from ..exceptions import RedisError

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.url = settings.redis.url
        self.max_connections = settings.redis.max_connections
        self.retry_on_timeout = settings.redis.retry_on_timeout
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None

    async def initialize(self) -> None:
        try:
            self._pool = ConnectionPool.from_url(self.url, max_connections=self.max_connections, retry_on_timeout=self.retry_on_timeout, decode_responses=True)
            self._client = Redis(connection_pool=self._pool)
            await self._client.ping()
            logger.info("Redis client initialized")
        except Exception as e:
            raise RedisError(f"Redis initialization failed: {e}", cause=e)

    async def shutdown(self) -> None:
        if self._client:
            await self._client.close()
            await self._pool.disconnect()
            logger.info("Redis client closed")

    async def get(self, key: str) -> Optional[str]:
        try:
            return await self._client.get(key)
        except RedisException as e:
            raise RedisError(f"Redis GET failed: {e}", cause=e)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        try:
            return await self._client.set(key, value, ex=ex)
        except RedisException as e:
            raise RedisError(f"Redis SET failed: {e}", cause=e)

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        value = await self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise RedisError(f"Invalid JSON in Redis: {e}", cause=e)

    async def set_json(self, key: str, value: Dict[str, Any], ex: Optional[int] = None) -> bool:
        try:
            encoded = json.dumps(value, default=str)
            return await self.set(key, encoded, ex=ex)
        except TypeError as e:
            raise RedisError(f"JSON serialization failed: {e}", cause=e)

    async def delete(self, key: str) -> int:
        try:
            return await self._client.delete(key)
        except RedisException as e:
            raise RedisError(f"Redis DELETE failed: {e}", cause=e)

    async def exists(self, key: str) -> bool:
        try:
            return await self._client.exists(key) > 0
        except RedisException as e:
            raise RedisError(f"Redis EXISTS failed: {e}", cause=e)

    async def incr(self, key: str) -> int:
        try:
            return await self._client.incr(key)
        except RedisException as e:
            raise RedisError(f"Redis INCR failed: {e}", cause=e)

_redis_client: Optional[RedisClient] = None

def get_redis_client() -> RedisClient:
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client
