from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

pool: ConnectionPool | None = None


async def init_redis():
    global pool
    pool = ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=20,
        decode_responses=True,
    )


async def get_redis() -> Redis | None:
    if pool is None:
        return None
    try:
        return Redis(connection_pool=pool)
    except Exception:
        return None


async def close_redis():
    global pool
    if pool is not None:
        await pool.disconnect()
        pool = None
