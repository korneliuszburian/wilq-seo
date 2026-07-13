from __future__ import annotations

from typing import Any

import pytest

import wilq.actions.service as action_service
from wilq.schemas import MetricFact


def test_action_metric_facts_use_latest_batch_read_for_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fact = MetricFact(
        name="clicks",
        value=7,
        period="last_28_days",
        source_connector="google_search_console",
        evidence_id="ev_action_latest",
    )
    seen: dict[str, Any] = {}

    class FastMetricStore:
        def list_metric_facts(self, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("Action candidates must use batched latest metric reads")

        def list_latest_metric_facts_by_connector(
            self,
            *_args: object,
            **_kwargs: object,
        ) -> object:
            raise AssertionError("Action candidates must use connector-specific limits")

        def list_latest_metric_facts_by_connector_limits(
            self,
            connector_limits: dict[str, int],
        ) -> dict[str, list[MetricFact]]:
            seen["connector_limits"] = connector_limits
            return {connector_id: [] for connector_id in connector_limits} | {
                "google_search_console": [fact]
            }

        def list_metric_facts_by_evidence_ids(
            self,
            _evidence_ids: list[str],
        ) -> list[MetricFact]:
            return []

    monkeypatch.setattr(action_service, "metric_store", lambda: FastMetricStore())

    facts = action_service._action_metric_facts()

    assert facts == [fact]
    assert seen["connector_limits"]["google_ads"] == action_service.ACTION_METRIC_FACT_LIMIT
    assert (
        seen["connector_limits"]["google_search_console"]
        == action_service.ACTION_METRIC_FACT_LIMIT
    )
