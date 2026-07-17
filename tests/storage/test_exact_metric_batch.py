from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from wilq.connectors.vendor import VendorMetricFact
from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshRun, ConnectorRefreshStatus
from wilq.storage.exact_metric_batch import list_exact_metric_batch
from wilq.storage.metric_store import DuckDbMetricStore


def test_exact_metric_batch_filters_in_storage_without_historical_deltas(
    tmp_path: Path,
) -> None:
    store = DuckDbMetricStore(tmp_path / "metrics.duckdb")
    now = datetime.now(UTC)
    older = _run("ads_old", "ev_ads_old", now - timedelta(days=1))
    latest = _run("ads_latest", "ev_ads_latest", now)
    store.save_connector_refresh_metrics(
        older,
        detailed_facts=[VendorMetricFact("search_term_clicks", 3)],
    )
    store.save_connector_refresh_metrics(
        latest,
        detailed_facts=[
            VendorMetricFact("search_term_clicks", 7),
            VendorMetricFact("unrelated_metric", 999),
        ],
    )

    facts = list_exact_metric_batch(
        store,
        connector_id="google_ads",
        evidence_id="ev_ads_latest",
        metric_names={"search_term_clicks"},
    )

    assert [(fact.name, fact.value, fact.evidence_id) for fact in facts] == [
        ("search_term_clicks", 7, "ev_ads_latest")
    ]
    assert facts[0].previous_value is None
    assert facts[0].previous_evidence_id is None


def _run(run_id: str, evidence_id: str, collected_at: datetime) -> ConnectorRefreshRun:
    return ConnectorRefreshRun(
        id=run_id,
        connector_id="google_ads",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=collected_at,
        completed_at=collected_at,
        evidence_ids=[evidence_id],
        metric_summary={},
        summary="Exact batch storage proof.",
    )
