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

    @staticmethod
    def _key(user_id: str, session_id: str) -> str:
        # Scoped to both user_id AND session_id — prevents cross-user leakage
        return f"session:{user_id}:{session_id}"

    async def get_session(self, user_id: str, session_id: str) -> dict:
        if not user_id or not session_id:
            return {}
        try:
            redis = await self._get_redis()
            data = await redis.get(self._key(user_id, session_id))
            return json.loads(data) if data else {}
        except Exception as e:
            log.warning("cache_get_failed", error=str(e))
            return {}

    async def set_session(self, user_id: str, session_id: str, data: dict, ttl: int = 3600):
        if not user_id or not session_id:
            return
        try:
            redis = await self._get_redis()
            await redis.setex(self._key(user_id, session_id), ttl, json.dumps(data))
        except Exception as e:
            log.warning("cache_set_failed", error=str(e))

    async def close(self):
        if self._redis:
            await self._redis.aclose()
