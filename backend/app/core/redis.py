import redis.asyncio as aioredis

from app.core.config import settings


def get_redis() -> aioredis.Redis:
    return aioredis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
