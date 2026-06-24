from datetime import UTC, datetime, timedelta
from uuid import UUID

import redis.asyncio as aioredis
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

_BLOCKLIST = "blocklist:"
_RESET = "reset:"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: UUID) -> tuple[str, int]:
    delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(UTC) + delta
    token = jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "access"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return token, int(delta.total_seconds())


def create_refresh_token(user_id: UUID) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "refresh"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_token(token: str) -> dict:  # type: ignore[type-arg]
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


async def revoke_token(redis: aioredis.Redis, token: str, ttl: int) -> None:
    await redis.setex(f"{_BLOCKLIST}{token}", ttl, "1")


async def is_token_revoked(redis: aioredis.Redis, token: str) -> bool:
    return await redis.exists(f"{_BLOCKLIST}{token}") == 1


async def store_reset_token(
    redis: aioredis.Redis, token: str, user_id: UUID, ttl: int = 3600
) -> None:
    await redis.setex(f"{_RESET}{token}", ttl, str(user_id))


async def consume_reset_token(redis: aioredis.Redis, token: str) -> UUID | None:
    key = f"{_RESET}{token}"
    raw = await redis.get(key)
    if not raw:
        return None
    await redis.delete(key)
    return UUID(raw)
