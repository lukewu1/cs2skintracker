import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CSFLOAT_API_KEY", "test-csfloat-key")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from database import Base, get_db
import main as main_module


class FakeRedis:
    """In-memory stand-in for the redis client main.py caches responses in."""

    def __init__(self):
        self._store = {}

    async def get(self, key):
        return self._store.get(key)

    async def setex(self, key, ttl, value):
        self._store[key] = value

    async def incr(self, key):
        self._store[key] = int(self._store.get(key, 0)) + 1
        return self._store[key]

    async def expire(self, key, ttl):
        pass

    async def delete(self, key):
        self._store.pop(key, None)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """Async client hitting the real app, DB swapped for SQLite and Redis faked.

    Does not run FastAPI's lifespan (that would call init_db() against the
    real Postgres DATABASE_URL), so app.state.redis is set by hand instead.
    """

    async def override_get_db():
        yield db_session

    main_module.app.dependency_overrides[get_db] = override_get_db
    main_module.app.state.redis = FakeRedis()

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    main_module.app.dependency_overrides.clear()
