import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.dependencies import bearer_scheme, get_current_user, get_db, get_redis
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.register(
        business_name=body.business_name,
        business_email=body.business_email,
        business_phone=body.business_phone,
        business_type=body.business_type,
        owner_full_name=body.owner_full_name,
        owner_email=body.owner_email,
        owner_password=body.owner_password,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.login(email=body.email, password=body.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.refresh(refresh_token=body.refresh_token)


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    redis: Redis | None = Depends(get_redis),
):
    payload = decode_token(credentials.credentials)
    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti and redis is not None:
        ttl = max(int(exp) - int(datetime.now(timezone.utc).timestamp()), 0) if exp else 900
        await redis.setex(f"smarta:session:blacklist:{jti}", ttl, "1")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserOut)
async def me(
    user: User = Depends(get_current_user),
    redis: Redis | None = Depends(get_redis),
):
    cache_key = f"smarta:user:{user.id}:profile"
    if redis is not None:
        cached = await redis.get(cache_key)
        if cached is not None:
            return json.loads(cached)
    data = UserOut.model_validate(user).model_dump()
    if redis is not None:
        await redis.setex(cache_key, 900, json.dumps(data, default=str))
    return data
