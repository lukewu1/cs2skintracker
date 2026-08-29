import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Boolean, Float, Integer, DateTime, func, Index
from typing import Optional
from datetime import datetime

DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql+asyncpg://cs2user:cs2password@postgres:5432/cs2deals"
)

# Convert standard postgresql:// schema to asyncpg if needed
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
    __tablename__ = "skin_listings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    market_hash_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    float_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    float_tier: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    paint_seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_stattrak: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("idx_skin_price_float", "market_hash_name", "is_stattrak", "float_value"),
    )

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
