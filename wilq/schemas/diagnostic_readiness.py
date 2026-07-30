"""API-owned readiness projection shared by diagnostic response models."""

from __future__ import annotations

from collections.abc import Iterable

from .core import (
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorStatus,
    ConnectorStatusValue,
    DiagnosticDataReadiness,
    DiagnosticDataReadinessState,
    MetricFact,
)


def build_diagnostic_data_readiness(
    *,
    connector: ConnectorStatus,
    latest_refresh: ConnectorRefreshRun | None,
    factual_metrics: Iterable[MetricFact],
    factual_metric_count: int | None = None,
    evidence_ids: Iterable[str] = (),
    partial: bool = False,
    stale: bool = False,
    partial_coverage_label: str | None = None,
) -> DiagnosticDataReadiness:
    """Project facts or explicit recovery without dashboard-side inference."""

    facts = list(factual_metrics)
    trace_ids = _trace_ids(facts, evidence_ids, latest_refresh)
    if stale:
        return _nonfactual_readiness(
            connector=connector,
            latest_refresh=latest_refresh,
            evidence_ids=trace_ids,
            state=(
                DiagnosticDataReadinessState.refresh_available
                if connector.refresh_state.refresh_allowed
                else DiagnosticDataReadinessState.unavailable
            ),
            state_label="Dane wymagają odświeżenia",
            reason=(
                "WILQ ma wcześniejszy odczyt, ale nie traktuje go jako bieżącej "
                "podstawy liczb ani rekomendacji."
            ),
            coverage_label="Metryki z wcześniejszego odczytu nie są pokazane jako bieżące.",
        )
    if facts:
        return _factual_readiness(
            connector=connector,
            latest_refresh=latest_refresh,
            facts=facts,
            factual_metric_count=factual_metric_count,
            evidence_ids=trace_ids,
            partial=partial,
            partial_coverage_label=partial_coverage_label,
        )
    return _missing_readiness(connector, latest_refresh, trace_ids)


def _factual_readiness(
    *,
    connector: ConnectorStatus,
    latest_refresh: ConnectorRefreshRun | None,
    facts: list[MetricFact],
    factual_metric_count: int | None,
    evidence_ids: list[str],
    partial: bool,
    partial_coverage_label: str | None,
) -> DiagnosticDataReadiness:
    return DiagnosticDataReadiness(
        state=(
            DiagnosticDataReadinessState.partial
            if partial
            else DiagnosticDataReadinessState.ready
        ),
        state_label="Dane częściowe" if partial else "Dane gotowe do użycia",
        reason=(
            "WILQ potwierdził tylko część wymaganych danych; pokazuje wyłącznie "
            "zaobserwowane fakty."
            if partial
            else "WILQ ma utrwalone fakty dla tego widoku."
        ),
        safe_next_step=(
            connector.refresh_state.safe_next_step
            if partial
            else "Przejrzyj fakty i podejmij tylko decyzję opartą na pokazanych dowodach."
        ),
        connector_id=connector.id,
        latest_refresh_id=latest_refresh.id if latest_refresh else None,
        evidence_ids=evidence_ids,
        factual_metric_count=(
            factual_metric_count if factual_metric_count is not None else len(facts)
        ),
        factual_metrics=facts,
        coverage_label=(
            partial_coverage_label or "Zakres danych jest częściowy."
            if partial
            else "Pokazane metryki są potwierdzone przez WILQ."
        ),
        refresh_allowed=connector.refresh_state.refresh_allowed,
    )


def _missing_readiness(
    connector: ConnectorStatus,
    latest_refresh: ConnectorRefreshRun | None,
    evidence_ids: list[str],
) -> DiagnosticDataReadiness:
    state, label, reason = _missing_state(connector, latest_refresh)
    return _nonfactual_readiness(
        connector=connector,
        latest_refresh=latest_refresh,
        evidence_ids=evidence_ids,
        state=state,
        state_label=label,
        reason=reason,
        coverage_label="Brak potwierdzonych metryk do pokazania.",
    )


def _missing_state(
    connector: ConnectorStatus,
    latest_refresh: ConnectorRefreshRun | None,
) -> tuple[DiagnosticDataReadinessState, str, str]:
    if latest_refresh and latest_refresh.status in {
        ConnectorRefreshStatus.queued,
        ConnectorRefreshStatus.running,
    }:
        return (
            DiagnosticDataReadinessState.refresh_running,
            "Trwa odczyt danych",
            "WILQ wykonuje odczyt źródła; nie pokazuje jeszcze metryk ani rekomendacji.",
        )
    if latest_refresh and latest_refresh.status == ConnectorRefreshStatus.failed:
        return (
            DiagnosticDataReadinessState.failed,
            "Odczyt danych nie powiódł się",
            "Ostatni odczyt nie dostarczył utrwalonych metryk do tej decyzji.",
        )
    if latest_refresh and latest_refresh.status == ConnectorRefreshStatus.blocked:
        return (
            DiagnosticDataReadinessState.blocked,
            "Odczyt danych jest zablokowany",
            "WILQ nie ma potwierdzonych metryk, bo ostatni odczyt źródła został zablokowany.",
        )
    if connector.status in {
        ConnectorStatusValue.missing_credentials,
        ConnectorStatusValue.auth_error,
        ConnectorStatusValue.missing_dependency,
        ConnectorStatusValue.disabled,
    }:
        return (
            DiagnosticDataReadinessState.blocked,
            "Brak dostępu do danych",
            "WILQ nie ma dostępu potrzebnego do potwierdzenia metryk dla tego widoku.",
        )
    if connector.status in {
        ConnectorStatusValue.unreachable,
        ConnectorStatusValue.rate_limited,
        ConnectorStatusValue.error,
    }:
        return (
            DiagnosticDataReadinessState.failed,
            "Źródło danych jest niedostępne",
            "WILQ nie uzyskał potwierdzonego odczytu ze źródła danych.",
        )
    if connector.refresh_state.refresh_allowed:
        return (
            DiagnosticDataReadinessState.refresh_available,
            "Wymagany odczyt danych",
            (
                "Źródło jest skonfigurowane, ale WILQ nie ma jeszcze utrwalonych metryk "
                "do tej decyzji."
            ),
        )
    return (
        DiagnosticDataReadinessState.unavailable,
        "Dane są niedostępne",
        "WILQ nie potwierdził metryk potrzebnych do tego widoku.",
    )


def _nonfactual_readiness(
    *,
    connector: ConnectorStatus,
    latest_refresh: ConnectorRefreshRun | None,
    evidence_ids: list[str],
    state: DiagnosticDataReadinessState,
    state_label: str,
    reason: str,
    coverage_label: str,
) -> DiagnosticDataReadiness:
    return DiagnosticDataReadiness(
        state=state,
        state_label=state_label,
        reason=reason,
        safe_next_step=connector.refresh_state.safe_next_step,
        connector_id=connector.id,
        latest_refresh_id=latest_refresh.id if latest_refresh else None,
        evidence_ids=evidence_ids,
        coverage_label=coverage_label,
        refresh_allowed=connector.refresh_state.refresh_allowed,
    )


def _trace_ids(
    facts: Iterable[MetricFact],
    evidence_ids: Iterable[str],
    latest_refresh: ConnectorRefreshRun | None,
) -> list[str]:
    seen: set[str] = set()
    values = [
        *evidence_ids,
        *(fact.evidence_id for fact in facts),
        *(latest_refresh.evidence_ids if latest_refresh else []),
    ]
    return [value for value in values if value and not (value in seen or seen.add(value))]
