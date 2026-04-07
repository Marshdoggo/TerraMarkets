# Architecture

## Backend

The API is a modular FastAPI service split across routers, schemas, services, and SQLAlchemy models.

- Auth uses short-lived access tokens plus rotating refresh tokens.
- Users have a single Terracoin wallet and a ledger trail.
- Markets support multiple outcomes and use LMSR pricing.
- Orders track purchases and positions track settled holdings.

## Frontend

The web app is a minimal Next.js pages-router client.

- API calls go through a shared client in `src/lib/api.js`.
- Auth tokens are stored in `localStorage`.
- The UI provides login, registration, market browsing, buying, wallet view, and admin tools.

## Data Store

Local development uses SQLite by default. The backend can switch to Postgres by changing `DATABASE_URL`.
