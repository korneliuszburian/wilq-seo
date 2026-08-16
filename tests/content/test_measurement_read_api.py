from __future__ import annotations

from datetime import UTC, datetime

from apps.api.wilq_api.routers import content_workflow as workflow_router
from wilq.content.measurement import evidence as measurement_evidence
from wilq.content.measurement.deployment import ContentPublicDeployment
from wilq.content.measurement.read_contracts import build_content_measurement_read
from wilq.schemas import MetricFact

WORK_ITEM_ID = "content_work_item_measurement_read"
URL = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"


def _gsc_facts() -> list[MetricFact]:
    def fact(name: str, value: float, period: str, evidence: str, collected_at: datetime):
        return MetricFact(
            name=name,
            value=value,
            period=period,
            source_connector="google_search_console",
            evidence_id=evidence,
            dimensions={"page": URL, "query": "bdo"},
            collected_at=collected_at,
        )

    return [
        fact(
            "clicks",
            0.0,
            "2026-08-07/2026-08-07",
            "ev_baseline",
            datetime(2026, 8, 8, tzinfo=UTC),
        ),
        fact(
            "impressions",
            92.0,
            "2026-08-07/2026-08-07",
            "ev_baseline",
            datetime(2026, 8, 8, tzinfo=UTC),
        ),
        fact(
            "clicks",
            0.0,
            "2026-08-09/2026-08-09",
            "ev_observation",
            datetime(2026, 8, 10, tzinfo=UTC),
        ),
        fact(
            "impressions",
            113.0,
            "2026-08-09/2026-08-09",
            "ev_observation",
            datetime(2026, 8, 10, tzinfo=UTC),
        ),
    ]


class _FakeMetricStore:
    def __init__(self, facts: list[MetricFact]) -> None:
        self.facts = facts

    def list_metric_facts_for_content_url(self, *_args, **_kwargs) -> list[MetricFact]:
        return self.facts


def _deployment() -> ContentPublicDeployment:
    return ContentPublicDeployment(
        deployment_id="deployment_measurement_read",
        work_item_id=WORK_ITEM_ID,
        revision_id="revision_measurement_read",
        revision_digest="a" * 64,
        public_url=URL,
        wordpress_post_id="1234",
        publication_evidence_id="ev_publication",
        publication_source_connector="wordpress_ekologus",
        observed_at=datetime(2026, 8, 6, tzinfo=UTC),
        confirmed_by="wilku",
        confirmed_at=datetime(2026, 8, 6, 1, tzinfo=UTC),
    )


def test_measurement_read_returns_real_before_after_comparison(monkeypatch) -> None:
    monkeypatch.setattr(
        measurement_evidence,
        "metric_store",
        lambda: _FakeMetricStore(_gsc_facts()),
    )

    deployment = _deployment()
    result = build_content_measurement_read(
        work_item_id=WORK_ITEM_ID,
        revision_id=deployment.revision_id,
        revision_digest=deployment.revision_digest,
        deployment=deployment,
    )

    assert result.status == "available"
    assert result.work_item_id == WORK_ITEM_ID
    assert result.content_url == URL
    assert result.deployment_id == deployment.deployment_id
    assert result.publication_evidence_id == deployment.publication_evidence_id
    assert result.fact_count >= 4
    gsc = next(row for row in result.rows if row.source_connector == "google_search_console")
    assert gsc.status == "available"
    assert gsc.baseline_values["impressions"] == 92.0
    assert gsc.observation_values["impressions"] == 113.0
    assert gsc.baseline_period == "2026-08-07/2026-08-07"
    assert gsc.observation_period == "2026-08-09/2026-08-09"
    assert gsc.metric_names == ["clicks", "impressions"]
    assert set(gsc.evidence_ids) == {"ev_baseline", "ev_observation"}
    assert "kompletną lineage" in gsc.reason
    assert result.source_connectors == ["google_search_console"]


def test_measurement_read_returns_no_data_state_for_unknown_page(monkeypatch) -> None:
    monkeypatch.setattr(
        measurement_evidence,
        "metric_store",
        lambda: _FakeMetricStore([]),
    )

    deployment = _deployment().model_copy(
        update={"public_url": "https://www.ekologus.pl/nie-istnieje/"}
    )
    result = build_content_measurement_read(
        work_item_id=WORK_ITEM_ID,
        revision_id=deployment.revision_id,
        revision_digest=deployment.revision_digest,
        deployment=deployment,
    )

    assert result.status == "not_available"
    assert {row.source_connector for row in result.rows} == {
        "google_search_console",
        "google_analytics_4",
    }
    assert all(row.reason for row in result.rows)
    assert result.fact_count == 0
    assert result.source_connectors == []


