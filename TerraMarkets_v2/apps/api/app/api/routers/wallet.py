from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_tier
from app.core.db import get_db
from app.models.enums import UserTier
from app.models.purchase_request import PurchaseRequest
from app.models.user import User
from app.models.wallet import LedgerEntry, Wallet
from app.schemas.wallet import (
    AdminUserWalletOut,
    DemoPurchaseIn,
    LedgerEntryOut,
    MintIn,
    PurchaseRequestIn,
    PurchaseRequestOut,
    WalletDetailOut,
    WalletOut,
)

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("", response_model=WalletOut)
def get_wallet(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = db.scalar(select(Wallet).where(Wallet.user_id == user.id))
    return WalletOut(balance=float(wallet.balance))


@router.get("/detail", response_model=WalletDetailOut)
def get_wallet_detail(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = db.scalar(select(Wallet).where(Wallet.user_id == user.id))
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    entries = db.scalars(select(LedgerEntry).where(LedgerEntry.wallet_id == wallet.id).order_by(LedgerEntry.id.desc()).limit(100)).all()
    return WalletDetailOut(
        balance=float(wallet.balance),
        entries=[
            LedgerEntryOut(id=entry.id, amount=float(entry.amount), memo=entry.memo, created_at=str(entry.created_at))
            for entry in entries
        ],
    )


@router.post("/mint", response_model=WalletOut)
def mint(payload: MintIn, admin: User = Depends(require_tier(UserTier.admin)), db: Session = Depends(get_db)):
    wallet = db.scalar(select(Wallet).where(Wallet.user_id == payload.user_id).with_for_update())
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    amount = Decimal(str(payload.amount))
    wallet.balance = Decimal(wallet.balance) + amount
    db.add(LedgerEntry(wallet_id=wallet.id, amount=amount, memo=payload.memo))
    db.commit()
    return WalletOut(balance=float(wallet.balance))


@router.post("/purchase-requests", response_model=PurchaseRequestOut)
def create_purchase_request(
    payload: PurchaseRequestIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    purchase_request = PurchaseRequest(user_id=user.id, amount=Decimal(str(payload.amount)), status="pending", note=payload.note)
    db.add(purchase_request)
    db.commit()
    db.refresh(purchase_request)
    return PurchaseRequestOut(
        id=purchase_request.id,
        user_id=purchase_request.user_id,
        amount=float(purchase_request.amount),
        status=purchase_request.status,
        note=purchase_request.note,
        approved_by_user_id=purchase_request.approved_by_user_id,
        created_at=str(purchase_request.created_at),
        reviewed_at=str(purchase_request.reviewed_at) if purchase_request.reviewed_at else None,
    )


@router.get("/purchase-requests", response_model=list[PurchaseRequestOut])
def list_purchase_requests(
    admin: User = Depends(require_tier(UserTier.admin)),
    db: Session = Depends(get_db),
):
    requests = db.scalars(select(PurchaseRequest).order_by(PurchaseRequest.id.desc())).all()
    return [
        PurchaseRequestOut(
            id=request.id,
            user_id=request.user_id,
            amount=float(request.amount),
            status=request.status,
            note=request.note,
            approved_by_user_id=request.approved_by_user_id,
            created_at=str(request.created_at),
            reviewed_at=str(request.reviewed_at) if request.reviewed_at else None,
        )
        for request in requests
    ]


@router.post("/purchase-requests/{request_id}/approve", response_model=PurchaseRequestOut)
def approve_purchase_request(
    request_id: int,
    admin: User = Depends(require_tier(UserTier.admin)),
    db: Session = Depends(get_db),
):
    purchase_request = db.scalar(select(PurchaseRequest).where(PurchaseRequest.id == request_id).with_for_update())
    if not purchase_request:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    if purchase_request.status != "pending":
        raise HTTPException(status_code=400, detail="Purchase request already processed")

    wallet = db.scalar(select(Wallet).where(Wallet.user_id == purchase_request.user_id).with_for_update())
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    amount = Decimal(purchase_request.amount)
    wallet.balance = Decimal(wallet.balance) + amount
    db.add(LedgerEntry(wallet_id=wallet.id, amount=amount, memo=f"Approved purchase request #{purchase_request.id}"))
    purchase_request.status = "approved"
    purchase_request.approved_by_user_id = admin.id
    purchase_request.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(purchase_request)

    return PurchaseRequestOut(
        id=purchase_request.id,
        user_id=purchase_request.user_id,
        amount=float(purchase_request.amount),
        status=purchase_request.status,
        note=purchase_request.note,
        approved_by_user_id=purchase_request.approved_by_user_id,
        created_at=str(purchase_request.created_at),
        reviewed_at=str(purchase_request.reviewed_at) if purchase_request.reviewed_at else None,
    )


@router.post("/demo-purchase", response_model=WalletOut)
def demo_purchase(payload: DemoPurchaseIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = db.scalar(select(Wallet).where(Wallet.user_id == user.id).with_for_update())
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    amount = Decimal(str(payload.amount))
    wallet.balance = Decimal(wallet.balance) + amount
    db.add(LedgerEntry(wallet_id=wallet.id, amount=amount, memo=payload.memo))
    db.commit()
    return WalletOut(balance=float(wallet.balance))


@router.get("/admin/users", response_model=list[AdminUserWalletOut])
def list_admin_users(admin: User = Depends(require_tier(UserTier.admin)), db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.id.asc())).all()
    wallets = {
        wallet.user_id: wallet
        for wallet in db.scalars(select(Wallet)).all()
    }
    return [
        AdminUserWalletOut(
            user_id=user.id,
            email=user.email,
            tier=user.tier.value,
            wallet_balance=float(wallets[user.id].balance) if user.id in wallets else 0.0,
        )
        for user in users
    ]
