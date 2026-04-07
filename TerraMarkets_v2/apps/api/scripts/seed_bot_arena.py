from __future__ import annotations

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.market import Market
from app.services.bot_service import seed_default_bots


def main():
    db = SessionLocal()
    try:
        bots = seed_default_bots(db)
        db.commit()
        market_count = len(db.scalars(select(Market)).all())
        print(f"Seeded {len(bots)} bots across {market_count} markets.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
