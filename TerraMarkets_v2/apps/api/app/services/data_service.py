from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.data import DataPoint, DataSourceRun


def _coerce_observed_at(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    raise TypeError("observed_at must be a datetime or ISO datetime string")


def ingest_data_run(db: Session, *, source_key: str, summary: str | None, payload: dict | None, points: list[dict]) -> DataSourceRun:
    run = DataSourceRun(source_key=source_key, status="success", summary=summary, payload=payload or {})
    db.add(run)
    db.flush()

    inserted_points = 0
    seen_in_batch: set[tuple[str, str]] = set()
    for point in points:
        observed_at = _coerce_observed_at(point["observed_at"])
        batch_key = (point["series_key"], observed_at.isoformat())
        if batch_key in seen_in_batch:
            continue
        seen_in_batch.add(batch_key)
        existing = db.scalar(
            select(DataPoint).where(
                DataPoint.source_key == source_key,
                DataPoint.series_key == point["series_key"],
                DataPoint.observed_at == observed_at,
            )
        )
        if existing:
            continue
        db.add(
            DataPoint(
                source_run_id=run.id,
                source_key=source_key,
                series_key=point["series_key"],
                label=point["label"],
                numeric_value=Decimal(str(point["numeric_value"])) if point.get("numeric_value") is not None else None,
                unit=point.get("unit"),
                observed_at=observed_at,
                metadata_json=point.get("metadata_json") or {},
            )
        )
        inserted_points += 1

    run.payload = {
        **(run.payload or {}),
        "points_received": len(points),
        "points_inserted": inserted_points,
    }

    return run


def list_data_runs(db: Session, source_key: str | None = None, limit: int = 500) -> list[DataSourceRun]:
    query = select(DataSourceRun).order_by(DataSourceRun.id.desc()).limit(limit)
    if source_key:
        query = select(DataSourceRun).where(DataSourceRun.source_key == source_key).order_by(DataSourceRun.id.desc()).limit(limit)
    return db.scalars(query).all()


def list_points_for_run(db: Session, run_id: int) -> list[DataPoint]:
    return db.scalars(select(DataPoint).where(DataPoint.source_run_id == run_id).order_by(DataPoint.observed_at.desc())).all()


def get_latest_point_for_series(db: Session, *, source_key: str, series_key: str) -> DataPoint | None:
    query = (
        select(DataPoint)
        .where(DataPoint.source_key == source_key, DataPoint.series_key == series_key)
        .order_by(DataPoint.observed_at.desc(), DataPoint.id.desc())
        .limit(1)
    )
    return db.scalar(query)


def list_recent_points_for_series(db: Session, *, source_key: str, series_key: str, limit: int = 30) -> list[DataPoint]:
    query = (
        select(DataPoint)
        .where(DataPoint.source_key == source_key, DataPoint.series_key == series_key)
        .order_by(DataPoint.observed_at.desc(), DataPoint.id.desc())
        .limit(limit)
    )
    return list(reversed(db.scalars(query).all()))
