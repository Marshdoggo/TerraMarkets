from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.auth import router as auth_router
from app.api.routers.bots import router as bots_router
from app.api.routers.data import router as data_router
from app.api.routers.markets import router as markets_router
from app.api.routers.portfolio import router as portfolio_router
from app.api.routers.wallet import router as wallet_router
from app.core.config import settings

app = FastAPI(title="TerraMarkets API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list(),
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(wallet_router)
app.include_router(markets_router)
app.include_router(portfolio_router)
app.include_router(data_router)
app.include_router(bots_router)


@app.get("/health")
def health():
    return {"status": "ok"}
