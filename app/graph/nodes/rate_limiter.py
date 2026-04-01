import time
import structlog
from app.config import settings

log = structlog.get_logger()


async def rate_limiter_node(state):
    user_id = state["user_id"]

    try:
        import redis.asyncio as aioredis
        redis = aioredis.from_url(settings.redis_url)

        key = f"rate:{user_id}"
        now = int(time.time())
        window_start = now - 60

        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, 60)
        results = await pipe.execute()

        request_count = results[2]
        await redis.aclose()

        if request_count > settings.rate_limit_per_minute:
            log.warning("rate_limit_exceeded", user_id=user_id, count=request_count)
            return {**state, "is_rate_limited": True, "response": "Please slow down. Take a breath. 🌿"}

    except Exception as e:
        log.warning("rate_limiter_redis_unavailable", error=str(e))

    return {**state, "is_rate_limited": False}
