import json
import structlog
from app.config import settings

log = structlog.get_logger()


class CacheService:
    def __init__(self):
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(settings.redis_url)
        return self._redis

    async def get_session(self, session_id: str) -> dict:
        try:
            redis = await self._get_redis()
            data = await redis.get(f"session:{session_id}")
            return json.loads(data) if data else {}
        except Exception as e:
            log.warning("cache_get_failed", error=str(e))
            return {}

    async def set_session(self, session_id: str, data: dict, ttl: int = 3600):
        try:
            redis = await self._get_redis()
            await redis.setex(f"session:{session_id}", ttl, json.dumps(data))
        except Exception as e:
            log.warning("cache_set_failed", error=str(e))

    async def close(self):
        if self._redis:
            await self._redis.aclose()
