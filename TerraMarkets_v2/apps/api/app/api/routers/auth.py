from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.security import decode_token
from app.models.user import User
from app.schemas.auth import LoginIn, MeOut, RegisterIn, TokenOut
from app.services.auth_service import authenticate, issue_tokens, register_user, revoke_all_refresh_tokens, rotate_refresh

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=MeOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    try:
        user = register_user(db, payload.email, payload.password)
        db.commit()
        return MeOut(id=user.id, email=user.email, tier=user.tier.value)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    try:
        user = authenticate(db, payload.email, payload.password)
        access, refresh = issue_tokens(db, user)
        db.commit()
        return TokenOut(access_token=access, refresh_token=refresh)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/refresh", response_model=TokenOut)
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = decode_token(refresh_token)
        if payload.get("typ") != "refresh":
            raise ValueError("Not refresh token.")
        user_id = int(payload["sub"])
        presented_raw = payload.get("rt")
        if not presented_raw:
            raise ValueError("Malformed refresh token.")
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            raise ValueError("User not found.")
        rotate_refresh(db, user=user, presented_raw=presented_raw)
        access, new_refresh = issue_tokens(db, user)
        db.commit()
        return TokenOut(access_token=access, refresh_token=new_refresh)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=401, detail="Refresh failed") from exc


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)):
    return MeOut(id=user.id, email=user.email, tier=user.tier.value)


@router.post("/logout", status_code=204)
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    revoke_all_refresh_tokens(db, user=user)
    db.commit()
    return Response(status_code=204)
