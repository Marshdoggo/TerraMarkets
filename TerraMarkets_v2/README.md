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
