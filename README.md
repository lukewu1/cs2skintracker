# CS2 Skin Tracker

Pulls CS2 skin listings from the CSFloat API, compares each asking price against CSFloat's own predicted market value, and serves the underpriced ones through a React dashboard.

Stack: FastAPI + PostgreSQL + React (Vite), behind nginx on a single EC2 t3 instance.

<!-- TODO: drop a dashboard screenshot here. A README with a picture of the
     thing reads very differently from one without. -->
<!-- ![Dashboard](docs/dashboard.png) -->

## How it works

The scraper (`backend/scrape.py`) runs on my own machine rather than on the server. CSFloat sits behind Cloudflare, which blocks requests from AWS IP ranges, so anything running on EC2 gets a 403 immediately. Running it from a residential connection sidesteps that. It fetches `/v1/listings`, computes a discount for each item, and batch-upserts straight into the remote Postgres instance:

```
discount_percent = (predicted_price - price) / predicted_price * 100
```

The API on EC2 only ever reads. It has no idea the scraper exists.

Everything else is conventional: FastAPI with SQLAlchemy and Pydantic, JWT auth with bcrypt hashing, nginx in front for TLS and compression.

## Query performance

The dashboard's main query filters on discount and sorts on price. There's a composite index for exactly that, in `backend/models.py`:

```python
__table_args__ = (
    Index('ix_deals_discount_price', 'discount_percent', 'price'),
)
```

Because the index is ordered on both columns, `WHERE discount_percent >= 20 ORDER BY price ASC LIMIT 50` walks a pre-sorted structure and stops after 50 leaves. No sort node, no full scan.

<!-- TODO: replace the block below with real output. Run:
       EXPLAIN ANALYZE SELECT * FROM deals WHERE discount_percent >= 20
       ORDER BY price ASC LIMIT 50;
     Paste the actual planner output and the actual execution time. A measured
     number with a plan behind it is worth more than any adjective. If it turns
     out to be 40ms, say 40ms. -->

## Setup

Needs Python 3.10+, PostgreSQL 14+, Node 18+.

**Backend**

```bash
git clone https://github.com/your-username/cs2skintracker.git
cd cs2skintracker

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/cs2_db"
export SECRET_KEY="your-super-secret-jwt-key"

uvicorn backend.main:app --reload --port 8000
```

**Scraper** — run this locally, not on the server:

```bash
export CSFLOAT_API_KEY="your_api_key_here"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/cs2_db"

python backend/scrape.py
```

**Frontend**

```bash
npm install
npm run dev
```

There's a `docker-compose.yml` that brings up FastAPI, Postgres, and nginx together for deployment.

## API

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/deals` | Filtered, sorted list of deals. |
| `GET` | `/deals/{deal_id}` | Single listing by CSFloat ID. |
| `POST` | `/register` | New account. Body: `username`, `email`, `password`. |
| `POST` | `/token` | OAuth2 password form. Returns a JWT. |

`/deals` accepts `min_discount` (float), `max_price` (float), `category` (string), `sort_by` (string), and `limit` (int).

## Schema

The `deals` table:

| Field | Type | Notes |
| :--- | :--- | :--- |
| `id` | `VARCHAR(64)` | Primary key. CSFloat's listing ID, used directly. |
| `market_hash_name` | `VARCHAR(255)` | Indexed. Full name, e.g. `AK-47 \| Redline (Field-Tested)`. |
| `weapon_type` | `VARCHAR(50)` | Indexed. AK-47, Karambit, etc. |
| `category` | `VARCHAR(50)` | Indexed. Rifle, Knife, Gloves. |
| `wear_name` | `VARCHAR(50)` | Factory New, Field-Tested, etc. |
| `wear_float` | `DOUBLE PRECISION` | Indexed. 0.0–1.0. |
| `price` | `DOUBLE PRECISION` | Indexed. Asking price, USD. |
| `predicted_price` | `DOUBLE PRECISION` | CSFloat's valuation. |
| `discount_percent` | `DOUBLE PRECISION` | Indexed. Computed at ingest. |
| `is_stattrak` | `BOOLEAN` | |
| `is_souvenir` | `BOOLEAN` | |
| `icon_url` | `VARCHAR(512)` | Thumbnail. |

Upserts use `ON CONFLICT (id) DO UPDATE`, so re-running the scraper refreshes prices on listings it's already seen instead of erroring.

## Notes on a few choices

**Why the scraper is separate.** Mostly forced. Cloudflare blocked data-center IPs. CSFLOAT explicitly says the reason for this is to prevent sniper and auto-buy bots. The split turned out fine: ingest and serve scale independently, and the API stays read-only.

**Why FastAPI over Flask.** The EC2 instance is single-core. An async event loop handles concurrent dashboard reads without spawning a thread per request.

**Why the ORM.** Parameterization comes free, which matters since the filter params come straight off query strings. `Depends(get_db)` handles session lifecycle without boilerplate.
