CS2 Skin Tracker 🎯A high-performance, real-time CS2 skin deal aggregator and market analytics platform. The system ingests listings from the CSFloat API, calculates net discount percentages against predicted market baselines, and persists deal records in PostgreSQL for ultra-fast, sub-15ms filtering and search on a React dashboard.🚀 Key FeaturesCloudflare WAF Bypass Architecture: Ingestion engine (backend/scrape.py) executes locally via residential IP to fetch CSFloat API listings (/v1/listings) without getting blocked by Cloudflare's AWS EC2 Data Center IP restrictions.Automated Valuation & Discount Engine: Computes listing discount margins using CSFloat's predicted market price baseline:$$\text{Discount \%} = \left( \frac{\text{Predicted Price} - \text{Listing Price}}{\text{Predicted Price}} \right) \times 100$$Sub-15ms Dashboard Reads: PostgreSQL database boosted with B-Tree indexes and a specialized Composite Index on (discount_percent DESC, price ASC) to handle filtering, sorting, and pagination in a single lookup step.FastAPI Async Backend: Non-blocking ASGI engine powered by Uvicorn and SQLAlchemy ORM with automatic Pydantic request validation.Stateless Authentication: User management and session security powered by JWT bearer tokens (python-jose) and bcrypt password hashing (passlib).Production Edge Proxy: HTTPS auto-renewal, TLS termination, and response compression managed by Caddy Server targeting FastAPI on port 8000.🛠️ Tech StackLayerTechnologyRoleFrontendReact, Vite, Tailwind CSS, AxiosSingle-page application dashboard with dynamic sorting, filtering, and responsive deal cards.Backend APIFastAPI, Uvicorn, PydanticAsynchronous REST API serving user auth and deal query endpoints.DatabasePostgreSQL, SQLAlchemy ORMRelational database layer with custom B-Tree and Composite indexing strategies.Ingestion EnginePython (backend/scrape.py), RequestsLocal scraper executing batch upserts to the remote PostgreSQL instance on EC2.Edge / SecurityCaddy, JWT, BcryptReverse proxy with automatic SSL certificate management and stateless auth tokens.📐 System Architecture[ Local Ingestion Machine ]
       │
       ├─► Executes backend/scrape.py (Residential IP)
       ├─► Fetches /v1/listings via CSFloat API
       ├─► Extracts predicted_price & calculates discount_percent
       └─► Batch Upserts (ON CONFLICT UPDATE) into EC2 PostgreSQL
                                │
                                ▼
[ AWS EC2 Instance ]
       ┌─────────────────────────────────────────────────────────┐
       │                                                         │
       │  [ Caddy Proxy ] (Ports 80 / 443)                        │
       │       │                                                 │
       │       ▼ Reverse Proxy                                   │
       │  [ FastAPI + Uvicorn ] (Port 8000)                        │
       │       │                                                 │
       │       ▼ Sub-15ms Reads (Depends(get_db))                 │
       │  [ PostgreSQL Database ]                                 │
       │       └─ Composite Index: (discount_percent, price)    │
       │                                                         │
       └─────────────────────────────────────────────────────────┘
                                ▲
                                │ REST API Queries (/deals)
[ Client Browser ] ─────────────┘
  React Vite SPA
