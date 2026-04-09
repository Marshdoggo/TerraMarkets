from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_tier
from app.core.db import get_db
from app.ingestion.pipelines.smithsonian_volcanoes import fetch_smithsonian_weekly_history
from app.models.data import DataFetchRequest, DataPoint, DataSourceRun
from app.models.enums import UserTier
from app.models.user import User
from app.schemas.data import (
    DataFetchAllItemOut,
    DataFetchAllOut,
    DataFetchRequestIn,
    DataFetchRequestOut,
    DataIngestIn,
    DataPointOut,
    DataRunOut,
    DonkiSolarFlareFetchIn,
    EnsoOniFetchIn,
    NsidcAntarcticFetchIn,
    NsidcCharcticFetchIn,
    OpenMeteoFetchIn,
    SmithsonianVolcanoBackfillIn,
    SmithsonianVolcanoFetchIn,
    UsgsEarthquakeFetchIn,
)
from app.ingestion.registry import PIPELINE_REGISTRY, get_pipeline
from app.ingestion.storage import ingest_pipeline_result
from app.oracles.nsidc_charctic import fetch_nsidc_antarctic_daily, fetch_nsidc_charctic_daily
from app.services.bot_service import run_event_driven_for_source
from app.services.fetchers import fetch_open_meteo_current
from app.services.data_service import ingest_data_run, list_data_runs, list_points_for_run

router = APIRouter(prefix="/data", tags=["data"])


def serialize_data_run(db: Session, run) -> DataRunOut:
    points = list_points_for_run(db, run.id)
    return DataRunOut(
        id=run.id,
        source_key=run.source_key,
        status=run.status,
        summary=run.summary,
        created_at=str(run.created_at),
        points=[
            DataPointOut(
                id=point.id,
                source_key=point.source_key,
                series_key=point.series_key,
                label=point.label,
                numeric_value=float(point.numeric_value) if point.numeric_value is not None else None,
                unit=point.unit,
                observed_at=str(point.observed_at),
                metadata_json=point.metadata_json,
            )
            for point in points
        ],
    )


def serialize_fetch_request(request: DataFetchRequest, requested_by_email: str | None = None) -> DataFetchRequestOut:
    return DataFetchRequestOut(
        id=request.id,
        source_key=request.source_key,
        label=request.label,
        note=request.note,
        status=request.status,
        requested_by_user_id=request.requested_by_user_id,
        requested_by_email=requested_by_email,
        reviewed_by_user_id=request.reviewed_by_user_id,
        created_at=str(request.created_at),
        reviewed_at=str(request.reviewed_at) if request.reviewed_at else None,
    )


def fulfill_pending_fetch_requests(db: Session, *, source_key: str, admin_id: int):
    pending_requests = db.scalars(
        select(DataFetchRequest)
        .where(DataFetchRequest.source_key == source_key, DataFetchRequest.status == "pending")
        .order_by(DataFetchRequest.id.asc())
    ).all()
    for request in pending_requests:
        request.status = "fulfilled"
        request.reviewed_by_user_id = admin_id
        request.reviewed_at = datetime.now(timezone.utc)


