from __future__ import annotations

from fastapi import APIRouter

from wilq.schemas import MetricFact, MetricStoreStatus
from wilq.storage.metric_store import metric_store

router = APIRouter()


@router.get("/api/metrics", response_model=list[MetricFact])
def metric_facts(connector_id: str | None = None, limit: int = 100) -> list[MetricFact]:
    return metric_store().list_metric_facts(connector_id=connector_id, limit=limit)


@router.get("/api/metrics/status", response_model=MetricStoreStatus)
def metric_store_status() -> MetricStoreStatus:
    return MetricStoreStatus.model_validate(metric_store().status())
