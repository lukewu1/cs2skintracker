import os
from enum import Enum
from typing import Optional, List
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import httpx
import statistics

from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import init_db, get_db, User, SkinListing
from auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user
)

FLOAT_GROUPS = {
    "BS": {"bad": [0.9, 1.0], "mid": [0.5, 0.9], "good": [0.47, 0.5], "very good": [0.45, 0.47]},
    "WW": {"bad": [0.42, 0.45], "mid": [0.4, 0.42], "good": [0.39, 0.4], "very good": [0.38, 0.39]},
    "FT": {"bad": [0.27, 0.38], "mid": [0.21, 0.27], "good": [0.158, 0.21], "very good": [0.15, 0.158]},
    "MW": {"bad": [0.12, 0.15], "mid": [0.1, 0.12], "good": [0.08, 0.1], "very good": [0.07, 0.08]},
    "FN": {"bad": [0.04, 0.07], "mid": [0.03, 0.04], "good": [0.01, 0.03], "very good": [0.0, 0.01]},
}

load_dotenv()
CSFLOAT_API_KEY = os.environ.get("CSFLOAT_API_KEY", "")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    await init_db()
    yield

app = FastAPI(title="CS2 Deal Scanner & Auth API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SortBy(str, Enum):
    LOWEST_PRICE = "lowest_price"
    MOST_RECENT = "most_recent"
    BEST_DEAL = "best_deal"
    LOWEST_FLOAT = "lowest_float"

class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

def get_float_tier(float_val: Optional[float]) -> Optional[str]:
    if float_val is None:
        return None
    if float_val >= 0.45:
        group_wear = FLOAT_GROUPS["BS"]
    elif float_val >= 0.38:
        group_wear = FLOAT_GROUPS["WW"]
    elif float_val >= 0.15:
        group_wear = FLOAT_GROUPS["FT"]
    elif float_val >= 0.07:
        group_wear = FLOAT_GROUPS["MW"]
    else:
        group_wear = FLOAT_GROUPS["FN"]

    for tier_name, (low, high) in group_wear.items():
        if low <= float_val <= high:
            return tier_name
    return None

async def get_http_client():
    async with httpx.AsyncClient(
        base_url="https://csfloat.com/api/v1",
        headers={"Authorization": CSFLOAT_API_KEY} if CSFLOAT_API_KEY else {},
        timeout=15.0,
    ) as client:
        yield client

# --- Auth Endpoints ---

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.username == user_in.username)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    new_user = User(
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(new_user)
    await db.commit()
    return {"message": "User created successfully"}

@app.post("/api/auth/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.username == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me")
async def read_current_user(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "created_at": current_user.created_at
    }

# --- Protected Scanner Endpoint ---

@app.get("/api/listings")
async def fetch_market_listings(
    market_hash_name: Optional[str] = Query(None),
    sort_by: SortBy = Query(SortBy.LOWEST_PRICE),
    limit: int = Query(50, ge=1, le=50),
    min_float: Optional[float] = Query(None, ge=0.0, le=1.0),
    max_float: Optional[float] = Query(None, ge=0.0, le=1.0),
    min_discount: float = Query(0.10, ge=0.0, le=1.0),
    current_user: User = Depends(get_current_user),  # Requires Auth
    client: httpx.AsyncClient = Depends(get_http_client),
    db: AsyncSession = Depends(get_db),
):
    params = {"sort_by": sort_by.value, "limit": limit, "type": "buy_now"}
    if market_hash_name:
        params["market_hash_name"] = market_hash_name
    if min_float is not None:
        params["min_float"] = min_float
    if max_float is not None:
        params["max_float"] = max_float

    response = await client.get("/listings", params=params)

    if response.status_code == 429:
        raise HTTPException(status_code=429, detail="CSFloat rate limit reached.")
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    raw_data = response.json()
    items = raw_data if isinstance(raw_data, list) else raw_data.get("data", [])

    FLOAT_DELTA = 0.015
    formatted = []
    
    for entry in items:
        item_data = entry.get("item", {})
        float_val = item_data.get("float_value")
        price_usd = entry.get("price", 0) / 100
        is_st = item_data.get("is_stattrak", False) or entry.get("category") == 2
        tier = get_float_tier(float_val)

        formatted.append({
            "id": entry.get("id"),
            "name": item_data.get("market_hash_name"),
            "price_usd": price_usd,
            "float_value": float_val,
            "float_tier": tier,
            "paint_seed": item_data.get("paint_seed"),
            "is_stattrak": is_st,
            "stickers": [s.get("name", "").replace("Sticker | ", "") for s in item_data.get("stickers", [])],
            "url": f"https://csfloat.com/item/{entry.get('id')}",
        })

    good_deals = []
    for item in formatted:
        current_float = item.get("float_value")
        if current_float is None:
            continue

        peers = [
            peer for peer in formatted
            if peer["id"] != item["id"]
            and peer["name"] == item["name"]
            and peer["is_stattrak"] == item["is_stattrak"]
            and peer["float_value"] is not None
            and abs(peer["float_value"] - current_float) <= FLOAT_DELTA
        ]

        if peers:
            peer_prices = [p["price_usd"] for p in peers]
            ref_price = statistics.median(peer_prices)
            discount = (ref_price - item["price_usd"]) / ref_price if ref_price > 0 else 0.0

            if discount >= min_discount:
                item["peer_count"] = len(peers)
                item["ref_price_usd"] = round(ref_price, 2)
                item["discount_percent"] = round(discount * 100, 2)
                item["is_good_deal"] = True
                good_deals.append(item)

    good_deals.sort(key=lambda x: x["discount_percent"], reverse=True)
    return {"count": len(good_deals), "listings": good_deals}