@router.post("/fetch-requests", response_model=DataFetchRequestOut)
def create_fetch_request(
    payload: DataFetchRequestIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    request = DataFetchRequest(
        source_key=payload.source_key,
        label=payload.label,
        note=payload.note,
        status="pending",
        requested_by_user_id=user.id,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return serialize_fetch_request(request, requested_by_email=user.email)


@router.get("/fetch-requests", response_model=list[DataFetchRequestOut])
def list_fetch_requests(
    admin: User = Depends(require_tier(UserTier.admin)),
    db: Session = Depends(get_db),
):
    requests = db.scalars(select(DataFetchRequest).order_by(DataFetchRequest.id.desc())).all()
    users = {user.id: user.email for user in db.scalars(select(User)).all()}
    return [serialize_fetch_request(request, requested_by_email=users.get(request.requested_by_user_id)) for request in requests]


@router.post("/ingest", response_model=DataRunOut)
def ingest_data(
    payload: DataIngestIn,
    db: Session = Depends(get_db),
    admin=Depends(require_tier(UserTier.admin)),
):
    run = ingest_data_run(
        db,
        source_key=payload.source_key,
        summary=payload.summary,
        payload=payload.payload,
        points=[point.model_dump() for point in payload.points],
    )
    db.commit()
    run_event_driven_for_source(payload.source_key)
    return serialize_data_run(db, run)


@router.get("/runs", response_model=list[DataRunOut])
def get_runs(source_key: str | None = None, db: Session = Depends(get_db)):
    runs = list_data_runs(db, source_key=source_key)
    payload = []
    for run in runs:
        points = list_points_for_run(db, run.id)
        payload.append(
            DataRunOut(
                id=run.id,
                source_key=run.source_key,
                status=run.status,
                summary=run.summary,
                created_at=str(run.created_at),
                points=[
                    DataPointOut(
                        id=point.id,
                        source_key=point.source_key,
                        series_key=point.series_key,
                        label=point.label,
                        numeric_value=float(point.numeric_value) if point.numeric_value is not None else None,
                        unit=point.unit,
                        observed_at=str(point.observed_at),
                        metadata_json=point.metadata_json,
                    )
                    for point in points
                ],
            )
        )
    return payload


@router.get("/pipelines")
def get_pipelines():
    pipelines = [
        {"source_key": "nsidc_charctic_daily", "label": "NSIDC Arctic Sea Ice"},
    ]
    pipelines.extend(
        {"source_key": source_key, "label": pipeline.label}
        for source_key, pipeline in PIPELINE_REGISTRY.items()
    )
    return pipelines


@router.post("/fetch/open-meteo", response_model=DataRunOut)
def fetch_open_meteo(
    payload: OpenMeteoFetchIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_tier(UserTier.admin)),
):
    fetched = fetch_open_meteo_current(payload.latitude, payload.longitude, payload.label)
    run = ingest_data_run(
        db,
        source_key=payload.source_key,
        summary=fetched["summary"],
        payload=fetched["payload"],
        points=fetched["points"],
    )
    fulfill_pending_fetch_requests(db, source_key=payload.source_key, admin_id=admin.id)
    db.commit()
    run_event_driven_for_source(payload.source_key)
    return serialize_data_run(db, run)


@router.post("/fetch/enso-oni", response_model=DataRunOut)
def fetch_enso_oni(
    payload: EnsoOniFetchIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_tier(UserTier.admin)),
):
    pipeline = get_pipeline(payload.source_key)
    result = pipeline.fetch()
    run = ingest_pipeline_result(db, source_key=payload.source_key, result=result)
    fulfill_pending_fetch_requests(db, source_key=payload.source_key, admin_id=admin.id)
    db.commit()
    run_event_driven_for_source(payload.source_key)
    return serialize_data_run(db, run)


@router.post("/fetch/usgs-earthquakes", response_model=DataRunOut)
def fetch_usgs_earthquakes(
    payload: UsgsEarthquakeFetchIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_tier(UserTier.admin)),
):
    pipeline = get_pipeline(payload.source_key)
    result = pipeline.fetch()
    run = ingest_pipeline_result(db, source_key=payload.source_key, result=result)
    fulfill_pending_fetch_requests(db, source_key=payload.source_key, admin_id=admin.id)
    db.commit()
    run_event_driven_for_source(payload.source_key)
    return serialize_data_run(db, run)


@router.post("/fetch/donki-solar-flares", response_model=DataRunOut)
def fetch_donki_solar_flares(
    payload: DonkiSolarFlareFetchIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_tier(UserTier.admin)),
):
    pipeline = get_pipeline(payload.source_key)
    result = pipeline.fetch(start_date=payload.start_date, end_date=payload.end_date)
    run = ingest_pipeline_result(db, source_key=payload.source_key, result=result)
    fulfill_pending_fetch_requests(db, source_key=payload.source_key, admin_id=admin.id)
    db.commit()
    run_event_driven_for_source(payload.source_key)
    return serialize_data_run(db, run)


