from __future__ import annotations

from pydantic import BaseModel


class WalletOut(BaseModel):
    balance: float


class LedgerEntryOut(BaseModel):
    id: int
    amount: float
    memo: str
    created_at: str


class WalletDetailOut(WalletOut):
    entries: list[LedgerEntryOut]


class MintIn(BaseModel):
    user_id: int
    amount: float
    memo: str = "Admin mint"


class DemoPurchaseIn(BaseModel):
    amount: float
    memo: str = "Demo Terracoin purchase"


class PurchaseRequestIn(BaseModel):
    amount: float
    note: str = "Terracoin purchase request"


class PurchaseRequestOut(BaseModel):
    id: int
    user_id: int
    amount: float
    status: str
    note: str | None = None
    approved_by_user_id: int | None = None
    created_at: str
    reviewed_at: str | None = None


class AdminUserWalletOut(BaseModel):
    user_id: int
    email: str
    tier: str
    wallet_balance: float
