from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import settings

# Global client — created lazily, reused across the app
redis_client: Redis | None = None


def get_redis() -> Redis:
    """Return the shared Redis client, creating it if needed."""
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
    return redis_client


async def close_redis() -> None:
    """Close the shared Redis client. Called on app shutdown."""
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None


async def redis_dependency() -> AsyncGenerator[Redis, None]:
    """FastAPI dependency that yields the shared Redis client."""
    yield get_redis()