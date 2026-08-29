# CS2 Skin Deal Scanner

A price-anomaly detector for the Counter-Strike 2 skin market. It pulls live listings from the CSFloat marketplace, groups them by item and float value, and flags listings priced meaningfully below comparable ones.

The interesting problem here isn't fetching listings — it's deciding what "underpriced" means. Two AK-47 Redlines can differ in price by 4x based on a float value in the fourth decimal place, so a naive lowest-price sort is useless. This project compares each listing only against peers with the same item name, StatTrak status, and a float within ±0.015, then measures the discount against that peer group's median.

**Status:** backend deployed and functional. Frontend auth is in progress — see [Roadmap](#roadmap).

<!-- TODO: add a screenshot of the deals page here. This is the first thing anyone looks at. -->

---

## Stack

**Frontend** — React 19, Vite, React Router
**Backend** — FastAPI, SQLAlchemy 2.0 (async), Pydantic
**Data** — PostgreSQL 16, Redis 7
**Auth** — JWT bearer tokens (PyJWT), bcrypt password hashing
**Infra** — Docker Compose on AWS EC2

## Architecture

```
React (Vite)
     │  HTTP + Bearer token
     ▼
FastAPI ──────► CSFloat API
     │
     ├──► PostgreSQL   users, listing history
     └──► Redis        response cache
```

The backend runs as three Compose services on a single EC2 instance. Postgres and Redis bind to `127.0.0.1` only; the API is the sole externally reachable service.

## How deal detection works

1. Fetch up to 50 live `buy_now` listings for a given `market_hash_name` from CSFloat.
2. Classify each listing's float into a wear bracket (FN / MW / FT / WW / BS) and then a quality tier within that bracket. A 0.152 Field-Tested and a 0.370 Field-Tested are both "FT" but are not remotely comparable in price.
3. For each listing, build a peer set: same item, same StatTrak status, float within ±0.015.
4. Take the median peer price as the reference. Flag the listing if its discount against that reference clears the threshold (default 10%).
5. Return flagged listings sorted by discount.

**Known limitation:** the reference price is currently computed from the same response batch, which biases it when results arrive sorted by price. Replacing this with a rolling median over persisted historical listings is the top item on the roadmap.

## API

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | — | Create an account |
| `POST` | `/api/auth/token` | — | Exchange credentials for a JWT (form-encoded) |
| `GET` | `/api/auth/me` | Bearer | Current user |
| `GET` | `/api/listings` | Bearer | Scan for deals |

`/api/listings` accepts `market_hash_name`, `sort_by`, `limit`, `min_float`, `max_float`, and `min_discount`.

Interactive docs at `/docs` when running.

## Running locally

Requires Docker, Node 18+, and a [CSFloat API key](https://csfloat.com/profile).

```bash
git clone https://github.com/lukewu1/cs2skintracker.git
cd cs2skintracker
```

Create `.env` in the project root:

```
CSFLOAT_API_KEY=your_key_here
JWT_SECRET_KEY=generate_with_openssl_rand_hex_32
POSTGRES_PASSWORD=choose_something
```

Start the backend:

```bash
docker compose up --build
```

Start the frontend:

```bash
npm install
npm run dev
```

Backend on `:8000`, frontend on `:5173`.

## Roadmap

- [ ] Login and registration UI, with a protected-route wrapper and bearer token injection
- [ ] Persist fetched listings and compute reference prices from a rolling historical window
- [ ] Redis caching layer on CSFloat responses (the API is rate limited; every request currently hits it live)
- [ ] Background polling job so watchlists refresh on a schedule instead of on page load
- [ ] Test suite — pytest for the API, unit coverage on float classification and discount logic
- [ ] CI via GitHub Actions
- [ ] Alembic migrations to replace `create_all` at startup
- [ ] TLS termination and a tightened CORS origin list

## Notes

Prices come from CSFloat and reflect a single marketplace, not a global consensus price. Nothing here is financial advice about a video game economy.
