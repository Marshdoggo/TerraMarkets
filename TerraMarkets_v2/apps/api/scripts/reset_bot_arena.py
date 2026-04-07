from __future__ import annotations

from app.core.db import SessionLocal
from app.services.bot_service import reset_arena_state


def main():
    db = SessionLocal()
    try:
        reset_arena_state(db)
        db.commit()
        print("Reset bot arena markets, bot runs, and bot users.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
