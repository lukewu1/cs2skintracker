import asyncio
import os
import sys
import uuid
from pathlib import Path

import httpx
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError

from database import AsyncSessionLocal, SkinListing, init_db

CSFLOAT_API_KEY = os.environ["CSFLOAT_API_KEY"]
CSFLOAT_URL = "https://csfloat.com/api/v1/listings"

LIMIT_PER_SKIN = 20
REQUEST_SPACING_SECONDS = 2.0

MAX_429_RETRIES = 5
BACKOFF_BASE_SECONDS = 10.0
BACKOFF_MAX_SECONDS = 120.0

DEFAULT_SKINS = [
    "AK-47 | Redline (Field-Tested)",
    "AWP | Asiimov (Field-Tested)",
    "Desert Eagle | Printstream (Field-Tested)",
    "M4A1-S | Hyper Beast (Field-Tested)",
    "USP-S | Kill Confirmed (Minimal Wear)",
]


def normalize(raw: dict, run_id: str) -> SkinListing | None:
    """CSFloat's payload -> one snapshot row. None if it can't be priced.

    Auctions are skipped even though the request already filters on
    type=buy_now: an auction's "price" is a starting/current bid, not a
    fixed price, so it would corrupt the discount and lowest-price sorts
    if one ever slipped through.
    """
    if raw.get("type") == "auction":
        return None

    item = raw.get("item") or {}
    price = raw.get("price")
    if not isinstance(price, (int, float)):
        return None

    stickers = [s.get("name") for s in (item.get("stickers") or []) if s.get("name")]
    listing_id = str(raw.get("id"))

    return SkinListing(
        listing_id=listing_id,
        run_id=run_id,
        market_hash_name=item.get("market_hash_name") or item.get("item_name") or "Unknown item",
        price_usd=round(price / 100, 2), 
        float_value=item.get("float_value"),
        paint_seed=item.get("paint_seed"),
        is_stattrak=bool(item.get("is_stattrak")),
        stickers=stickers or None,
        url=f"https://csfloat.com/item/{listing_id}",
    )


async def fetch_listings(http: httpx.AsyncClient, skin: str) -> httpx.Response | None:
    """GET one skin's listings, retrying on 429 with exponential backoff.

    Returns None (caller skips the skin) on repeated rate-limiting, a
    non-200/429 status, or a network error.
    """
    for attempt in range(MAX_429_RETRIES + 1):
        try:
            res = await http.get(
                CSFLOAT_URL,
                params={
                    "market_hash_name": skin,
                    "sort_by": "lowest_price",
                    "limit": LIMIT_PER_SKIN,
                    "type": "buy_now",
                },
            )
        except httpx.RequestError as exc:
            print(f"  {skin}: network error ({exc.__class__.__name__})")
            return None

        if res.status_code == 429:
            if attempt == MAX_429_RETRIES:
                print(f"  {skin}: 429, giving up after {MAX_429_RETRIES} retries")
                return None
            wait = min(BACKOFF_BASE_SECONDS * (2 ** attempt), BACKOFF_MAX_SECONDS)
            print(f"  {skin}: 429, backing off {wait:.0f}s (retry {attempt + 1}/{MAX_429_RETRIES})")
            await asyncio.sleep(wait)
            continue

        if res.status_code != 200:
            print(f"  {skin}: HTTP {res.status_code}")
            return None

        return res

    return None


async def scrape(skins: list[str]) -> None:
    run_id = str(uuid.uuid4())
    print(f"run {run_id}: {len(skins)} skins")

    await init_db()

    written = 0
    failed = 0
    async with httpx.AsyncClient(
        timeout=20.0, headers={"Authorization": CSFLOAT_API_KEY}
    ) as http:
        for i, skin in enumerate(skins):
            if i > 0:
                await asyncio.sleep(REQUEST_SPACING_SECONDS)

            res = await fetch_listings(http, skin)
            if res is None:
                continue

            payload = res.json()
            raw_listings = payload.get("data", []) if isinstance(payload, dict) else payload

            rows = [r for r in (normalize(r, run_id) for r in raw_listings) if r]

            # Commit per skin, in a fresh session: a full run takes hours,
            # and a single commit at the end meant one dropped tunnel lost
            # the whole run. Now it loses only the skin in flight.
            try:
                async with AsyncSessionLocal() as db:
                    db.add_all(rows)
                    await db.commit()
            except (SQLAlchemyError, OSError) as exc:
                failed += 1
                print(f"  {skin}: write failed ({exc.__class__.__name__})")
                continue

            written += len(rows)
            print(f"  {skin}: {len(rows)} listings")

    print(f"wrote {written} rows" + (f", {failed} skins failed to write" if failed else ""))

    async with AsyncSessionLocal() as db:
        total = await db.scalar(select(func.count()).select_from(SkinListing))
        runs = await db.scalar(select(func.count(func.distinct(SkinListing.run_id))))
        print(f"table now holds {total} rows across {runs} runs")


def load_skins_from_file(path: str) -> list[str]:
    lines = Path(path).read_text().splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 1 and Path(args[0]).is_file():
        targets = load_skins_from_file(args[0])
    else:
        targets = args or DEFAULT_SKINS
    asyncio.run(scrape(targets))