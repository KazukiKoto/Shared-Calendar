import pytest_asyncio
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.user import User  # noqa: F401 — registers table with metadata


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS calendar_app"))
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.execute(delete(User))
        await session.commit()
    await engine.dispose()


@pytest_asyncio.fixture
async def redis_client() -> aioredis.Redis:  # type: ignore[misc]
    r: aioredis.Redis = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
    yield r
    await r.aclose()


@pytest_asyncio.fixture
async def client(db: AsyncSession):
    async def _db_override():
        yield db

    app.dependency_overrides[get_db] = _db_override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
