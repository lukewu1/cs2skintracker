from scrape import RATE_LIMIT_MAX_WAIT_SECONDS, normalize, rate_limit_wait


def make_raw(**overrides):
    raw = {
        "id": 12345,
        "price": 2599,  # cents
        "type": "buy_now",
        "item": {
            "market_hash_name": "AK-47 | Redline (Field-Tested)",
            "float_value": 0.234,
            "paint_seed": 42,
            "is_stattrak": False,
            "stickers": [],
        },
    }
    raw.update(overrides)
    return raw


def test_normalize_converts_price_from_cents_to_dollars():
    row = normalize(make_raw(price=2599), run_id="run-1")
    assert row.price_usd == 25.99


def test_normalize_rejects_auction_listings():
    row = normalize(make_raw(type="auction"), run_id="run-1")
    assert row is None


def test_normalize_missing_price_returns_none():
    raw = make_raw()
    del raw["price"]
    assert normalize(raw, run_id="run-1") is None


def test_normalize_non_numeric_price_returns_none():
    row = normalize(make_raw(price="not-a-number"), run_id="run-1")
    assert row is None


def test_normalize_carries_float_and_paint_seed():
    row = normalize(make_raw(), run_id="run-1")
    assert row.float_value == 0.234
    assert row.paint_seed == 42


def test_normalize_falls_back_to_item_name_when_no_market_hash_name():
    raw = make_raw()
    del raw["item"]["market_hash_name"]
    raw["item"]["item_name"] = "AK-47 | Redline"
    row = normalize(raw, run_id="run-1")
    assert row.market_hash_name == "AK-47 | Redline"


def test_normalize_defaults_name_when_nothing_available():
    raw = make_raw()
    del raw["item"]["market_hash_name"]
    row = normalize(raw, run_id="run-1")
    assert row.market_hash_name == "Unknown item"


def test_normalize_collects_sticker_names():
    raw = make_raw()
    raw["item"]["stickers"] = [{"name": "Katowice 2014"}, {"name": "Crown (Foil)"}]
    row = normalize(raw, run_id="run-1")
    assert row.stickers == ["Katowice 2014", "Crown (Foil)"]


def test_normalize_empty_stickers_becomes_none():
    row = normalize(make_raw(), run_id="run-1")
    assert row.stickers is None


def test_normalize_stattrak_flag_is_coerced_to_bool():
    raw = make_raw()
    raw["item"]["is_stattrak"] = True
    row = normalize(raw, run_id="run-1")
    assert row.is_stattrak is True


def test_normalize_builds_csfloat_url_from_listing_id():
    row = normalize(make_raw(id=999), run_id="run-1")
    assert row.url == "https://csfloat.com/item/999"


def test_normalize_tags_row_with_run_id():
    row = normalize(make_raw(), run_id="run-abc")
    assert row.run_id == "run-abc"


# --- rate_limit_wait ---

def test_rate_limit_wait_sleeps_until_reported_reset():
    wait = rate_limit_wait({"x-ratelimit-reset": "1100"}, now=1000.0)
    assert wait == 101.0  # 100s to the reset, plus a 1s margin


def test_rate_limit_wait_reset_in_the_past_waits_only_the_margin():
    assert rate_limit_wait({"x-ratelimit-reset": "900"}, now=1000.0) == 1.0


def test_rate_limit_wait_caps_absurd_resets():
    wait = rate_limit_wait({"x-ratelimit-reset": "99999999999"}, now=1000.0)
    assert wait == RATE_LIMIT_MAX_WAIT_SECONDS


def test_rate_limit_wait_falls_back_to_retry_after():
    assert rate_limit_wait({"retry-after": "30"}, now=1000.0) == 30.0


def test_rate_limit_wait_none_without_usable_headers():
    assert rate_limit_wait({}, now=1000.0) is None
    assert rate_limit_wait({"x-ratelimit-reset": "soon"}, now=1000.0) is None
