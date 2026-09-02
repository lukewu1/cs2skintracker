import json
import os
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from database import get_db, init_db, User
from auth import verify_password, get_password_hash, create_access_token, get_current_user

CSFLOAT_API_KEY = os.environ["CSFLOAT_API_KEY"]
CSFLOAT_URL = "https://csfloat.com/api/v1/listings"
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
CACHE_TTL_SECONDS = 60

VALID_SORTS = {"best_deal", "lowest_price", "most_recent", "lowest_float", "highest_discount"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.redis = redis.from_url(REDIS_URL, decode_responses=True)
    app.state.http = httpx.AsyncClient(
        timeout=15.0,
        headers={"Authorization": CSFLOAT_API_KEY},
    )
    yield
    await app.state.http.aclose()
    await app.state.redis.aclose()


app = FastAPI(lifespan=lifespan)

allowed = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed + ["http://localhost:5173"],
    # Get ready for vercel deployment
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterIn(BaseModel):
    username: str
    password: str


@app.post("/api/auth/register", status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already registered")

    user = User(username=body.username, hashed_password=get_password_hash(body.password))
    db.add(user)
    await db.commit()
    return {"id": user.id, "username": user.username}


@app.post("/api/auth/token")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == form.username))
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


def normalize_listing(raw: dict) -> dict:
    """Flatten a CSFloat listing into the shape Deals.jsx renders."""
    item = raw.get("item") or {}
    stickers = [s.get("name") for s in (item.get("stickers") or []) if s.get("name")]

    price = raw.get("price")

    return {
        "id": str(raw.get("id")),
        "name": item.get("market_hash_name") or item.get("item_name") or "Unknown item",
        # CSFloat returns cents; the frontend calls .toFixed(2) on dollars.
        "price_usd": round(price / 100, 2) if isinstance(price, (int, float)) else None,
        "float_value": item.get("float_value"),
        "paint_seed": item.get("paint_seed"),
        "is_stattrak": bool(item.get("is_stattrak")),
        "stickers": stickers,
        "url": f"https://csfloat.com/item/{raw.get('id')}",
    }


@app.get("/api/listings")
async def listings(
    market_hash_name: str = Query(..., min_length=1, max_length=128),
    sort_by: str = Query("best_deal"),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
):
    if sort_by not in VALID_SORTS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown sort_by: {sort_by}")

    cache_key = f"listings:{market_hash_name}:{sort_by}:{limit}"

    try:
        cached = await app.state.redis.get(cache_key)
        if cached:
            return {"listings": json.loads(cached), "cached": True}
    except Exception:
        cached = None

    try:
        res = await app.state.http.get(
            CSFLOAT_URL,
            params={
                "market_hash_name": market_hash_name,
                "sort_by": sort_by,
                "limit": limit,
            },
        )
    except httpx.RequestError:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not reach CSFloat")

    if res.status_code == 429:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "CSFloat rate limit hit, try again shortly")
    if res.status_code == 401:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "CSFloat rejected the API key")
    if res.status_code >= 400:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"CSFloat returned {res.status_code}")

    payload = res.json()
    raw_listings = payload.get("data", []) if isinstance(payload, dict) else payload

    results = [normalize_listing(item) for item in raw_listings]
    results = [r for r in results if r["price_usd"] is not None]

    try:
        await app.state.redis.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(results))
    except Exception:
        pass

    return {"listings": results, "cached": False}