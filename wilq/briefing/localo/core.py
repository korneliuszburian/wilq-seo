"""Decomposed localo_diagnostics core implementation."""

from __future__ import annotations

from wilq.briefing.diagnostic_readiness import build_diagnostic_data_readiness
from wilq.briefing.localo.competitors import _localo_decision_queue, _localo_decisions_with_lineage
from wilq.briefing.localo.labels import (
    _label_localo_access_probe,
    _localo_connector_status_label,
    _localo_refresh_status_label,
)
from wilq.briefing.localo.reviews import _operator_connector, _operator_refresh, _operator_summary
from wilq.briefing.localo.shared import LOCALO_CONNECTOR_ID
from wilq.briefing.localo.visibility import (
    _access_probe,
    _latest_relevant_localo_refresh,
    _localo_read_contract_statuses,
    _localo_sections,
    _metric_facts_for_refresh,
    _visibility_facts,
)
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.content.operator_copy import unique
from wilq.schemas import LocaloDiagnosticsResponse


def build_localo_diagnostics() -> LocaloDiagnosticsResponse:
    connector = get_connector_status(LOCALO_CONNECTOR_ID)
    if connector is None:
        raise RuntimeError("Localo connector is not registered.")

    refresh_runs = list_connector_refresh_runs(connector_id=LOCALO_CONNECTOR_ID)
    latest_refresh = _latest_relevant_localo_refresh(refresh_runs)
    metric_facts = _metric_facts_for_refresh(latest_refresh)
    visibility_facts = _visibility_facts(metric_facts)
    access_probe = _label_localo_access_probe(
        _access_probe(
            connector_missing=connector.missing_credentials,
            run=latest_refresh,
        )
    )
    live_data_available = bool(visibility_facts)
    sections = _localo_sections(access_probe, latest_refresh, visibility_facts)
    read_contract_statuses = _localo_read_contract_statuses(visibility_facts)
    decision_queue = _localo_decisions_with_lineage(
        _localo_decision_queue(
            access_probe,
            visibility_facts,
            read_contract_statuses,
        )
    )
    action_ids = unique(
        action_id for decision in decision_queue for action_id in decision.action_ids
    )
    evidence_ids = unique(
        evidence_id for section in sections for evidence_id in section.evidence_ids
    )
    ready_contract_count = sum(
        1 for contract in read_contract_statuses if contract.status == "ready"
    )
    partial = bool(visibility_facts and ready_contract_count < len(read_contract_statuses))
    data_readiness = build_diagnostic_data_readiness(
        connector=connector,
        latest_refresh=latest_refresh,
        factual_metrics=visibility_facts[:12],
        factual_metric_count=len(visibility_facts),
        evidence_ids=evidence_ids,
        partial=partial,
        stale=connector.freshness.state == "stale",
        partial_coverage_label=(
            f"Potwierdzone {ready_contract_count} z {len(read_contract_statuses)} "
            "zakresów danych Localo."
        ),
    )

    return LocaloDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=_operator_connector(connector),
        connector_status_label=_localo_connector_status_label(str(connector.status)),
        latest_refresh=_operator_refresh(latest_refresh),
        latest_refresh_status_label=_localo_refresh_status_label(latest_refresh)
        if latest_refresh
        else None,
        access_probe=access_probe,
        live_data_available=live_data_available,
        data_readiness=data_readiness,
        visibility_fact_count=len(visibility_facts),
        read_contract_statuses=read_contract_statuses,
        operator_summary=_operator_summary(
            decision_queue,
            access_probe,
            len(visibility_facts),
            read_contract_statuses,
        ),
        decision_queue=decision_queue,
        sections=sections,
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        blocker_count=sum(1 for decision in decision_queue if decision.status == "blocked"),
    )
