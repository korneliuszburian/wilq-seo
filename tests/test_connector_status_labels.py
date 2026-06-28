from __future__ import annotations

from wilq.schemas import (
    ConnectorCapability,
    ConnectorStatus,
    ConnectorStatusValue,
    FreshnessState,
    connector_status_label,
)


def test_connector_status_hydrates_operator_status_label() -> None:
    connector = ConnectorStatus(
        id="google_analytics_4",
        label="Google Analytics 4",
        status=ConnectorStatusValue.configured,
        configured=True,
        freshness=FreshnessState(state="unknown"),
        capabilities=ConnectorCapability(read=True),
        health_check="credential_presence",
    )

    assert connector.status_label == "dostęp skonfigurowany"
    assert connector.missing_credentials_summary_label == "brak brakujących pól dostępu"
    assert connector.credential_source_summary_label == "brak źródeł konfiguracji"


def test_connector_status_unknown_fallback_is_neutral_polish_copy() -> None:
    assert connector_status_label("vendor_status_that_drifted") == (
        "status źródła do sprawdzenia"
    )
