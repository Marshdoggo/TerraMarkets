from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_token
from app.models.enums import UserTier
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = decode_token(token)
        if payload.get("typ") != "access":
            raise ValueError("Not access token")
        user_id = int(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_tier(min_tier: UserTier):
    order = {UserTier.free: 0, UserTier.pro: 1, UserTier.admin: 2}

    def _inner(user: User = Depends(get_current_user)) -> User:
        if order[user.tier] < order[min_tier]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return _inner

