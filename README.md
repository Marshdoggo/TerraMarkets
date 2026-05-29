# TerraMarkets

TerraMarkets is a conceptual prediction-market research and economic forecasting platform for Earth science, commodities, macroeconomic events, and other public-data-driven indicators. The project explores how market-implied probabilities, structured event modeling, and transparent data pipelines can help analysts reason about uncertain real-world outcomes without positioning the product as gambling, crypto speculation, or financial advice.

## Problem

Public datasets from agencies such as NOAA, NASA, USGS, and other scientific or economic sources are valuable but often hard to translate into decision-ready probability estimates. TerraMarkets prototypes an interface where datasets, model narratives, simulated participants, and market prices can be linked to show how evidence changes forecasts over time.

## Key Features

- Multi-outcome event markets with LMSR-style pricing and market-implied probabilities
- FastAPI backend with authentication, wallet-style demo balances, portfolio views, and admin market tooling
- Next.js frontend for markets, datasets, bot profiles, theses, and portfolio exploration
- Public-data ingestion pipelines for climate, geohazard, space-weather, and agricultural indicators
- Bot arena research layer for comparing forecast strategies and source-backed thesis generation
- Alembic migrations and local SQLite defaults, with a deployment path toward Postgres

## Tech Stack

- Frontend: Next.js, React, JavaScript, CSS
- Backend: Python, FastAPI, Pydantic, SQLAlchemy, Alembic
- Data: Public science and economic data pipelines, normalized observations, citation metadata
- Testing: Pytest for API, ingestion, and forecasting workflow coverage
- Infrastructure: Docker Compose examples, Vercel-oriented frontend, Render/Railway-style API deployment notes

## Current Status

This is a portfolio-ready research/product prototype. The active application lives in `TerraMarkets_v2/`; older root-level scratch folders are intentionally ignored. The current implementation is designed for local demonstration and research workflows, not production trading, regulated financial activity, or real-money use.

## Project Structure

```text
TerraMarkets_v2/
  apps/api/       FastAPI service, SQLAlchemy models, Alembic migrations, ingestion pipelines, tests
  apps/web/       Next.js application and reusable UI components
  docs/           Architecture, deployment, migration, and portfolio notes
  infra/compose/  Local Docker Compose examples
  scripts/        Bootstrap, seeding, and demo reset helpers
```

The repository would be cleaner long term if `TerraMarkets_v2/` were promoted to the root application directory. For now, the structure is documented explicitly to avoid a risky refactor before publishing.

## Local Setup

From the repository root:

```bash
cd TerraMarkets_v2
./scripts/bootstrap.sh
```

Run the API:

```bash
cd TerraMarkets_v2/apps/api
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload
```

Run the web app in a second terminal:

```bash
cd TerraMarkets_v2/apps/web
npm run dev
```

The web app expects the API at `http://localhost:8000` unless `NEXT_PUBLIC_API_BASE_URL` is set.

## Environment Variables

Copy the example files before running locally:

```bash
cp TerraMarkets_v2/apps/api/.env.example TerraMarkets_v2/apps/api/.env
cp TerraMarkets_v2/apps/web/.env.local.example TerraMarkets_v2/apps/web/.env.local
```

Important backend variables:

- `DATABASE_URL`: defaults to local SQLite for development
- `SECRET_KEY`: replace the example value for any shared or deployed environment
- `NASA_DONKI_API_KEY`: optional API key for NASA DONKI solar flare ingestion
- `OPENAI_API_KEY`: optional key for bot reasoning and thesis generation
- `OPENAI_BOT_ENABLED`, `OPENAI_BOT_THESIS_ENABLED`, `OPENAI_BOT_SEARCH_ENABLED`: optional research-layer feature flags

Local `.env` files, SQLite databases, virtual environments, build output, and dependency folders are ignored by git.

## Suggested Screenshots

- Market detail page showing event probabilities and linked evidence
- Data Lab page showing normalized public datasets and citations
- Bot arena page showing forecast strategy profiles and theses
- Portfolio page showing simulated positions and market exposure
- Admin/demo seeding flow for local market setup

## Roadmap

- Promote the active v2 workspace to the repository root after publication planning
- Add production-ready Postgres configuration and migration runbooks
- Expand public-data connectors for commodities, macro indicators, and climate risk
- Add model evaluation metrics for forecast calibration and thesis quality
- Improve screenshot/demo fixtures for portfolio presentation
- Harden authentication/session handling before any public multi-user deployment

## Portfolio Framing

TerraMarkets demonstrates full-stack product engineering, data ingestion design, probabilistic event modeling, and financial/economic forecasting concepts. It is best presented as a research prototype for turning public datasets into explainable probability estimates and analyst-facing forecasting workflows.
