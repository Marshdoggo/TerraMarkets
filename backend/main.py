# backend/main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from uuid import uuid4
from datetime import datetime, timedelta
from typing import List, Optional

from .security import hash_password
from .auth import create_access_token, get_current_user

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:3000",  # Next.js dev server
    # "https://your-domain.com", # Add if/when you deploy
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # or ["*"] for local dev (less secure)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Database Setup ----------
from .database import Base, SessionLocal, engine, UserDB, get_db
...

# ---------- Database Setup ----------
from .database import Base, SessionLocal, engine, UserDB, get_db

# ---------- Models ----------

class MarketDB(Base):
    __tablename__ = "markets"
    id = Column(String, primary_key=True, index=True)
    question = Column(String)
    expires_at = Column(DateTime)
    total_yes = Column(Float, default=0.0)
    total_no = Column(Float, default=0.0)
    resolved = Column(Boolean, default=False)
    outcome = Column(Boolean, nullable=True)

class BetDB(Base):
    __tablename__ = "bets"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String)
    market_id = Column(String)
    amount = Column(Float)
    direction = Column(Boolean)  # True = Yes, False = No

Base.metadata.create_all(bind=engine)

# ---------- Schemas ----------
class User(BaseModel):
    id: str
    username: str
    balance: float
    class Config:
        orm_mode = True

class Market(BaseModel):
    id: str
    question: str
    expires_at: datetime
    total_yes: float
    total_no: float
    resolved: bool
    outcome: Optional[bool]
    class Config:
        from_attributes = True

class Bet(BaseModel):
    user_id: str
    market_id: str
    amount: float
    direction: bool

# ---------- Dependency ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- API Endpoints ----------
@app.post("/register", response_model=User)
def register_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user_id = str(uuid4())
    hashed_pw = hash_password(form_data.password)
    user = UserDB(id=user_id, username=form_data.username, password=hashed_pw)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    from .auth import authenticate_user
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=User)
def read_users_me(current_user: UserDB = Depends(get_current_user)):
    return current_user

@app.post("/markets", response_model=Market)
def create_market(question: str, duration_minutes: int = 60, db: Session = Depends(get_db)):
    market_id = str(uuid4())
    expires = datetime.utcnow() + timedelta(minutes=duration_minutes)
    market = MarketDB(id=market_id, question=question, expires_at=expires)
    db.add(market)
    db.commit()
    db.refresh(market)
    return market

@app.get("/markets", response_model=List[Market])
def list_markets(db: Session = Depends(get_db)):
    return db.query(MarketDB).all()

@app.post("/bet")
def place_bet(bet: Bet, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == bet.user_id).first()
    market = db.query(MarketDB).filter(MarketDB.id == bet.market_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    if market.resolved or market.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Market closed")
    if bet.amount > user.balance:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    user.balance -= bet.amount
    if bet.direction:
        market.total_yes += bet.amount
    else:
        market.total_no += bet.amount

    bet_entry = BetDB(id=str(uuid4()), **bet.dict())
    db.add(bet_entry)
    db.commit()
    return {"message": "Bet placed"}

@app.post("/resolve/{market_id}")
def resolve_market(market_id: str, outcome: bool, db: Session = Depends(get_db)):
    market = db.query(MarketDB).filter(MarketDB.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    if market.resolved:
        raise HTTPException(status_code=400, detail="Market already resolved")
    if market.expires_at > datetime.utcnow():
        raise HTTPException(status_code=400, detail="Market not yet expired")

    market.resolved = True
    market.outcome = outcome
    db.commit()

    # Payouts
    bets = db.query(BetDB).filter(BetDB.market_id == market_id, BetDB.direction == outcome).all()
    total_pool = market.total_yes + market.total_no
    winning_pool = market.total_yes if outcome else market.total_no

    for bet in bets:
        user = db.query(UserDB).filter(UserDB.id == bet.user_id).first()
        share = bet.amount / winning_pool
        payout = round(share * total_pool, 2)
        user.balance += payout

    db.commit()
    return {"message": "Market resolved"}
