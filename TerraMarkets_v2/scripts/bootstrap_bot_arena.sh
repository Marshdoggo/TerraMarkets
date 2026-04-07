#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d apps/api/.venv ]; then
  python3 -m venv apps/api/.venv
fi

source apps/api/.venv/bin/activate
pip install -r apps/api/requirements.txt

export DATABASE_URL="${DATABASE_URL:-sqlite+pysqlite:///./bot_arena.db}"

cd apps/api
alembic upgrade head
python scripts/reset_bot_arena.py
python scripts/seed_admin.py
python scripts/seed_demo_markets.py
python scripts/seed_bot_arena.py

cd ../web
npm install

cat <<'EOF'
Bot Arena bootstrapped.
Suggested runtime:
  API: DATABASE_URL=sqlite+pysqlite:///./bot_arena.db uvicorn app.main:app --host 127.0.0.1 --port 8100
  Web: NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8100 npm run dev -- --port 3100
EOF
