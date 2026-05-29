# TerraMarkets

TerraMarkets is the active full-stack workspace for a prediction-market research and economic forecasting prototype. It focuses on Earth science, commodities, macroeconomic events, and public-data-driven probability markets, with an emphasis on explainable event modeling rather than real-money trading.

## Layout

- `apps/api`: FastAPI backend with auth, market APIs, data ingestion, bot arena services, Alembic migrations, and tests
- `apps/web`: Next.js frontend for markets, datasets, bot profiles, theses, and portfolio views
- `docs`: architecture, deployment, migration, and portfolio documentation
- `infra/compose`: local Docker Compose examples
- `scripts`: bootstrap, reset, seed, and demo helpers

## Backend

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

The backend defaults to SQLite at `apps/api/dev.db` for local development. That file stores local users, demo balances, markets, bot arena state, and data runs; it is intentionally ignored by git.

## Frontend

```bash
cd apps/web
npm install
cp .env.local.example .env.local
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` if the API is not running on `http://localhost:8000`.

## Environment

Backend configuration is documented in `apps/api/.env.example`. Key variables include:

- `DATABASE_URL`
- `SECRET_KEY`
- `NASA_DONKI_API_KEY`
- `OPENAI_API_KEY`
- `OPENAI_BOT_ENABLED`
- `OPENAI_BOT_THESIS_ENABLED`
- `OPENAI_BOT_SEARCH_ENABLED`

The OpenAI and NASA keys are optional for local demos unless those ingestion or research-agent features are enabled.

## Current Scope

The prototype includes:

- email/password auth and token-based sessions
- non-redeemable demo balances for local portfolio simulation
- multi-outcome event markets
- LMSR-style automated pricing
- admin market seeding, resolution, and settlement workflows
- public-data ingestion pipelines with citation-oriented metadata
- a watch-only bot arena for comparing forecast strategies and thesis quality

This project is not a production trading venue, gambling product, investment service, or financial advice tool.

## Verification

```bash
cd apps/api
source .venv/bin/activate
python -m pytest -q
```

```bash
cd apps/web
npm run build
```

## Deployment Notes

Recommended first public deployment:

- frontend on Vercel
- API on Render, Railway, or a comparable Python hosting platform
- managed Postgres for `DATABASE_URL`

The first public release should remain watch-only: markets, datasets, bot profiles, leaderboards, and theses can be visible while admin-only market creation, bot controls, seeding, and data refresh stay protected.

See `docs/deployment.md` for the production setup checklist and `docs/PORTFOLIO_SUMMARY.md` for resume-friendly positioning.
