from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DataPointIn(BaseModel):
    series_key: str
    label: str
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    observed_at: datetime
    metadata_json: Optional[dict] = None


class DataIngestIn(BaseModel):
    source_key: str
    summary: Optional[str] = None
    payload: Optional[dict] = None
    points: list[DataPointIn]


class DataPointOut(BaseModel):
    id: int
    source_key: str
    series_key: str
    label: str
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    observed_at: str
    metadata_json: Optional[dict] = None


class DataRunOut(BaseModel):
    id: int
    source_key: str
    status: str
    summary: Optional[str] = None
    created_at: str
    points: list[DataPointOut]


class DataFetchAllItemOut(BaseModel):
    source_key: str
    label: str
    status: str
    inserted_points: int = 0
    received_points: int = 0
    run: Optional[DataRunOut] = None
    error_message: Optional[str] = None


class DataFetchAllOut(BaseModel):
    status: str
    results: list[DataFetchAllItemOut]


class DataFetchRequestIn(BaseModel):
    source_key: str
    label: str
    note: Optional[str] = None


class DataFetchRequestOut(BaseModel):
    id: int
    source_key: str
    label: str
    note: Optional[str] = None
    status: str
    requested_by_user_id: int
    requested_by_email: Optional[str] = None
    reviewed_by_user_id: Optional[int] = None
    created_at: str
    reviewed_at: Optional[str] = None


class OpenMeteoFetchIn(BaseModel):
    latitude: float
    longitude: float
    label: str
    source_key: str = "open_meteo_current"


class NsidcCharcticFetchIn(BaseModel):
    days: int = 365
    source_key: str = "nsidc_charctic_daily"


class EnsoOniFetchIn(BaseModel):
    source_key: str = "enso_oni"


class UsgsEarthquakeFetchIn(BaseModel):
    source_key: str = "usgs_earthquakes"


class DonkiSolarFlareFetchIn(BaseModel):
    source_key: str = "nasa_donki_solar_flares"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
