from __future__ import annotations

from sqlalchemy import delete

from app.core.db import SessionLocal
from app.models.auth import RefreshToken
from app.models.data import DataPoint, DataSourceRun
from app.models.market import Market
from app.models.market_snapshot import MarketSnapshot
from app.models.order import Order
from app.models.position import Position
from app.models.wallet import LedgerEntry


def main():
    db = SessionLocal()
    try:
        db.execute(delete(DataPoint))
        db.execute(delete(DataSourceRun))
        db.execute(delete(MarketSnapshot))
        db.execute(delete(Order))
        db.execute(delete(Position))
        db.execute(delete(Market))
        db.execute(delete(LedgerEntry))
        db.execute(delete(RefreshToken))
        db.commit()
        print("Cleared demo trading data, snapshots, source runs, and refresh tokens.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
