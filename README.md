# CS2 Skin Tracker

Pulls CS2 skin listings from the CSFloat API, compares each listing's price against that skin's own 7-day trailing average, and serves the underpriced ones through a React dashboard.

Stack: FastAPI + PostgreSQL + React (Vite), behind nginx on a single EC2 t3 instance.

<!-- TODO: drop a dashboard screenshot here. A README with a picture of the
     thing reads very differently from one without. -->
<!-- ![Dashboard](docs/dashboard.png) -->

## How it works

The scraper (`backend/scrape.py`) runs on my own machine rather than on the server, on a `launchd` schedule. CSFloat sits behind Cloudflare, which blocks requests from AWS IP ranges, so anything running on EC2 gets a 403 immediately. Running it from a residential connection sidesteps that. It fetches `/v1/listings` (excluding auctions — only `type=buy_now`), tags every row with a `run_id` for that invocation, and batch-inserts snapshots straight into the remote Postgres instance over an SSH tunnel.

The API on EC2 only ever reads — it has no discount stored anywhere. `GET /api/listings` computes it at request time, per listing, against that skin's own trailing average over `backend/main.py`'s `BASELINE_WINDOW_DAYS` (7 days):

```python
discount_pct = round((baseline_price - price) / baseline_price * 100, 1)
```

Results are cached in Redis for `CACHE_TTL_SECONDS` (5 minutes), keyed on skin + sort + limit.

Everything else is conventional: FastAPI with SQLAlchemy and Pydantic, JWT auth with bcrypt hashing, nginx in front for TLS and compression.

## Query performance

`GET /api/listings` always filters on `market_hash_name` and either sorts on `price_usd` or `fetched_at`. Two composite indexes on `skin_listings` (`backend/database.py`) cover that:

```python
__table_args__ = (
    Index("idx_skin_name_fetched", "market_hash_name", "fetched_at"),
    Index("idx_skin_name_price", "market_hash_name", "price_usd"),
)
```

<!-- TODO: replace this with a real EXPLAIN ANALYZE run against skin_listings
     for a skin with meaningful row counts. A measured number with a plan
     behind it is worth more than any adjective. -->

## Setup

Needs Python 3.10+, PostgreSQL 14+, Node 18+.

**Backend**

```bash
git clone https://github.com/your-username/cs2skintracker.git
cd cs2skintracker/backend

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/cs2_db"
export JWT_SECRET_KEY="your-super-secret-jwt-key"
export REDIS_URL="redis://localhost:6379"
export CSFLOAT_API_KEY="your_api_key_here"
export ALLOWED_ORIGINS="http://localhost:5173"

uvicorn main:app --reload --port 8000
```

**Scraper** — run this locally, not on the server (from `backend/`, same env vars as above):

```bash
python scrape.py                 # DEFAULT_SKINS, a handful of well-known ones
python scrape.py skins.txt       # everything in a text file, one market_hash_name per line
```

**Frontend**

```bash
npm install
npm run dev
```

There's a `docker-compose.yml` that brings up FastAPI, Postgres, and nginx together for deployment.

## Testing

**Backend**

```bash
pip install -r backend/requirements-dev.txt
cd backend
pytest
```

Auth (hashing, JWT signing/expiry) and `scrape.py`'s `normalize()` are tested as pure functions. The API routes are tested end-to-end against the real FastAPI app with SQLite swapped in for Postgres and an in-memory fake standing in for Redis, so the suite needs no live database, tunnel, or external service to run.

**Frontend**

```bash
npm run test
```

Covers `src/auth.js` (token storage, `authFetch`'s header/401 handling) with a stubbed `localStorage` and mocked `fetch`, so no backend needs to be running.

Both suites run in CI on every push/PR via `.github/workflows/test.yml`.

## API

All routes except `/` and auth require `Authorization: Bearer <token>`.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Health check. |
| `POST` | `/api/auth/register` | New account. Body: `username`, `password`. |
| `POST` | `/api/auth/token` | OAuth2 password form. Returns a JWT. |
| `GET` | `/api/auth/me` | Current user. |
| `GET` | `/api/skins` | Every distinct `market_hash_name` on record, with its last-seen time. |
| `GET` | `/api/listings` | Listings for one skin's latest scrape run. |

`/api/listings` requires `market_hash_name` and accepts `sort_by` (`best_deal` \| `lowest_price` \| `lowest_float` \| `most_recent`, default `best_deal`) and `limit` (1-50, default 20). Response includes each listing's `discount_pct` against the skin's 7-day baseline, plus `cached` (whether it came from the Redis cache).

## Schema

The `skin_listings` table — one row per listing per scrape run, so the same CSFloat listing reappearing in a later run becomes a new row, not an overwrite. That's what makes price history (and the 7-day baseline) possible.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `id` | `INTEGER` | Primary key, autoincrement (surrogate — not CSFloat's ID). |
| `listing_id` | `VARCHAR(64)` | Indexed. CSFloat's listing ID; repeats across runs. |
| `run_id` | `VARCHAR(36)` | Indexed. Groups every row written by one scrape invocation. |
| `market_hash_name` | `VARCHAR(128)` | Indexed. Full name, e.g. `AK-47 \| Redline (Field-Tested)`. |
| `price_usd` | `DOUBLE PRECISION` | Asking price. |
| `float_value` | `DOUBLE PRECISION` | Nullable. 0.0–1.0. |
| `paint_seed` | `INTEGER` | Nullable. |
| `is_stattrak` | `BOOLEAN` | |
| `stickers` | `JSON` | Nullable. List of sticker names. |
| `url` | `VARCHAR(255)` | Nullable. `https://csfloat.com/item/{listing_id}`. |
| `fetched_at` | `TIMESTAMPTZ` | Indexed. Defaults to insert time. |

## Notes on a few choices

**Why the scraper is separate.** Mostly forced. Cloudflare blocked data-center IPs. CSFLOAT explicitly says the reason for this is to prevent sniper and auto-buy bots. The split turned out fine: ingest and serve scale independently, and the API stays read-only.

**Why FastAPI over Flask.** The EC2 instance is single-core. An async event loop handles concurrent dashboard reads without spawning a thread per request.

**Why the ORM.** Parameterization comes free, which matters since the filter params come straight off query strings. `Depends(get_db)` handles session lifecycle without boilerplate.
