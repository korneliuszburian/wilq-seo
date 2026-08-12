from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from wilq.content.measurement import evidence as measurement_evidence
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


def test_measurement_read_returns_real_before_after_comparison(monkeypatch) -> None:
    monkeypatch.setattr(
        measurement_evidence,
        "metric_store",
        lambda: _FakeMetricStore(_gsc_facts()),
    )

    result = build_content_measurement_read(work_item_id=WORK_ITEM_ID, content_url=URL)

    assert result.work_item_id == WORK_ITEM_ID
    assert result.content_url == URL
    assert result.fact_count >= 4
    gsc = next(row for row in result.rows if row.source_connector == "google_search_console")
    assert gsc.status == "available"
    assert gsc.baseline_values["impressions"] == 92.0
    assert gsc.observation_values["impressions"] == 113.0
    assert gsc.metric_names == ["clicks", "impressions"]
    assert set(gsc.evidence_ids) == {"ev_baseline", "ev_observation"}


def test_measurement_read_returns_no_data_state_for_unknown_page(monkeypatch) -> None:
    monkeypatch.setattr(
        measurement_evidence,
        "metric_store",
        lambda: _FakeMetricStore([]),
    )

    result = build_content_measurement_read(
        work_item_id=WORK_ITEM_ID,
        content_url="https://www.ekologus.pl/nie-istnieje/",
    )

    assert result.rows == []
    assert result.fact_count == 0
    assert result.source_connectors == []


def test_measurement_read_route_returns_typed_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        measurement_evidence,
        "metric_store",
        lambda: _FakeMetricStore(_gsc_facts()),
    )
    snapshot = SimpleNamespace(
        preflight=SimpleNamespace(
            item=SimpleNamespace(
                final_canonical_url=URL,
                source_public_url=URL,
            )
        )
    )
    import apps.api.wilq_api.routers.content_snapshot as snapshot_module

    monkeypatch.setattr(
        snapshot_module,
        "snapshot_for_work_item_or_404",
        lambda _work_item_id: snapshot,
    )

    client = TestClient(__import__("apps.api.wilq_api.main", fromlist=["app"]).app)
    response = client.get(f"/api/content/work-items/{WORK_ITEM_ID}/measurement")

    assert response.status_code == 200
    payload = response.json()
    assert payload["work_item_id"] == WORK_ITEM_ID
    assert payload["content_url"] == URL
    assert payload["fact_count"] >= 4
    assert any(row["source_connector"] == "google_search_console" for row in payload["rows"])
