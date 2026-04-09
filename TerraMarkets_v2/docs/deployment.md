# TerraMarkets Deployment Notes

## Recommended shape

- Next.js frontend on Vercel
- FastAPI API on Render or Railway
- Managed Postgres for production state

## Required production env vars

### API

- `DATABASE_URL`
- `SECRET_KEY`
- `ALLOWED_ORIGINS`
- `NASA_DONKI_API_KEY` if solar flare fetching is enabled
- `OPENAI_API_KEY` if bot reasoning or thesis writing is enabled
- `OPENAI_BOT_ENABLED`
- `OPENAI_BOT_THESIS_ENABLED`
- `OPENAI_BOT_SEARCH_ENABLED`
- `OPENAI_BOT_MODEL`
- `OPENAI_BOT_THESIS_MODEL`
- `OPENAI_BOT_SEARCH_MODEL`
- `OPENAI_BOT_SEARCH_ALLOWED_DOMAINS`

### Web

- `NEXT_PUBLIC_API_BASE_URL`

## Launch checklist

1. Point `DATABASE_URL` at Postgres and run Alembic migrations.
2. Set CORS origins for the production web domain.
3. Seed the admin user, demo markets, and default bots from the API service.
4. Refresh all datasets once after deploy.
5. Verify public pages:
   - `/markets`
   - `/datasets`
   - `/bots`
   - `/theses`
6. Verify admin-only flows remain protected:
   - `/admin`
   - `/data/fetch/all`
   - `/markets/seed/demo`
   - `/bots/run-cycle`

## First public mode

Keep the first public domain watch-only:

- no public deposits
- no user trading
- no public comments
- focus on observability, datasets, and bot research
