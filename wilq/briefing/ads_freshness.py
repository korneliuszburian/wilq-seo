from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.schemas import (
    AdsFreshnessAssessment,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    connector_refresh_has_live_data,
)

GOOGLE_ADS_CONNECTOR_ID = "google_ads"
ADS_STALE_AFTER_HOURS = 48


def latest_google_ads_refresh() -> ConnectorRefreshRun | None:
    runs = [
        run
        for run in list_connector_refresh_runs(connector_id=GOOGLE_ADS_CONNECTOR_ID)
        if run.mode == ConnectorRefreshMode.vendor_read
    ]
    if not runs:
        return None
    return max(runs, key=connector_refresh_recency_key)


def ads_freshness_assessment(
    latest_refresh: ConnectorRefreshRun | None,
    *,
    refresh_status_label: Callable[[ConnectorRefreshRun | object], str],
) -> AdsFreshnessAssessment:
    if latest_refresh is None:
        return AdsFreshnessAssessment(
            state="missing",
            state_label="brak odczytu",
            latest_refresh_id=None,
            latest_refresh_completed_at=None,
            age_hours=None,
            stale_after_hours=ADS_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary="Brak zapisanego odczytu danych Google Ads.",
            next_step="Uruchom odczyt danych Google Ads przed oceną aktualnego stanu kampanii.",
        )

    completed_at = as_utc(latest_refresh.completed_at or latest_refresh.started_at)
    age_hours = round((datetime.now(UTC) - completed_at).total_seconds() / 3600, 2)
    if not connector_refresh_has_live_data(latest_refresh):
        return AdsFreshnessAssessment(
            state="blocked",
            state_label="odczyt zablokowany",
            latest_refresh_id=latest_refresh.id,
            latest_refresh_completed_at=completed_at,
            age_hours=age_hours,
            stale_after_hours=ADS_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary=(
                "Ostatni odczyt Google Ads nie zakończył się pełnym pobraniem metryk. "
                f"Status odczytu: {refresh_status_label(latest_refresh)}."
            ),
            next_step=(
                "Napraw blocker odczytu i uruchom ponownie odczyt danych Google Ads przed "
                "wnioskami o aktualnym stanie kampanii."
            ),
        )

    if age_hours > ADS_STALE_AFTER_HOURS:
        return AdsFreshnessAssessment(
            state="stale",
            state_label="dane wymagają odświeżenia",
            latest_refresh_id=latest_refresh.id,
            latest_refresh_completed_at=completed_at,
            age_hours=age_hours,
            stale_after_hours=ADS_STALE_AFTER_HOURS,
            requires_refresh=True,
            summary=(
                f"Ostatni odczyt danych Google Ads ma około {age_hours:.1f}h i jest do "
                "odświeżenia. To wystarcza do przeglądu nieświeżych danych, ale nie do "
                "wniosków o bieżącym stanie kampanii."
            ),
            next_step=(
                "Uruchom odczyt danych Google Ads, jeśli pytanie dotyczy aktualnego stanu "
                "kampanii, budżetów, rekomendacji albo wyszukiwanych haseł."
            ),
        )

    return AdsFreshnessAssessment(
        state="fresh",
        state_label="dane świeże",
        latest_refresh_id=latest_refresh.id,
        latest_refresh_completed_at=completed_at,
        age_hours=age_hours,
        stale_after_hours=ADS_STALE_AFTER_HOURS,
        requires_refresh=False,
        summary=(
            f"Ostatni odczyt danych Google Ads ma około {age_hours:.1f}h i mieści się "
            f"w progu {ADS_STALE_AFTER_HOURS}h."
        ),
        next_step="Można użyć danych Google Ads do review bez dodatkowego odświeżenia.",
    )


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def connector_refresh_recency_key(run: ConnectorRefreshRun) -> tuple[str, str]:
    timestamp = run.completed_at or run.started_at
    return (timestamp.isoformat(), run.id)
