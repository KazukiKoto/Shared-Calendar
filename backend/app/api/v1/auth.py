from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmBody,
    PasswordResetRequestBody,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth_service, email_service
from app.services.auth_service import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidTokenError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    try:
        user = await auth_service.register_user(db, data)
    except EmailAlreadyRegisteredError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    try:
        user = await auth_service.authenticate_user(db, data.email, data.password)
    except InvalidCredentialsError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token, expires_in = security.create_access_token(user.id)
    refresh_token = security.create_refresh_token(user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    data: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> AccessTokenResponse:
    try:
        access_token, expires_in = await auth_service.refresh_access_token(
            db, redis, data.refresh_token
        )
    except InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return AccessTokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.removeprefix("Bearer ")
    try:
        security.decode_token(token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    await auth_service.logout_user(redis, token, ttl)


@router.post("/password-reset/request", response_model=MessageResponse)
async def password_reset_request(
    data: PasswordResetRequestBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> MessageResponse:
    token = await auth_service.request_password_reset(db, redis, data.email)
    if token:
        await email_service.send_password_reset_email(data.email, token)
    return MessageResponse(message="If that email is registered, a reset link has been sent.")


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def password_reset_confirm(
    data: PasswordResetConfirmBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> MessageResponse:
    try:
        await auth_service.confirm_password_reset(db, redis, data.token, data.new_password)
    except InvalidTokenError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    return MessageResponse(message="Password updated successfully.")
