from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_snapshot
from wilq.content.canonical.redacted_landing import build_redacted_landing_reference
from wilq.content.workflow.ads_demand_source import content_diagnostics_with_ads_refresh
from wilq.schemas import (
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ContentDiagnosticsResponse,
    MetricFact,
)


def test_snapshot_reads_latest_ads_batch_and_joins_clicked_term_landing(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    client = TestClient(app)
    diagnostics = ContentDiagnosticsResponse.model_validate(
        client.get("/api/content/diagnostics").json()
    )
    decision = next(item for item in diagnostics.decision_queue if item.source_public_url)
    assert decision.source_public_url is not None
    work_item_id = f"content_work_item_{decision.id}"
    parsed_url = urlsplit(decision.source_public_url)
    content_path = parsed_url.path.rstrip("/") or "/"
    content_url = f"{parsed_url.scheme}://{parsed_url.netloc}{content_path}"
    gsc_evidence_id = next(
        fact.evidence_id
        for fact in decision.metric_facts
        if fact.source_connector == "google_search_console"
    )
    fresh_ads_refresh = _ads_refresh(diagnostics.freshness_assessment.checked_at)
    ads_refresh = _ads_refresh(
        diagnostics.freshness_assessment.checked_at - timedelta(hours=72)
    )
    diagnostics = diagnostics.model_copy(
        update={
            "latest_refreshes": [
                *(run for run in diagnostics.latest_refreshes if run.connector_id != "google_ads"),
                ads_refresh,
            ]
        }
    )
    previously_blocked = diagnostics.model_copy(
        update={
            "freshness_assessment": diagnostics.freshness_assessment.model_copy(
                update={
                    "blocked_connector_ids": ["google_ads"],
                    "stale_connector_ids": ["google_ads"],
                }
            )
        }
    )
    refreshed = content_diagnostics_with_ads_refresh(
        previously_blocked,
        fresh_ads_refresh,
    )
    assert "google_ads" not in refreshed.freshness_assessment.blocked_connector_ids
    assert "google_ads" not in refreshed.freshness_assessment.stale_connector_ids
    store = _GscStore(gsc_evidence_id, content_url, content_path)
    calls: list[dict[str, Any]] = []

    def exact_batch(_store: object, **kwargs: Any) -> list[MetricFact]:
        calls.append(kwargs)
        return _ads_facts(ads_refresh.evidence_ids[0], content_url)

    monkeypatch.setattr(content_snapshot, "build_content_diagnostics_cached", lambda: diagnostics)
    monkeypatch.setattr(content_snapshot, "list_connector_refresh_runs", lambda **_: [ads_refresh])
    monkeypatch.setattr(content_snapshot, "metric_store", lambda: store)
    monkeypatch.setattr(content_snapshot, "list_exact_metric_batch", exact_batch)

    response = client.get(
        "/api/content/work-items/"
        f"{work_item_id}/snapshot"
    )

    assert response.status_code == 200
    ads_rows = response.json()["planning_workspace"]["proposal"]["search_demand"][
        "ads_term_rows"
    ]
    assert calls[0]["connector_id"] == "google_ads"
    assert calls[0]["evidence_id"] == ads_refresh.evidence_ids[0]
    assert "search_term_clicks" in calls[0]["metric_names"]
    assert "search_term_payload_status" in calls[0]["metric_names"]
    assert [(row["term"], row["clicks"]) for row in ads_rows] == [("ekologus", 7)]
    assert ads_rows[0]["alignment_basis"] == "same_window_search_term_landing"
    assert ads_rows[0]["freshness"] == "stale"
    assert response.json()["planning_workspace"]["proposal"]["search_demand"][
        "optional_ads_status"
    ] == "stale"


class _GscStore:
    def __init__(self, evidence_id: str, content_url: str, content_path: str) -> None:
        self.evidence_id = evidence_id
        self.content_url = content_url
        self.content_path = content_path

    def list_metric_facts_for_content_url(
        self,
        connector_ids: list[str],
        content_url: str,
        *,
        content_path: str,
    ) -> list[MetricFact]:
        assert (connector_ids, content_url, content_path) == (
            ["google_search_console"],
            self.content_url,
            self.content_path,
        )
        return [
            _fact(
                "impressions",
                40,
                self.evidence_id,
                {"page": content_url, "query": "ekologus"},
            )
        ]


def _ads_refresh(
    collected_at: datetime = datetime(2026, 7, 16, 8, tzinfo=UTC),
) -> ConnectorRefreshRun:
    return ConnectorRefreshRun(
        id="refresh_ads_same_window",
        connector_id="google_ads",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=collected_at,
        completed_at=collected_at,
        evidence_ids=["ev_refresh_ads_same_window"],
        vendor_data_collected=True,
        metrics_persisted=True,
        metric_summary={"search_term_row_count": 1, "search_term_landing_mapped_row_count": 1},
        summary="Same-window Ads test batch.",
    )


def _ads_facts(evidence_id: str, content_url: str) -> list[MetricFact]:
    identity = build_redacted_landing_reference(content_url).identity_sha256
    assert identity is not None
    scope = {"campaign_id": "101", "ad_group_id": "201"}
    clicked_landing = {
        **scope,
        "search_term": "ekologus",
        "landing_mapping_status": "resolved",
        "landing_identity_sha256": identity,
        "actual_clicked_in_window": "true",
    }
    return [
        _fact(
            "search_term_clicks",
            7,
            evidence_id,
            clicked_landing,
        ),
        _fact("search_term_impressions", 70, evidence_id, clicked_landing),
        _fact("search_term_cost_micros", 3_000_000, evidence_id, clicked_landing),
        _fact("search_term_conversions", 1.0, evidence_id, clicked_landing),
        _fact("search_term_conversion_value", 400.0, evidence_id, clicked_landing),
        _fact("search_term_payload_status", "ready", evidence_id, {}),
    ]


def _fact(
    name: str,
    value: int | float | str,
    evidence_id: str,
    dimensions: dict[str, str],
) -> MetricFact:
    return MetricFact(
        name=name,
        value=value,
        period="last_30_days",
        source_connector=(
            "google_search_console" if "page" in dimensions else "google_ads"
        ),
        evidence_id=evidence_id,
        dimensions=dimensions,
        collected_at=datetime(2026, 7, 16, 8, tzinfo=UTC),
    )
