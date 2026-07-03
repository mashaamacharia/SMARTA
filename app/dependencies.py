import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_redis as get_redis_dep
from app.core.database import get_async_session
from app.core.security import decode_token
from app.models.user import User
from app.services.cache_service import CacheService

bearer_scheme = HTTPBearer()


async def get_db() -> AsyncSession:
    async for session in get_async_session():
        yield session


async def get_redis() -> Redis | None:
    return await get_redis_dep()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis | None = Depends(get_redis),
) -> User:
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    token_type = payload.get("type")
    if not user_id or token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )
    jti = payload.get("jti")
    if jti and redis is not None:
        blacklisted = await redis.exists(f"smarta:session:blacklist:{jti}")
        if blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def get_current_business(user: User = Depends(get_current_user)) -> uuid.UUID:
    return user.business_id


async def get_cache_service(redis: Redis | None = Depends(get_redis)) -> CacheService | None:
    if redis is None:
        return None
    return CacheService(redis)
