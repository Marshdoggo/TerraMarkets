from __future__ import annotations

from abc import ABC, abstractmethod

from app.ingestion.types import PipelineFetchResult


class BaseIngestionPipeline(ABC):
    source_key: str
    label: str

    @abstractmethod
    def fetch(self, **kwargs) -> PipelineFetchResult:
        raise NotImplementedError
