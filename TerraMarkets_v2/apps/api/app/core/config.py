from __future__ import annotations

import json
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite+pysqlite:///./dev.db"
    SECRET_KEY: str = "CHANGE_ME"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 20
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    ALLOWED_ORIGINS: str = '["http://localhost:3000","http://127.0.0.1:3000"]'
    NASA_DONKI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    OPENAI_BOT_MODEL: str = "gpt-5.2"
    OPENAI_BOT_ENABLED: bool = False

    def model_post_init(self, __context) -> None:
        if self.DATABASE_URL == "sqlite+pysqlite:///./dev.db":
            self.DATABASE_URL = f"sqlite+pysqlite:///{API_DIR / 'dev.db'}"

    def allowed_origins_list(self) -> List[str]:
        try:
            return list(json.loads(self.ALLOWED_ORIGINS))
        except Exception:
            return ["http://localhost:3000"]


settings = Settings()
