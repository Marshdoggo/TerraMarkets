from __future__ import annotations

from app.ingestion.pipelines import (
    AntarcticSeaIcePipeline,
    DonkiSolarFlarePipeline,
    EnsoONIPipeline,
    SmithsonianVolcanoPipeline,
    USGSEarthquakePipeline,
)

PIPELINE_REGISTRY = {
    AntarcticSeaIcePipeline.source_key: AntarcticSeaIcePipeline(),
    EnsoONIPipeline.source_key: EnsoONIPipeline(),
    USGSEarthquakePipeline.source_key: USGSEarthquakePipeline(),
    DonkiSolarFlarePipeline.source_key: DonkiSolarFlarePipeline(),
    SmithsonianVolcanoPipeline.source_key: SmithsonianVolcanoPipeline(),
}


def get_pipeline(source_key: str):
    pipeline = PIPELINE_REGISTRY.get(source_key)
    if not pipeline:
        raise KeyError(f"Unknown pipeline: {source_key}")
    return pipeline
