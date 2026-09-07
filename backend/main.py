import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from database import get_db, init_db, User, SkinListing
from auth import verify_password, get_password_hash, create_access_token, get_current_user

REDIS_URL = os.environ["REDIS_URL"]
CACHE_TTL_SECONDS = 300

BASELINE_WINDOW_DAYS = 7

VALID_SORTS = {"best_deal", "lowest_price", "lowest_float", "most_recent"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.redis = redis.from_url(REDIS_URL, decode_responses=True)
    yield
    await app.state.redis.aclose()


app = FastAPI(lifespan=lifespan)

allowed = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_origin_regex=r"https://cs2skintracker-.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def health():
    return {"status": "ok"}


class RegisterIn(BaseModel):
    username: str
    password: str


@app.post("/api/auth/register", status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    username = body.username.strip().lower()

    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already registered")

    user = User(username=username, hashed_password=get_password_hash(body.password))
    db.add(user)
    await db.commit()
    return {"id": user.id, "username": user.username}


@app.post("/api/auth/token")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    username = form.username.strip().lower()
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token({"sub": user.username}),
        "token_type": "bearer",
    }


@app.get("/api/auth/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "is_active": user.is_active}


@app.get("/api/skins")
async def skins(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(
            SkinListing.market_hash_name,
            func.max(SkinListing.fetched_at).label("last_seen"),
        ).group_by(SkinListing.market_hash_name)
         .order_by(SkinListing.market_hash_name)
    )
    return {
        "skins": [
            {"market_hash_name": name, "last_seen": last_seen.isoformat()}
            for name, last_seen in rows.all()
        ]
    }


@app.get("/api/listings")
async def listings(
    market_hash_name: str = Query(..., min_length=1, max_length=128),
    sort_by: str = Query("best_deal"),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get the most recent snapshot for the skin
    if sort_by not in VALID_SORTS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown sort_by: {sort_by}")

    cache_key = f"listings:{market_hash_name}:{sort_by}:{limit}"

    try:
        cached = await app.state.redis.get(cache_key)
        if cached:
            return {**json.loads(cached), "cached": True}
    except Exception:
        pass

    # The newest scrape run that included this skin.
    latest_run = (
        select(SkinListing.run_id)
        .where(SkinListing.market_hash_name == market_hash_name)
        .order_by(SkinListing.fetched_at.desc())
        .limit(1)
        .scalar_subquery()
    )

    # Baseline: average price for this skin across the recent window,
    # including older runs. With only one run on record this equals the
    # current prices, so every discount reads 0% until history builds up.
    since = datetime.now(timezone.utc) - timedelta(days=BASELINE_WINDOW_DAYS)
    baseline = await db.scalar(
        select(func.avg(SkinListing.price_usd)).where(
            SkinListing.market_hash_name == market_hash_name,
            SkinListing.fetched_at >= since,
        )
    )

    query = select(SkinListing).where(
        SkinListing.market_hash_name == market_hash_name,
        SkinListing.run_id == latest_run,
    )

    if sort_by in ("best_deal", "lowest_price"):
        # Within one skin the baseline is constant, so ranking by discount
        # and by price give the same order. The discount matters when the
        # client merges results across several skins.
        query = query.order_by(SkinListing.price_usd.asc())
    elif sort_by == "lowest_float":
        query = query.order_by(SkinListing.float_value.asc().nulls_last())
    else:  # most_recent
        query = query.order_by(SkinListing.fetched_at.desc(), SkinListing.price_usd.asc())

    rows = (await db.execute(query.limit(limit))).scalars().all()

    if not rows:
        return {
            "listings": [],
            "fetched_at": None,
            "baseline_price": None,
            "cached": False,
        }

    def discount(price: float) -> float | None:
        if not baseline or baseline <= 0:
            return None
        return round((baseline - price) / baseline * 100, 1)

    payload = {
        "listings": [
            {
                "id": str(r.id),
                "listing_id": r.listing_id,
                "name": r.market_hash_name,
                "price_usd": r.price_usd,
                "float_value": r.float_value,
                "paint_seed": r.paint_seed,
                "is_stattrak": r.is_stattrak,
                "stickers": r.stickers or [],
                "url": r.url,
                "discount_pct": discount(r.price_usd),
            }
            for r in rows
        ],
        "fetched_at": rows[0].fetched_at.isoformat(),
        "baseline_price": round(baseline, 2) if baseline else None,
    }

    try:
        await app.state.redis.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(payload))
    except Exception:
        pass

    return {**payload, "cached": False}