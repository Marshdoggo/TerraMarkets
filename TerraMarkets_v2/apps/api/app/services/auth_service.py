from __future__ import annotations

import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_token, hash_password, pwd_context, verify_password
from app.models.auth import RefreshToken
from app.models.user import User
from app.models.wallet import Wallet

SIGNUP_BONUS_TERRACOIN = 1000


def register_user(db: Session, email: str, password: str) -> User:
    email = email.lower().strip()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise ValueError("Email already registered.")
    user = User(email=email, password_hash=hash_password(password))
    user.wallet = Wallet(balance=SIGNUP_BONUS_TERRACOIN)
    db.add(user)
    db.flush()
    return user


def _hash_refresh(raw: str) -> str:
    return pwd_context.hash(raw)


def _verify_refresh(raw: str, hashed: str) -> bool:
    return pwd_context.verify(raw, hashed)


def issue_tokens(db: Session, user: User) -> tuple[str, str]:
    access = create_token(
        subject=str(user.id),
        token_type="access",
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra={"tier": user.tier.value},
    )
    raw_refresh = secrets.token_urlsafe(48)
    refresh_jwt = create_token(
        subject=str(user.id),
        token_type="refresh",
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        extra={"rt": raw_refresh},
    )
    db.add(RefreshToken(user_id=user.id, token_hash=_hash_refresh(raw_refresh)))
    return access, refresh_jwt


def authenticate(db: Session, email: str, password: str) -> User:
    email = email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("Invalid credentials.")
    return user


def rotate_refresh(db: Session, *, user: User, presented_raw: str) -> None:
    tokens = db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.is_revoked == False)
    ).all()
    matched = None
    for token in tokens:
        if _verify_refresh(presented_raw, token.token_hash):
            matched = token
            break
    if not matched:
        raise ValueError("Refresh token not recognized.")
    matched.is_revoked = True


def revoke_all_refresh_tokens(db: Session, *, user: User) -> None:
    tokens = db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.is_revoked == False)).all()
    for token in tokens:
        token.is_revoked = True
