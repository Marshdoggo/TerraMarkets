from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.ingestion.types import NormalizedObservation, PipelineFetchResult
from app.models.data import DataSourceRun
from app.services.data_service import ingest_data_run

logger = logging.getLogger(__name__)


def normalized_observation_to_point(record: NormalizedObservation) -> dict:
    metadata = dict(record.metadata or {})
    raw_value = record.value
    numeric_value = None

    if isinstance(raw_value, (int, float, Decimal)):
      numeric_value = float(raw_value)
    else:
      metadata["normalized_value"] = raw_value

    unit = metadata.get("unit")
    label = metadata.get("label") or record.metric.replace("_", " ")

    metadata.update(
        {
            "source": record.source,
            "metric": record.metric,
        }
    )

    return {
        "series_key": record.metric,
        "label": label,
        "numeric_value": numeric_value,
        "unit": unit,
        "observed_at": record.timestamp,
        "metadata_json": metadata,
    }


def ingest_pipeline_result(
    db: Session,
    *,
    source_key: str,
    result: PipelineFetchResult,
) -> DataSourceRun:
    logger.info("Ingesting %s normalized records for %s", len(result.records), source_key)
    return ingest_data_run(
        db,
        source_key=source_key,
        summary=result.summary,
        payload=result.payload,
        points=[normalized_observation_to_point(record) for record in result.records],
    )
