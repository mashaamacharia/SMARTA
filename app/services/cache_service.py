import json
import logging
from collections import OrderedDict
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class SmartJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, OrderedDict):
            return dict(obj)
        return super().default(obj)


class CacheService:
    def __init__(self, redis: Redis | None):
        self.redis = redis

    async def get(self, key: str) -> Any | None:
        if self.redis is None:
            return None
        try:
            data = await self.redis.get(key)
            if data is not None:
                await self.redis.incr("smarta:stats:hits")
                return json.loads(data)
            await self.redis.incr("smarta:stats:misses")
            return None
        except Exception:
            logger.exception("Cache get failed")
            return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        if self.redis is None:
            return
        try:
            await self.redis.setex(key, ttl, json.dumps(value, cls=SmartJSONEncoder))
        except Exception:
            logger.exception("Cache set failed")

    async def delete(self, key: str) -> None:
        if self.redis is None:
            return
        try:
            await self.redis.delete(key)
        except Exception:
            logger.exception("Cache delete failed")

    async def invalidate_pattern(self, pattern: str) -> None:
        if self.redis is None:
            return
        try:
            keys = []
            async for key in self.redis.scan_iter(pattern):
                keys.append(key)
            if keys:
                await self.redis.delete(*keys)
        except Exception:
            logger.exception("Cache pattern invalidation failed")

    async def blacklist_token(self, jti: str, ttl: int) -> None:
        if self.redis is None:
            return
        try:
            await self.redis.setex(
                f"smarta:session:blacklist:{jti}", ttl, "1"
            )
        except Exception:
            logger.exception("Token blacklist failed")

    async def is_token_blacklisted(self, jti: str) -> bool:
        if self.redis is None:
            return False
        try:
            result = await self.redis.exists(f"smarta:session:blacklist:{jti}")
            return result > 0
        except Exception:
            return False