@router.post("/fetch/nsidc-charctic", response_model=DataRunOut)
def fetch_nsidc_charctic(
    payload: NsidcCharcticFetchIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_tier(UserTier.admin)),
):
    fetched = fetch_nsidc_charctic_daily(days=payload.days, source_key=payload.source_key)
    run = ingest_data_run(
        db,
        source_key=fetched["source_key"],
        summary=fetched["summary"],
        payload=fetched["payload"],
        points=fetched["points"],
    )
    fulfill_pending_fetch_requests(db, source_key=fetched["source_key"], admin_id=admin.id)
    db.commit()
    run_event_driven_for_source(fetched["source_key"])
    return serialize_data_run(db, run)


@router.post("/fetch/nsidc-antarctic", response_model=DataRunOut)
def fetch_nsidc_antarctic(
    payload: NsidcAntarcticFetchIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_tier(UserTier.admin)),
):
    fetched = fetch_nsidc_antarctic_daily(days=payload.days, source_key=payload.source_key)
    run = ingest_data_run(
        db,
        source_key=fetched["source_key"],
        summary=fetched["summary"],
        payload=fetched["payload"],
        points=fetched["points"],
    )
    fulfill_pending_fetch_requests(db, source_key=fetched["source_key"], admin_id=admin.id)
    db.commit()
    run_event_driven_for_source(fetched["source_key"])
    return serialize_data_run(db, run)


@router.post("/fetch/smithsonian-volcanoes", response_model=DataRunOut)
def fetch_smithsonian_volcanoes(
    payload: SmithsonianVolcanoFetchIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_tier(UserTier.admin)),
):
    pipeline = get_pipeline(payload.source_key)
    result = pipeline.fetch()
    run = ingest_pipeline_result(db, source_key=payload.source_key, result=result)
    fulfill_pending_fetch_requests(db, source_key=payload.source_key, admin_id=admin.id)
    db.commit()
    run_event_driven_for_source(payload.source_key)
    return serialize_data_run(db, run)


def _ingest_pipeline_fetch(db: Session, *, source_key: str, admin_id: int):
    pipeline = get_pipeline(source_key)
    result = pipeline.fetch()
    run = ingest_pipeline_result(db, source_key=source_key, result=result)
    fulfill_pending_fetch_requests(db, source_key=source_key, admin_id=admin_id)
    db.commit()
    run_event_driven_for_source(source_key)
    return run


def _ingest_nsidc_fetch(db: Session, *, admin_id: int):
    fetched = fetch_nsidc_charctic_daily(days=365, source_key="nsidc_charctic_daily")
    run = ingest_data_run(
        db,
        source_key=fetched["source_key"],
        summary=fetched["summary"],
        payload=fetched["payload"],
        points=fetched["points"],
    )
    fulfill_pending_fetch_requests(db, source_key=fetched["source_key"], admin_id=admin_id)
    db.commit()
    run_event_driven_for_source(fetched["source_key"])
    return run


def _ingest_nsidc_antarctic_fetch(db: Session, *, admin_id: int):
    fetched = fetch_nsidc_antarctic_daily(days=365, source_key="nsidc_antarctic_daily")
    run = ingest_data_run(
        db,
        source_key=fetched["source_key"],
        summary=fetched["summary"],
        payload=fetched["payload"],
        points=fetched["points"],
    )
    fulfill_pending_fetch_requests(db, source_key=fetched["source_key"], admin_id=admin_id)
    db.commit()
    run_event_driven_for_source(fetched["source_key"])
    return run


