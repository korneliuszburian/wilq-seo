from __future__ import annotations

from datetime import date
from typing import Any, cast

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from wilq.content.measurement.outcome import (
    ContentMeasurementObservedMetric,
    interpret_content_measurement_outcome,
)
from wilq.content.measurement.window import (
    ContentDateRange,
    ContentMeasurementMetric,
    ContentMeasurementWindow,
)


def _window(**overrides: object) -> ContentMeasurementWindow:
    payload: dict[str, object] = {
        "id": "measurement_window_content_work_item_bdo",
        "work_item_id": "content_work_item_bdo",
        "content_url": "https://ekologus.pl/bdo/",
        "baseline_period": ContentDateRange(
            start=date(2026, 5, 1),
            end=date(2026, 5, 31),
        ),
        "observation_period": ContentDateRange(
            start=date(2026, 7, 1),
            end=date(2026, 7, 31),
        ),
        "earliest_verdict_date": date(2026, 8, 1),
        "allowed_metrics": ["gsc_clicks", "gsc_impressions"],
        "source_connectors": ["google_search_console"],
        "evidence_ids": ["ev_gsc_bdo"],
        "status": "ready_for_review",
        "handoff_id": "wordpress_draft_handoff_content_work_item_bdo",
        "success_claim_allowed": True,
    }
    payload.update(overrides)
    return ContentMeasurementWindow.model_validate(payload)


def _metric(
    metric: str,
    baseline: float | None,
    observation: float | None,
    *,
    evidence_ids: list[str] | None = None,
) -> ContentMeasurementObservedMetric:
    return ContentMeasurementObservedMetric(
        metric=cast(ContentMeasurementMetric, metric),
        baseline_value=baseline,
        observation_value=observation,
        source_connector="google_search_console",
        evidence_ids=evidence_ids or ["ev_gsc_bdo"],
    )


def test_measurement_outcome_blocks_before_window_is_ready() -> None:
    outcome = interpret_content_measurement_outcome(
        window=_window(status="planned", success_claim_allowed=False),
        observed_metrics=[_metric("gsc_clicks", 10, 20)],
        as_of=date(2026, 7, 20),
    )

    assert outcome.status == "not_ready"
    assert outcome.success_claim_allowed is False
    assert outcome.queue_feedback_allowed is False
    assert outcome.confidence == "none"


def test_measurement_outcome_requires_metric_values_and_evidence() -> None:
    outcome = interpret_content_measurement_outcome(
        window=_window(),
        observed_metrics=[_metric("gsc_clicks", 10, None, evidence_ids=[])],
        as_of=date(2026, 8, 1),
    )

    assert outcome.status == "insufficient_data"
    assert outcome.success_claim_allowed is False
    assert "Brakuje wartości bazowej" in outcome.limitations[0]


def test_measurement_outcome_classifies_noisy_directional_and_success_states() -> None:
    noisy = interpret_content_measurement_outcome(
        window=_window(),
        observed_metrics=[_metric("gsc_clicks", 100, 104)],
        as_of=date(2026, 8, 1),
    )
    directional = interpret_content_measurement_outcome(
        window=_window(),
        observed_metrics=[
            _metric("gsc_clicks", 100, 130),
            _metric("gsc_impressions", 1000, 990),
        ],
        as_of=date(2026, 8, 1),
    )
    success = interpret_content_measurement_outcome(
        window=_window(),
        observed_metrics=[
            _metric("gsc_clicks", 100, 130),
            _metric("gsc_impressions", 1000, 1200),
        ],
        as_of=date(2026, 8, 1),
    )

    assert noisy.status == "noisy_inconclusive"
    assert noisy.success_claim_allowed is False
    assert directional.status == "directional_improvement"
    assert directional.success_claim_allowed is False
    assert directional.queue_feedback_allowed is True
    assert success.status == "measured_success"
    assert success.success_claim_allowed is True
    assert success.queue_feedback_allowed is True
    assert "nie pełny dowód przyczyny" in " ".join(success.limitations)


def test_measurement_outcome_api_returns_typed_interpretation() -> None:
    response = TestClient(app).post(
        "/api/content/work-items/measurement-outcome",
        json={
            "window": _window().model_dump(mode="json"),
            "observed_metrics": [
                {
                    "metric": "gsc_clicks",
                    "baseline_value": 100,
                    "observation_value": 130,
                    "source_connector": "google_search_console",
                    "evidence_ids": ["ev_gsc_bdo"],
                }
            ],
            "as_of": "2026-08-01",
        },
    )

    assert response.status_code == 200
    payload: dict[str, Any] = response.json()
    assert payload["outcome"]["status"] == "measured_success"
    assert payload["outcome"]["success_claim_allowed"] is True
    assert payload["outcome"]["source_connectors"] == ["google_search_console"]