📁 Repository Structurecs2skintracker/
├── backend/
│   ├── auth.py          # JWT generation, token verification, bcrypt hashing
│   ├── database.py      # SQLAlchemy engine, connection pooling, get_db dependency
│   ├── main.py          # FastAPI application, REST router, CORS configuration
│   ├── models.py        # SQLAlchemy ORM models (User, Deal) & index definitions
│   ├── schemas.py       # Pydantic schemas for request/response serialization
│   └── scrape.py        # Local ingestion script with discount calculation & DB upserts
├── src/                 # React Vite frontend SPA
│   ├── components/      # UI components (Navbar, DealCard, Filters, Stats)
│   ├── pages/           # Page routes (Deals.jsx, Login.jsx, Register.jsx)
│   └── services/        # Axios API client bindings
├── Caddyfile            # Caddy reverse proxy configuration
├── docker-compose.yml   # Multi-container orchestration (FastAPI + Postgres + Caddy)
└── requirements.txt     # Python backend dependencies
📊 Database Schema & Indexing Strategydeals Table DefinitionFieldTypeModifiersDescriptionidVARCHAR(64)PRIMARY KEYUnique CSFloat listing ID (derived directly from API payload).market_hash_nameVARCHAR(255)INDEXFull skin name (e.g., AK-47 | Redline (Field-Tested)).weapon_typeVARCHAR(50)INDEXCategory type (e.g., AK-47, Karambit).categoryVARCHAR(50)INDEXItem class (e.g., Rifle, Knife, Gloves).wear_nameVARCHAR(50)-Wear condition (e.g., Factory New, Field-Tested).wear_floatDOUBLE PRECISIONINDEXExact wear float value (0.0 to 1.0).priceDOUBLE PRECISIONINDEXAsking listing price in USD.predicted_priceDOUBLE PRECISION-CSFloat estimated valuation baseline.discount_percentDOUBLE PRECISIONINDEXNet calculated discount percentage.is_stattrakBOOLEAN-StatTrak flag.is_souvenirBOOLEAN-Souvenir item flag.icon_urlVARCHAR(512)-Direct image thumbnail URL.Why Composite Indexing Enables Sub-15ms QueriesThe application relies on a composite B-Tree index defined in backend/models.py:__table_args__ = (
    Index('ix_deals_discount_price', 'discount_percent', 'price'),
)
Filtering & Sorting in One Step: Queries like WHERE discount_percent >= 20 ORDER BY price ASC traverse a single pre-sorted B-Tree structure on disk.Zero Memory Sorting: Completely eliminates costly in-memory QuickSort operations on the EC2 server.Instant Early-Exit: With LIMIT 50, PostgreSQL reads the first 50 index leaves directly and returns immediately without scanning remaining records.⚡ API EndpointsPublic & Deal EndpointsGET /dealsQuery Params: min_discount (float), max_price (float), category (string), sort_by (string), limit (int)Description: Returns a sorted list of CS2 skin deals matching filter parameters.GET /deals/{deal_id}Description: Retrieves details for a specific listing by its CSFloat ID.Authentication EndpointsPOST /registerBody: { "username": "...", "email": "...", "password": "..." }Description: Registers a new user account with bcrypt password hashing.POST /tokenBody: OAuth2 password form (username, password)Description: Returns a signed JWT access token for authenticated client sessions.⚙️ Getting StartedPrerequisitesPython 3.10+PostgreSQL 14+Node.js 18+ & npmDocker & Docker Compose (for deployment)1. Backend Setup# Clone the repository
git clone https://github.com/your-username/cs2skintracker.git
cd cs2skintracker

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/cs2_db"
export SECRET_KEY="your-super-secret-jwt-key"

# Start the FastAPI server
uvicorn backend.main:app --reload --port 8000
2. Running Local Ingestion EngineTo seed or refresh the database with CSFloat market deals from your residential network:# Set your CSFloat API Key and DB connection string
export CSFLOAT_API_KEY="your_api_key_here"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/cs2_db"

# Execute scraper script
python backend/scrape.py
3. Frontend Setup# Navigate to frontend / root
npm install

# Start Vite development server
npm run dev
⚖️ Strategic Design DecisionsLocal Ingestion vs. EC2 Cloud Scraping: Direct scraping from Cloud infrastructure (AWS EC2) triggers Cloudflare 403 Forbidden blocks due to Data Center IP reputation. Running scrape.py locally bypasses IP bans cleanly while pushing structured data straight to PostgreSQL.FastAPI ASGI vs. Synchronous Flask: FastAPI's async event loop handles concurrent read requests efficiently on lightweight single-core EC2 instances without spawning excessive OS thread overhead.SQLAlchemy ORM vs. Raw SQL: SQLAlchemy abstracts query execution into clean, typed Python objects, neutralizes SQL injection vulnerabilities automatically via input parameterization, and integrates cleanly with FastAPI session injection (Depends(get_db)).📝 LicenseDistributed under the MIT License. See LICENSE for more information.
