from __future__ import annotations

import enum


class UserTier(str, enum.Enum):
    free = "free"
    pro = "pro"
    admin = "admin"


class MarketStatus(str, enum.Enum):
    open = "open"
    closed = "closed"
    resolved = "resolved"
    cancelled = "cancelled"


class BotStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    archived = "archived"