def test_measurement_read_returns_typed_missing_deployment_state() -> None:
    result = build_content_measurement_read(
        work_item_id=WORK_ITEM_ID,
        revision_id="revision_measurement_read",
        revision_digest="a" * 64,
        deployment=None,
    )

    assert result.status == "blocked"
    assert result.content_url is None
    assert result.deployment_id is None
    assert result.rows == []
    assert "diagnostyki" in result.reason


def test_measurement_read_route_returns_typed_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        measurement_evidence,
        "metric_store",
        lambda: _FakeMetricStore(_gsc_facts()),
    )
    deployment = _deployment()
    revision = type(
        "Revision",
        (),
        {
            "revision_id": deployment.revision_id,
            "content_digest": deployment.revision_digest,
        },
    )()
    store = type(
        "Store",
        (),
        {"list_draft_revisions": lambda self, _work_item_id: [revision]},
    )()
    monkeypatch.setattr(
        workflow_router,
        "content_workflow_store",
        lambda: store,
    )
    monkeypatch.setattr(
        "wilq.content.workflow.store.store_public_deployment.public_deployment",
        lambda _store, *, work_item_id, revision_id, revision_digest: deployment,
    )

    result = workflow_router.content_work_item_measurement_read(
        WORK_ITEM_ID,
        deployment.revision_id,
    )

    assert result.work_item_id == WORK_ITEM_ID
    assert result.revision_id == deployment.revision_id
    assert result.content_url == deployment.public_url
    assert result.fact_count >= 4
    assert any(row.source_connector == "google_search_console" for row in result.rows)


def test_measurement_read_uses_real_persisted_metric_facts(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "metrics.duckdb"))
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state.sqlite3"))
    from wilq.connectors.vendor import VendorMetricFact
    from wilq.schemas import ConnectorRefreshMode, ConnectorRefreshRun, ConnectorRefreshStatus
    from wilq.storage.local_state import local_state_store
    from wilq.storage.metric_store import metric_store

    real_url = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    for run_id, period, impressions, at in (
        ("run_baseline", "2026-08-01/2026-08-07", 92.0, datetime(2026, 8, 8, tzinfo=UTC)),
        ("run_obs", "2026-08-08/2026-08-14", 113.0, datetime(2026, 8, 15, tzinfo=UTC)),
    ):
        run = ConnectorRefreshRun(
            id=run_id,
            connector_id="google_search_console",
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            started_at=at,
            completed_at=at,
            evidence_ids=[f"ev_{run_id}"],
            external_call_attempted=True,
            vendor_data_collected=True,
            summary=f"seed {run_id}",
        )
        metric_store().save_connector_refresh_metrics(
            run,
            detailed_facts=[
                VendorMetricFact(
                    "clicks",
                    0.0,
                    {"page": real_url, "query": "bdo"},
                    period=period,
                ),
                VendorMetricFact(
                    "impressions",
                    impressions,
                    {"page": real_url, "query": "bdo"},
                    period=period,
                ),
            ],
        )
        local_state_store().save_connector_refresh_run(run)

    deployment = ContentPublicDeployment(
        deployment_id="deployment_real_bdo",
        work_item_id="content_work_item_real_bdo",
        revision_id="revision_real_bdo",
        revision_digest="b" * 64,
        public_url=real_url,
        wordpress_post_id="1930",
        publication_evidence_id="ev_publication_real",
        publication_source_connector="wordpress_ekologus",
        observed_at=datetime(2026, 8, 6, tzinfo=UTC),
        confirmed_by="wilku",
        confirmed_at=datetime(2026, 8, 6, 1, tzinfo=UTC),
    )

    result = build_content_measurement_read(
        work_item_id="content_work_item_real_bdo",
        revision_id=deployment.revision_id,
        revision_digest=deployment.revision_digest,
        deployment=deployment,
    )

    assert result.status in {"available", "not_available"}
    assert result.fact_count >= 2
    assert result.content_url == real_url
    gsc = next(
        (row for row in result.rows if row.source_connector == "google_search_console"),
        None,
    )
    if gsc is not None and gsc.status == "available":
        assert gsc.observation_values.get("impressions") == 113.0
        assert set(gsc.evidence_ids) == {"ev_run_baseline", "ev_run_obs"}
