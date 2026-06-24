import secrets
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.models.user import User
from app.schemas.auth import RegisterRequest


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    existing = await db.scalar(select(User).where(User.email == data.email))
    if existing:
        raise EmailAlreadyRegisteredError
    user = User(
        name=data.name,
        email=data.email,
        hashed_password=security.hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not security.verify_password(password, user.hashed_password):
        raise InvalidCredentialsError
    return user


async def refresh_access_token(
    db: AsyncSession, redis: aioredis.Redis, refresh_token: str
) -> tuple[str, int]:
    try:
        payload = security.decode_token(refresh_token)
    except JWTError as exc:
        raise InvalidTokenError from exc

    if payload.get("type") != "refresh":
        raise InvalidTokenError

    if await security.is_token_revoked(redis, refresh_token):
        raise InvalidTokenError

    user_id = uuid.UUID(payload["sub"])
    if not await db.get(User, user_id):
        raise InvalidTokenError

    return security.create_access_token(user_id)


async def logout_user(redis: aioredis.Redis, access_token: str, ttl: int) -> None:
    await security.revoke_token(redis, access_token, ttl)


async def request_password_reset(db: AsyncSession, redis: aioredis.Redis, email: str) -> str | None:
    user = await db.scalar(select(User).where(User.email == email))
    if not user:
        return None
    token = secrets.token_urlsafe(32)
    await security.store_reset_token(redis, token, user.id)
    return token


async def confirm_password_reset(
    db: AsyncSession, redis: aioredis.Redis, token: str, new_password: str
) -> None:
    user_id = await security.consume_reset_token(redis, token)
    if not user_id:
        raise InvalidTokenError
    user = await db.get(User, user_id)
    if not user:
        raise InvalidTokenError
    user.hashed_password = security.hash_password(new_password)
    user.updated_at = datetime.now(UTC)
    await db.commit()


async def get_user_from_token(db: AsyncSession, redis: aioredis.Redis, token: str) -> User:
    try:
        payload = security.decode_token(token)
    except JWTError as exc:
        raise InvalidTokenError from exc

    if payload.get("type") != "access":
        raise InvalidTokenError

    if await security.is_token_revoked(redis, token):
        raise InvalidTokenError

    user_id = uuid.UUID(payload["sub"])
    user = await db.get(User, user_id)
    if not user:
        raise InvalidTokenError
    return user
