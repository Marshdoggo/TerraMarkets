from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.enums import UserTier
from app.models.user import User
from app.models.wallet import LedgerEntry
from app.services.auth_service import register_user

ADMIN_EMAIL = "admin@terramarkets.dev"
ADMIN_PASSWORD = "adminpass"
MINT = 1000


def main():
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if not user:
            user = register_user(db, ADMIN_EMAIL, ADMIN_PASSWORD)
            user.tier = UserTier.admin
            db.flush()
            print("Created admin:", user.email, "id=", user.id)
        else:
            print("Admin already exists:", user.email, "id=", user.id)
            user.tier = UserTier.admin

        wallet = user.wallet
        mint_amount = Decimal(str(MINT))
        wallet.balance = Decimal(wallet.balance) + mint_amount
        db.add(LedgerEntry(wallet_id=wallet.id, amount=mint_amount, memo="Seed mint"))
        db.commit()
        print("Minted", MINT, "Terracoin. Balance:", float(wallet.balance))
    finally:
        db.close()


if __name__ == "__main__":
    main()