def _prune_invalid_smithsonian_volcano_history(db: Session) -> dict[str, int]:
    cutoff = datetime(2005, 1, 1, tzinfo=timezone.utc)
    doomed_run_ids = [
        row[0]
        for row in db.execute(
            select(DataPoint.source_run_id).where(
                DataPoint.source_key == "smithsonian_volcanoes",
                DataPoint.observed_at < cutoff,
            )
        ).all()
    ]
    deleted_points = db.execute(
        delete(DataPoint).where(
            DataPoint.source_key == "smithsonian_volcanoes",
            DataPoint.observed_at < cutoff,
        )
    ).rowcount or 0
    deleted_runs = 0
    if doomed_run_ids:
        deleted_runs = db.execute(
            delete(DataSourceRun).where(
                DataSourceRun.id.in_(sorted(set(doomed_run_ids))),
                DataSourceRun.source_key == "smithsonian_volcanoes",
            )
        ).rowcount or 0
    return {"deleted_points": deleted_points, "deleted_runs": deleted_runs}


@router.post("/fetch/smithsonian-volcanoes/backfill", response_model=DataRunOut)
def backfill_smithsonian_volcanoes(
    payload: SmithsonianVolcanoBackfillIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_tier(UserTier.admin)),
):
    prune_summary = {"deleted_points": 0, "deleted_runs": 0}
    if payload.prune_invalid_existing:
        prune_summary = _prune_invalid_smithsonian_volcano_history(db)

    result = fetch_smithsonian_weekly_history(weeks=payload.weeks)
    result.payload = {
        **(result.payload or {}),
        "history_weeks": max(payload.weeks, 1),
        "pruned_invalid_existing": payload.prune_invalid_existing,
        **prune_summary,
    }
    run = ingest_pipeline_result(db, source_key=payload.source_key, result=result)
    fulfill_pending_fetch_requests(db, source_key=payload.source_key, admin_id=admin.id)
    db.commit()
    run_event_driven_for_source(payload.source_key)
    return serialize_data_run(db, run)


@router.post("/fetch/all", response_model=DataFetchAllOut)
def fetch_all_pipelines(
    db: Session = Depends(get_db),
    admin: User = Depends(require_tier(UserTier.admin)),
):
    controls = [
        ("nsidc_charctic_daily", "Arctic sea ice", lambda: _ingest_nsidc_fetch(db, admin_id=admin.id)),
        ("nsidc_antarctic_daily", "Antarctic sea ice", lambda: _ingest_nsidc_antarctic_fetch(db, admin_id=admin.id)),
        ("enso_oni", "ENSO / ONI", lambda: _ingest_pipeline_fetch(db, source_key="enso_oni", admin_id=admin.id)),
        ("usgs_earthquakes", "USGS earthquakes", lambda: _ingest_pipeline_fetch(db, source_key="usgs_earthquakes", admin_id=admin.id)),
        ("nasa_donki_solar_flares", "NASA DONKI solar flares", lambda: _ingest_pipeline_fetch(db, source_key="nasa_donki_solar_flares", admin_id=admin.id)),
        ("smithsonian_volcanoes", "Smithsonian volcanoes", lambda: _ingest_pipeline_fetch(db, source_key="smithsonian_volcanoes", admin_id=admin.id)),
    ]
    results: list[DataFetchAllItemOut] = []
    for source_key, label, fetcher in controls:
        try:
            run = fetcher()
            run_out = serialize_data_run(db, run)
            results.append(
                DataFetchAllItemOut(
                    source_key=source_key,
                    label=label,
                    status="success",
                    inserted_points=int((run.payload or {}).get("points_inserted", len(run_out.points))),
                    received_points=int((run.payload or {}).get("points_received", len(run_out.points))),
                    run=run_out,
                )
            )
        except Exception as exc:
            db.rollback()
            results.append(
                DataFetchAllItemOut(
                    source_key=source_key,
                    label=label,
                    status="failed",
                    error_message=str(exc),
                )
            )
    overall_status = "success" if all(result.status == "success" for result in results) else "partial_failure"
    return DataFetchAllOut(status=overall_status, results=results)
