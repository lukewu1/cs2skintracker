from datetime import datetime, timedelta, timezone

import pytest

from database import SkinListing


async def register(client, username="lukewu", password="hunter22"):
    return await client.post(
        "/api/auth/register", json={"username": username, "password": password}
    )


async def login(client, username="lukewu", password="hunter22"):
    return await client.post(
        "/api/auth/token", data={"username": username, "password": password}
    )


async def auth_headers(client, username="lukewu", password="hunter22"):
    await register(client, username, password)
    res = await login(client, username, password)
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- registration ---

async def test_register_creates_user(client):
    res = await register(client)
    assert res.status_code == 201
    body = res.json()
    assert body["username"] == "lukewu"
    assert "id" in body


async def test_register_duplicate_username_is_rejected(client):
    await register(client)
    res = await register(client)
    assert res.status_code == 409


async def test_register_normalizes_username_case_and_whitespace(client):
    res = await client.post(
        "/api/auth/register", json={"username": "  LukeWu  ", "password": "hunter22"}
    )
    assert res.status_code == 201
    assert res.json()["username"] == "lukewu"


# --- login ---

async def test_login_returns_bearer_token(client):
    await register(client)
    res = await login(client)
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


async def test_login_rejects_wrong_password(client):
    await register(client)
    res = await login(client, password="wrong-password")
    assert res.status_code == 401


async def test_login_rejects_unknown_user(client):
    res = await login(client, username="nobody")
    assert res.status_code == 401


# --- /api/auth/me ---

async def test_me_requires_auth(client):
    res = await client.get("/api/auth/me")
    assert res.status_code == 401


async def test_me_returns_current_user(client):
    headers = await auth_headers(client)
    res = await client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["username"] == "lukewu"


async def test_me_rejects_garbage_token(client):
    res = await client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert res.status_code == 401


# --- /api/skins ---

async def test_skins_lists_distinct_names(client, db_session):
    db_session.add_all(
        [
            SkinListing(
                listing_id="1",
                run_id="run-1",
                market_hash_name="AK-47 | Redline (Field-Tested)",
                price_usd=20.0,
            ),
            SkinListing(
                listing_id="2",
                run_id="run-1",
                market_hash_name="AK-47 | Redline (Field-Tested)",
                price_usd=22.0,
            ),
            SkinListing(
                listing_id="3",
                run_id="run-1",
                market_hash_name="AWP | Asiimov (Field-Tested)",
                price_usd=40.0,
            ),
        ]
    )
    await db_session.commit()

    headers = await auth_headers(client)
    res = await client.get("/api/skins", headers=headers)
    assert res.status_code == 200
    names = [s["market_hash_name"] for s in res.json()["skins"]]
    assert names == ["AK-47 | Redline (Field-Tested)", "AWP | Asiimov (Field-Tested)"]


# --- /api/listings ---

async def test_listings_requires_auth(client):
    res = await client.get("/api/listings", params={"market_hash_name": "AK-47 | Redline (Field-Tested)"})
    assert res.status_code == 401


async def test_listings_rejects_unknown_sort_by(client):
    headers = await auth_headers(client)
    res = await client.get(
        "/api/listings",
        params={"market_hash_name": "AK-47 | Redline (Field-Tested)", "sort_by": "bogus"},
        headers=headers,
    )
    assert res.status_code == 422


async def test_listings_empty_when_skin_has_no_data(client):
    headers = await auth_headers(client)
    res = await client.get(
        "/api/listings",
        params={"market_hash_name": "AK-47 | Redline (Field-Tested)"},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["listings"] == []
    assert body["baseline_price"] is None


async def test_listings_sorted_by_lowest_price(client, db_session):
    name = "AK-47 | Redline (Field-Tested)"
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            SkinListing(listing_id="1", run_id="run-1", market_hash_name=name, price_usd=30.0, fetched_at=now),
            SkinListing(listing_id="2", run_id="run-1", market_hash_name=name, price_usd=10.0, fetched_at=now),
            SkinListing(listing_id="3", run_id="run-1", market_hash_name=name, price_usd=20.0, fetched_at=now),
        ]
    )
    await db_session.commit()

    headers = await auth_headers(client)
    res = await client.get(
        "/api/listings",
        params={"market_hash_name": name, "sort_by": "lowest_price"},
        headers=headers,
    )
    prices = [row["price_usd"] for row in res.json()["listings"]]
    assert prices == [10.0, 20.0, 30.0]


async def test_listings_uses_only_the_latest_run(client, db_session):
    name = "AK-47 | Redline (Field-Tested)"
    older = datetime.now(timezone.utc) - timedelta(hours=2)
    newer = datetime.now(timezone.utc)
    db_session.add_all(
        [
            SkinListing(listing_id="stale", run_id="run-old", market_hash_name=name, price_usd=999.0, fetched_at=older),
            SkinListing(listing_id="fresh", run_id="run-new", market_hash_name=name, price_usd=25.0, fetched_at=newer),
        ]
    )
    await db_session.commit()

    headers = await auth_headers(client)
    res = await client.get(
        "/api/listings", params={"market_hash_name": name}, headers=headers
    )
    listings = res.json()["listings"]
    assert len(listings) == 1
    assert listings[0]["listing_id"] == "fresh"


async def test_listings_discount_reflects_drop_from_baseline(client, db_session):
    name = "AK-47 | Redline (Field-Tested)"
    baseline_time = datetime.now(timezone.utc) - timedelta(days=1)
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            # Establishes a $100 baseline average over the trailing window.
            SkinListing(listing_id="old", run_id="run-old", market_hash_name=name, price_usd=100.0, fetched_at=baseline_time),
            # Latest run: one listing 50% under that baseline.
            SkinListing(listing_id="deal", run_id="run-new", market_hash_name=name, price_usd=50.0, fetched_at=now),
        ]
    )
    await db_session.commit()

    headers = await auth_headers(client)
    res = await client.get(
        "/api/listings", params={"market_hash_name": name}, headers=headers
    )
    listings = res.json()["listings"]
    assert listings[0]["discount_pct"] == 33.3  # (100 avg of [100,50] -> 75) -> (75-50)/75*100


async def test_listings_lowest_float_sorts_nulls_last(client, db_session):
    name = "AK-47 | Redline (Field-Tested)"
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            SkinListing(listing_id="1", run_id="run-1", market_hash_name=name, price_usd=20.0, float_value=None, fetched_at=now),
            SkinListing(listing_id="2", run_id="run-1", market_hash_name=name, price_usd=20.0, float_value=0.05, fetched_at=now),
            SkinListing(listing_id="3", run_id="run-1", market_hash_name=name, price_usd=20.0, float_value=0.5, fetched_at=now),
        ]
    )
    await db_session.commit()

    headers = await auth_headers(client)
    res = await client.get(
        "/api/listings",
        params={"market_hash_name": name, "sort_by": "lowest_float"},
        headers=headers,
    )
    floats = [row["float_value"] for row in res.json()["listings"]]
    assert floats == [0.05, 0.5, None]


async def test_listings_response_is_cached_on_second_call(client, db_session):
    name = "AK-47 | Redline (Field-Tested)"
    db_session.add(
        SkinListing(listing_id="1", run_id="run-1", market_hash_name=name, price_usd=20.0)
    )
    await db_session.commit()

    headers = await auth_headers(client)
    first = await client.get("/api/listings", params={"market_hash_name": name}, headers=headers)
    second = await client.get("/api/listings", params={"market_hash_name": name}, headers=headers)

    assert first.json()["cached"] is False
    assert second.json()["cached"] is True
