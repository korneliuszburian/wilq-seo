from __future__ import annotations

import pytest

from wilq.briefing.diagnostic_readiness import build_diagnostic_data_readiness
from wilq.schemas import (
    ConnectorCapability,
    ConnectorRefreshState,
    ConnectorStatus,
    ConnectorStatusValue,
    FreshnessState,
    MetricFact,
)


def _connector(*, refresh_allowed: bool) -> ConnectorStatus:
    return ConnectorStatus(
        id="localo",
        label="Localo",
        status=ConnectorStatusValue.configured,
        configured=True,
        freshness=FreshnessState(state="unknown"),
        refresh_state=ConnectorRefreshState(
            refresh_allowed=refresh_allowed,
            safe_next_step="Uruchom odczyt Localo przed oceną widoczności.",
        ),
        capabilities=ConnectorCapability(read=True),
        health_check="credential_presence",
    )


def test_configured_connector_without_facts_is_recovery_not_zero() -> None:
    readiness = build_diagnostic_data_readiness(
        connector=_connector(refresh_allowed=True),
        latest_refresh=None,
        factual_metrics=[],
    )

    assert readiness.state == "refresh_available"
    assert readiness.factual_metric_count == 0
    assert readiness.factual_metrics == []
    assert readiness.refresh_allowed is True


def test_observed_zero_is_ready_factual_metric_with_trace() -> None:
    readiness = build_diagnostic_data_readiness(
        connector=_connector(refresh_allowed=False),
        latest_refresh=None,
        factual_metrics=[
            MetricFact(
                name="localo_competitor_change_count",
                value=0,
                period="localo_mcp_read",
                source_connector="localo",
                evidence_id="ev_localo_observed_zero",
            )
        ],
    )

    assert readiness.state == "ready"
    assert readiness.factual_metric_count == 1
    fact = readiness.factual_metrics[0]
    assert fact.value == 0
    assert fact.source_connector_label == "Localo"
    assert fact.period_label == "ostatni odczyt Localo"
    assert readiness.evidence_ids == ["ev_localo_observed_zero"]


@pytest.mark.parametrize(
    "field",
    ["evidence_id", "metric_label", "period_label", "source_connector_label"],
)
def test_metric_fact_rejects_blank_marketer_context(field: str) -> None:
    payload = {
        "name": "localo_competitor_change_count",
        "metric_label": "Zmiany konkurencji",
        "value": 0,
        "period": "localo_mcp_read",
        "period_label": "ostatni odczyt Localo",
        "source_connector": "localo",
        "source_connector_label": "Localo",
        "evidence_id": "ev_localo_observed_zero",
    }
    for blank_value in ["", "   "]:
        payload[field] = blank_value

        with pytest.raises(ValueError, match="pustego kontekstu marketera"):
            MetricFact(**payload)
