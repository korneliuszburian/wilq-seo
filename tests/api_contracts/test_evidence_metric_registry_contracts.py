from __future__ import annotations

from pathlib import Path

import pytest

from wilq.connectors.vendor import VendorMetricFact
from wilq.evidence.registry import list_evidence_by_ids, refresh_run_evidence_id
from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshRun, ConnectorRefreshStatus
from wilq.storage.metric_store import metric_store


def test_list_evidence_by_ids_returns_metric_fact_evidence_without_full_scan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "targeted_evidence.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "targeted_evidence.duckdb"))
    run = ConnectorRefreshRun(
        id="refresh_targeted_metric_evidence",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=[refresh_run_evidence_id("refresh_targeted_metric_evidence")],
        summary="Targeted metric evidence test run.",
    )
    metric_store().save_connector_refresh_metrics(
        run,
        detailed_facts=[
            VendorMetricFact(
                "clicks",
                12,
                {
                    "query": "bdo co to",
                    "page": "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
                },
            )
        ],
    )

    evidence = list_evidence_by_ids(
        [
            refresh_run_evidence_id("refresh_targeted_metric_evidence"),
            "ev_missing_not_returned",
        ]
    )

    assert [item.id for item in evidence] == [
        refresh_run_evidence_id("refresh_targeted_metric_evidence")
    ]
    assert evidence[0].source_connector == "google_search_console"
    assert evidence[0].source_type == "metric_fact_store"
    assert "clicks" in evidence[0].summary
