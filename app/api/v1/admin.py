from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from app.dependencies import get_redis

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/cache/stats")
async def cache_stats(redis: Redis | None = Depends(get_redis)):
    if redis is None:
        return {"status": "Redis not available"}

    info = await redis.info()
    hits = int(await redis.get("smarta:stats:hits") or 0)
    misses = int(await redis.get("smarta:stats:misses") or 0)
    total = hits + misses
    hit_rate = round((hits / total * 100), 1) if total > 0 else 0.0

    return {
        "redis_memory_used": info.get("used_memory_human", "N/A"),
        "total_keys": info.get("db0", {}).get("keys", 0),
        "hit_rate": f"{hit_rate}%",
        "connected_clients": info.get("connected_clients", 0),
        "uptime_seconds": info.get("uptime_in_seconds", 0),
        "cache_hits": hits,
        "cache_misses": misses,
    }
