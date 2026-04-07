from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DataSourceRun(Base):
    __tablename__ = "data_source_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_key: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DataPoint(Base):
    __tablename__ = "data_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_run_id: Mapped[int] = mapped_column(ForeignKey("data_source_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    source_key: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    series_key: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    numeric_value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=True)
    unit: Mapped[str] = mapped_column(String(64), nullable=True)
    observed_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DataFetchRequest(Base):
    __tablename__ = "data_fetch_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_key: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    requested_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    reviewed_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=True)
