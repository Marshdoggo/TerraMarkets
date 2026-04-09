# TerraMarkets_v2

Clean v2 workspace for TerraMarkets.

## Layout

- `apps/api`: FastAPI backend with Alembic migrations, wallet ledger, LMSR trading, and auth
- `apps/web`: Next.js frontend wired to the v2 API contract
- `docs`: architecture and migration notes
- `infra`: local compose setup
- `scripts`: helper scripts

## Backend

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

The backend defaults to SQLite for local development at `apps/api/dev.db`.
That file is your persistent local app state: users, wallets, markets, bot arena state, and stored data runs live there until you delete the DB or run a reset script.

## Frontend

```bash
cd apps/web
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` if the API is not running on `http://localhost:8000`.

## Current Scope

This v2 keeps the product off-chain for now:

- email/password auth
- access and refresh tokens
- Terracoin wallet balances with signup funding and admin minting
- multi-outcome markets
- LMSR pricing and share purchases
- admin resolution and settlement

Terracoin is treated as a non-redeemable in-app balance for local MVP use.
Smart contracts were intentionally not ported into the active v2 path yet.

## Observatory Expansion

The active v2 workspace now includes:

- a watch-only public bot observatory
- expanded science pipelines spanning cryosphere and geohazards
- structured bot citations for stored datasets and curated official web sources
- a larger bot arena with distinct strategy types

Key local env flags for the research layer:

```bash
OPENAI_BOT_ENABLED=true
OPENAI_BOT_THESIS_ENABLED=true
OPENAI_BOT_SEARCH_ENABLED=true
OPENAI_BOT_SEARCH_ALLOWED_DOMAINS=["nsidc.org","volcano.si.edu","usgs.gov","earthquake.usgs.gov","swpc.noaa.gov","nhc.noaa.gov","cpc.ncep.noaa.gov","noaa.gov","nasa.gov"]
```

## Deployment

Recommended first public deployment:

- frontend on Vercel
- API on Render or Railway
- managed Postgres for `DATABASE_URL`

The first public release should stay watch-only:

- public markets, datasets, bot profiles, leaderboards, and theses
- admin-only bot controls, market creation, seeding, and data refresh

See `docs/deployment.md` for the production setup checklist.
