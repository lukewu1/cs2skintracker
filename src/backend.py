import os
from typing import Optional
from dotenv import load_dotenv
import httpx
from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

CSFLOAT_API_KEY = os.environ.get("CSFLOAT_API_KEY", "")

app = FastAPI(title="CS2 CSFloat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Reusable client dependency
async def get_http_client():
    async with httpx.AsyncClient(
        base_url="https://csfloat.com/api/v1",
        headers={"Authorization": CSFLOAT_API_KEY} if CSFLOAT_API_KEY else {},
        timeout=15.0,
    ) as client:
        yield client


@app.get("/api/listings")
async def fetch_market_listings(
    market_hash_name: Optional[str] = Query(None, description="Exact skin name, e.g. 'AK-47 | Redline (Field-Tested)'"),
    sort_by: str = Query("lowest_price", enum=["lowest_price", "most_recent", "best_deal", "lowest_float"]),
    limit: int = Query(50, ge=1, le=50),
    min_float: Optional[float] = Query(None, ge=0.0, le=1.0),
    max_float: Optional[float] = Query(None, ge=0.0, le=1.0),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    params = {
        "sort_by": sort_by,
        "limit": limit,
        "type": "buy_now",
    }
    if market_hash_name:
        params["market_hash_name"] = market_hash_name
    if min_float is not None:
        params["min_float"] = min_float
    if max_float is not None:
        params["max_float"] = max_float

    response = await client.get("/listings", params=params)

    if response.status_code == 429:
        raise HTTPException(status_code=429, detail="CSFloat rate limit reached. Please wait.")
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    raw_data = response.json()
    items = raw_data if isinstance(raw_data, list) else raw_data.get("data", [])

    formatted = []
    for entry in items:
        item_data = entry.get("item", {})
        formatted.append({
            "id": entry.get("id"),
            "name": item_data.get("market_hash_name"),
            "price_usd": entry.get("price", 0) / 100,
            "float_value": item_data.get("float_value"),
            "paint_seed": item_data.get("paint_seed"),
            "is_stattrak": item_data.get("is_stattrak", False),
            "stickers": [s.get("name", "").replace("Sticker | ", "") for s in item_data.get("stickers", [])],
            "url": f"https://csfloat.com/item/{entry.get('id')}",
        })

    return {"count": len(formatted), "listings": formatted}