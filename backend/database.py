import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Boolean, Float, Integer, DateTime, JSON, func, Index
from typing import Optional, Any
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://cs2user:cs2password@localhost:5432/cs2deals"
)

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SkinListing(Base):
    """One row per listing per scrape run.

    The primary key is a surrogate, not the CSFloat listing id, so the same
    listing reappearing in a later run becomes a new row rather than an
    overwrite. That is what makes price history possible.
    """
    __tablename__ = "skin_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # CSFloat's id for the listing. Not unique here: it repeats across runs.
    listing_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    # Groups every row written by a single scrape invocation.
    run_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)

    market_hash_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    float_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    paint_seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_stattrak: Mapped[bool] = mapped_column(Boolean, default=False)
    stickers: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )

    __table_args__ = (
        # Serving query: newest rows for one skin.
        Index("idx_skin_name_fetched", "market_hash_name", "fetched_at"),
        # Price history for one skin over time.
        Index("idx_skin_name_price", "market_hash_name", "price_usd"),
    )


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session