# TerraMarkets

The active TerraMarkets product lives in `TerraMarkets_v2`.

## Start Here

- Product workspace: `TerraMarkets_v2/`
- Backend: `TerraMarkets_v2/apps/api`
- Frontend: `TerraMarkets_v2/apps/web`

## Local Bootstrap

```bash
cd TerraMarkets_v2
./scripts/bootstrap.sh
```

## Local Verification

```bash
cd TerraMarkets_v2/apps/api
source .venv/bin/activate
python -m pytest -q
uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd TerraMarkets_v2/apps/web
npm run build
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` if the API is not running on `http://localhost:8000`.
