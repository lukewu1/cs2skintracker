import asyncio
import os
import sys
import uuid

import httpx
from sqlalchemy import select, func

from database import AsyncSessionLocal, SkinListing, init_db

CSFLOAT_API_KEY = os.environ["CSFLOAT_API_KEY"]
CSFLOAT_URL = "https://csfloat.com/api/v1/listings"

LIMIT_PER_SKIN = 20
REQUEST_SPACING_SECONDS = 2.0   

DEFAULT_SKINS = [
    "AK-47 | Redline (Field-Tested)",
    "AWP | Asiimov (Field-Tested)",
    "Desert Eagle | Printstream (Field-Tested)",
    "M4A1-S | Hyper Beast (Field-Tested)",
    "USP-S | Kill Confirmed (Minimal Wear)",
]


def normalize(raw: dict, run_id: str) -> SkinListing | None:
    """CSFloat's payload -> one snapshot row. None if it can't be priced."""
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


async def scrape(skins: list[str]) -> None:
    run_id = str(uuid.uuid4())
    print(f"run {run_id}: {len(skins)} skins")

    await init_db()

    written = 0
    async with httpx.AsyncClient(
        timeout=20.0, headers={"Authorization": CSFLOAT_API_KEY}
    ) as http:
        async with AsyncSessionLocal() as db:
            for i, skin in enumerate(skins):
                if i > 0:
                    await asyncio.sleep(REQUEST_SPACING_SECONDS)

                try:
                    res = await http.get(
                        CSFLOAT_URL,
                        params={
                            "market_hash_name": skin,
                            "sort_by": "lowest_price",
                            "limit": LIMIT_PER_SKIN,
                        },
                    )
                except httpx.RequestError as exc:
                    print(f"  {skin}: network error ({exc.__class__.__name__})")
                    continue

                if res.status_code == 429:
                    print(f"  {skin}: 429, stopping run")
                    break
                if res.status_code != 200:
                    print(f"  {skin}: HTTP {res.status_code}")
                    continue

                payload = res.json()
                raw_listings = payload.get("data", []) if isinstance(payload, dict) else payload

                rows = [r for r in (normalize(r, run_id) for r in raw_listings) if r]
                db.add_all(rows)
                written += len(rows)
                print(f"  {skin}: {len(rows)} listings")

            await db.commit()

    print(f"wrote {written} rows")

    async with AsyncSessionLocal() as db:
        total = await db.scalar(select(func.count()).select_from(SkinListing))
        runs = await db.scalar(select(func.count(func.distinct(SkinListing.run_id))))
        print(f"table now holds {total} rows across {runs} runs")


if __name__ == "__main__":
    targets = sys.argv[1:] or DEFAULT_SKINS
    asyncio.run(scrape(targets))