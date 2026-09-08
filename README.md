<div align="center">

# 🎯 CS2 Skin Tracker

**A high-performance, real-time CS2 skin deal aggregator and market analytics platform.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Async-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-Vite-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

The system ingests listings from the **CSFloat API**, calculates net discount percentages against predicted market baselines, and persists deal records in **PostgreSQL** for ultra-fast, sub-15ms filtering and search on a **React** dashboard.

## 📑 Table of Contents

- [Key Features](#-key-features)
- [Tech Stack](#️-tech-stack)
- [System Architecture](#-system-architecture)
- [Repository Structure](#-repository-structure)
- [Database Schema & Indexing Strategy](#-database-schema--indexing-strategy)
- [API Endpoints](#-api-endpoints)
- [Getting Started](#️-getting-started)
- [Strategic Design Decisions](#️-strategic-design-decisions)
- [License](#-license)

## 🚀 Key Features

| Feature | Description |
| :--- | :--- |
| 🛡️ **Cloudflare WAF Bypass** | Ingestion engine (`backend/scrape.py`) executes locally via residential IP to fetch CSFloat `/v1/listings` without tripping Cloudflare's data-center IP restrictions. |
| 💰 **Automated Valuation Engine** | Computes listing discount margins against CSFloat's predicted market price baseline. |
| ⚡ **Sub-15ms Dashboard Reads** | B-Tree indexes plus a composite index on `(discount_percent DESC, price ASC)` handle filtering, sorting, and pagination in a single lookup step. |
| 🔄 **FastAPI Async Backend** | Non-blocking ASGI engine powered by Uvicorn and SQLAlchemy ORM with automatic Pydantic request validation. |
| 🔐 **Stateless Authentication** | JWT bearer tokens (`python-jose`) and bcrypt password hashing (`passlib`). |
| 🌐 **Production Edge Proxy** | Caddy handles HTTPS auto-renewal, TLS termination, and response compression, targeting FastAPI on port `8000`. |

### Discount Formula

$$\text{Discount \\%} = \left( \frac{\text{Predicted Price} - \text{Listing Price}}{\text{Predicted Price}} \right) \times 100$$

## 🛠️ Tech Stack

| Layer | Technology | Role |
| :--- | :--- | :--- |
| **Frontend** | React, Vite, Tailwind CSS, Axios | Single-page dashboard with dynamic sorting, filtering, and responsive deal cards. |
| **Backend API** | FastAPI, Uvicorn, Pydantic | Asynchronous REST API serving user auth and deal query endpoints. |
| **Database** | PostgreSQL, SQLAlchemy ORM | Relational layer with custom B-Tree and composite indexing strategies. |
| **Ingestion Engine** | Python (`backend/scrape.py`), Requests | Local scraper executing batch upserts to the remote PostgreSQL instance on EC2. |
| **Edge / Security** | Caddy, JWT, Bcrypt | Reverse proxy with automatic SSL certificate management and stateless auth tokens. |

## 📐 System Architecture

```text
[ Local Ingestion Machine ]
       │
       ├─► Executes backend/scrape.py (Residential IP)
       ├─► Fetches /v1/listings via CSFloat API
       ├─► Extracts predicted_price & calculates discount_percent
       └─► Batch Upserts (ON CONFLICT UPDATE) into EC2 PostgreSQL
                                │
                                ▼
[ AWS EC2 Instance ]
       ┌────────────────────────────────────────────────────────┐
       │                                                        │
       │  [ Caddy Proxy ] (Ports 80 / 443)                      │
       │       │                                                │
       │       ▼ Reverse Proxy                                  │
       │  [ FastAPI + Uvicorn ] (Port 8000)                     │
       │       │                                                │
       │       ▼ Sub-15ms Reads (Depends(get_db))               │
       │  [ PostgreSQL Database ]                               │
       │       └─ Composite Index: (discount_percent, price)    │
       │                                                        │
       └────────────────────────────────────────────────────────┘
                                ▲
                                │ REST API Queries (/deals)
[ Client Browser ] ─────────────┘
  React Vite SPA
```

## 📁 Repository Structure

```text
cs2skintracker/
├── backend/
│   ├── auth.py           # JWT generation, token verification, bcrypt hashing
│   ├── database.py       # SQLAlchemy engine, connection pooling, get_db dependency
│   ├── main.py           # FastAPI application, REST router, CORS configuration
│   ├── models.py         # SQLAlchemy ORM models (User, Deal) & index definitions
│   ├── schemas.py        # Pydantic schemas for request/response serialization
│   └── scrape.py         # Local ingestion script with discount calc & DB upserts
├── src/                  # React Vite frontend SPA
│   ├── components/       # UI components (Navbar, DealCard, Filters, Stats)
│   ├── pages/            # Page routes (Deals.jsx, Login.jsx, Register.jsx)
│   └── services/         # Axios API client bindings
├── Caddyfile             # Caddy reverse proxy configuration
├── docker-compose.yml    # Multi-container orchestration (FastAPI + Postgres + Caddy)
└── requirements.txt      # Python backend dependencies
```

## 📊 Database Schema & Indexing Strategy

### `deals` Table Definition

| Field | Type | Modifiers | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(64)` | `PRIMARY KEY` | Unique CSFloat listing ID (derived directly from API payload). |
| `market_hash_name` | `VARCHAR(255)` | `INDEX` | Full skin name (e.g. `AK-47 \| Redline (Field-Tested)`). |
| `weapon_type` | `VARCHAR(50)` | `INDEX` | Category type (e.g. AK-47, Karambit). |
| `category` | `VARCHAR(50)` | `INDEX` | Item class (e.g. Rifle, Knife, Gloves). |
| `wear_name` | `VARCHAR(50)` | — | Wear condition (e.g. Factory New, Field-Tested). |
| `wear_float` | `DOUBLE PRECISION` | `INDEX` | Exact wear float value (0.0 – 1.0). |
| `price` | `DOUBLE PRECISION` | `INDEX` | Asking listing price in USD. |
| `predicted_price` | `DOUBLE PRECISION` | — | CSFloat estimated valuation baseline. |
| `discount_percent` | `DOUBLE PRECISION` | `INDEX` | Net calculated discount percentage. |
| `is_stattrak` | `BOOLEAN` | — | StatTrak flag. |
| `is_souvenir` | `BOOLEAN` | — | Souvenir item flag. |
| `icon_url` | `VARCHAR(512)` | — | Direct image thumbnail URL. |

### Why Composite Indexing Enables Sub-15ms Queries

The application relies on a composite B-Tree index defined in `backend/models.py`:

```python
__table_args__ = (
    Index('ix_deals_discount_price', 'discount_percent', 'price'),
)
```

- **Filtering & sorting in one step** — queries like `WHERE discount_percent >= 20 ORDER BY price ASC` traverse a single pre-sorted B-Tree structure on disk.
- **Zero memory sorting** — eliminates costly in-memory QuickSort operations on the EC2 server.
- **Instant early-exit** — with `LIMIT 50`, PostgreSQL reads the first 50 index leaves and returns immediately without scanning remaining records.

## ⚡ API Endpoints

### Deals

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/deals` | Returns a sorted list of CS2 skin deals matching filter parameters. |
| `GET` | `/deals/{deal_id}` | Retrieves details for a specific listing by its CSFloat ID. |

**Query parameters for `/deals`**

| Param | Type | Description |
| :--- | :--- | :--- |
| `min_discount` | `float` | Minimum net discount percentage. |
| `max_price` | `float` | Maximum asking price in USD. |
| `category` | `string` | Item class filter (Rifle, Knife, Gloves…). |
| `sort_by` | `string` | Sort key (e.g. `price`, `discount_percent`). |
| `limit` | `int` | Max number of records returned. |

### Authentication

| Method | Endpoint | Body | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/register` | `{ "username": "...", "email": "...", "password": "..." }` | Registers a new user with bcrypt password hashing. |
| `POST` | `/token` | OAuth2 password form (`username`, `password`) | Returns a signed JWT access token. |

## ⚙️ Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Node.js 18+ & npm
- Docker & Docker Compose (for deployment)

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/your-username/cs2skintracker.git
cd cs2skintracker

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/cs2_db"
export SECRET_KEY="your-super-secret-jwt-key"

# Start the FastAPI server
uvicorn backend.main:app --reload --port 8000
```

### 2. Running the Local Ingestion Engine

Seed or refresh the database with CSFloat market deals from your residential network:

```bash
# Set your CSFloat API key and DB connection string
export CSFLOAT_API_KEY="your_api_key_here"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/cs2_db"

# Execute scraper script
python backend/scrape.py
```

### 3. Frontend Setup

```bash
# Install npm dependencies
npm install

# Start Vite development server
npm run dev
```

## ⚖️ Strategic Design Decisions

<details>
<summary><b>Local ingestion vs. EC2 cloud scraping</b></summary>

Scraping directly from cloud infrastructure (AWS EC2) triggers Cloudflare `403 Forbidden` blocks due to data-center IP reputation. Running `scrape.py` locally bypasses IP bans cleanly while pushing structured data straight to PostgreSQL.

</details>

<details>
<summary><b>FastAPI ASGI vs. synchronous Flask</b></summary>

FastAPI's async event loop handles concurrent read requests efficiently on lightweight single-core EC2 instances without spawning excessive OS thread overhead.

</details>

<details>
<summary><b>SQLAlchemy ORM vs. raw SQL</b></summary>

SQLAlchemy abstracts query execution into clean, typed Python objects, neutralizes SQL injection vulnerabilities via automatic input parameterization, and integrates cleanly with FastAPI session injection (`Depends(get_db)`).

</details>

## 📝 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more information.
