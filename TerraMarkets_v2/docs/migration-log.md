# Migration Log

## Ported

- Modular backend from the untracked `terramarkets_backend` rewrite
- Core LMSR pricing service
- Alembic initial migration
- Admin seed script

## Rebuilt

- Frontend API integration against `/auth`, `/wallet`, and `/markets`
- Market detail page
- Shared API client and auth helpers
- Terracoin signup funding and wallet copy

## Deferred

- Smart contract integration
- ETL and oracle implementation beyond scaffolding
- Automated test coverage beyond the initial backend smoke file
