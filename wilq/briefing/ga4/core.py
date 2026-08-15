"""Decomposed ga4_diagnostics core implementation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from threading import Lock
from time import monotonic as monotonic

from wilq.actions.service import list_actions
from wilq.briefing.diagnostic_readiness import build_diagnostic_data_readiness
from wilq.briefing.ga4.conversions import _conversion_readiness_contract
from wilq.briefing.ga4.labels import (
    _ga4_connector_status_label,
    _ga4_live_data_status_label,
    _ga4_metric_fact_with_marketer_labels,
    _ga4_refresh_status_label,
    _ga4_response_with_marketer_labels,
)
from wilq.briefing.ga4.measurement import (
    _ga4_action_ids,
    _ga4_action_safety_section,
    _ga4_decision_queue,
    _ga4_decisions_with_lineage,
    _ga4_freshness_assessment,
    _latest_ga4_refresh,
    _tracking_readiness_section,
)
from wilq.briefing.ga4.shared import (
    GA4_CONNECTOR_ID,
    GA4_METRIC_FACT_LIMIT,
    _dimensioned_ga4_facts,
    _landing_group_count,
    _low_engagement_count,
    _tactical_landing_group_count,
    _unique,
    _wordpress_match_count,
)
from wilq.briefing.ga4.traffic import _landing_behavior_section, _operator_summary
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.connectors.registry import get_connector_status
from wilq.schemas import (
    ActionObject,
    Ga4DiagnosticsResponse,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
    connector_refresh_has_live_data,
)
from wilq.storage.metric_store import metric_store

DEFAULT_GA4_DIAGNOSTICS_CACHE_SECONDS = 60.0


_cached_ga4_diagnostics: Ga4DiagnosticsCacheEntry | None = None


_ga4_diagnostics_cache_lock = Lock()


@dataclass(frozen=True)
class Ga4DiagnosticsCacheEntry:
    created_at: float
    diagnostics: Ga4DiagnosticsResponse


def build_ga4_diagnostics(
    tactical_items: list[TacticalQueueItem] | None = None,
    actions: list[ActionObject] | None = None,
    metric_facts: list[MetricFact] | None = None,
) -> Ga4DiagnosticsResponse:
    connector = get_connector_status(GA4_CONNECTOR_ID)
    if connector is None:
        raise RuntimeError("GA4 connector is not registered.")
    latest_refresh = _latest_ga4_refresh()
    metric_facts = (
        metric_facts
        if metric_facts is not None
        else metric_store().list_metric_facts(
            connector_id=GA4_CONNECTOR_ID,
            limit=GA4_METRIC_FACT_LIMIT,
        )
    )
    metric_facts = [_ga4_metric_fact_with_marketer_labels(fact) for fact in metric_facts]
    live_data_available = bool(metric_facts) and (
        latest_refresh is None or connector_refresh_has_live_data(latest_refresh)
    )
    trusted_facts = metric_facts if live_data_available else []
    source_tactical_items = (
        tactical_items if tactical_items is not None else build_tactical_queue().items
    )
    tactical_items = [
        item for item in source_tactical_items if item.domain == OpportunityDomain.ga4
    ]
    actions = actions if actions is not None else list_actions()
    action_ids = _ga4_action_ids(actions)
    dimensioned_facts = _dimensioned_ga4_facts(trusted_facts)
    decision_queue = _ga4_decisions_with_lineage(
        _ga4_decision_queue(tactical_items, action_ids, dimensioned_facts)
    )
    freshness_assessment = _ga4_freshness_assessment(latest_refresh, trusted_facts)
    conversion_readiness_contract = _conversion_readiness_contract(
        latest_refresh=latest_refresh,
        facts=trusted_facts,
        tactical_items=tactical_items,
        action_ids=action_ids,
    )
    sections = [
        _landing_behavior_section(latest_refresh, trusted_facts, tactical_items, action_ids),
        _tracking_readiness_section(latest_refresh, trusted_facts, tactical_items, action_ids),
        _ga4_action_safety_section(latest_refresh, trusted_facts, tactical_items, action_ids),
    ]
    evidence_ids = _unique(
        [
            *(evidence_id for section in sections for evidence_id in section.evidence_ids),
            *conversion_readiness_contract.evidence_ids,
        ]
    )
    data_readiness = build_diagnostic_data_readiness(
        connector=connector,
        latest_refresh=latest_refresh,
        factual_metrics=trusted_facts[:12],
        factual_metric_count=len(trusted_facts),
        evidence_ids=evidence_ids,
        partial=bool(
            latest_refresh and latest_refresh.quality_state.value == "partial"
        ),
        stale=bool(trusted_facts and freshness_assessment.requires_refresh),
        partial_coverage_label=(
            "Pokazane metryki obejmują tylko potwierdzony zakres odczytu GA4."
        ),
    )
    response = Ga4DiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        connector_status_label=_ga4_connector_status_label(connector.status),
        latest_refresh=latest_refresh,
        latest_refresh_status_label=_ga4_refresh_status_label(latest_refresh)
        if latest_refresh
        else "",
        live_data_available=live_data_available,
        live_data_status_label=_ga4_live_data_status_label(live_data_available),
        data_readiness=data_readiness,
        landing_group_count=max(
            _landing_group_count(trusted_facts),
            _tactical_landing_group_count(tactical_items),
        ),
        low_engagement_count=_low_engagement_count(tactical_items),
        wordpress_match_count=_wordpress_match_count(tactical_items),
        freshness_assessment=freshness_assessment,
        conversion_readiness_contract=conversion_readiness_contract,
        operator_summary=_operator_summary(
            decision_queue,
            conversion_readiness_contract,
            freshness_assessment,
            sections,
            action_ids,
        ),
        decision_queue=decision_queue,
        sections=sections,
        evidence_ids=evidence_ids,
        action_ids=_unique(action_id for section in sections for action_id in section.action_ids),
        blocker_count=(
            sum(1 for section in sections if section.status == "blocked")
            + (1 if conversion_readiness_contract.status != "ready" else 0)
        ),
        decision_blocker_count=sum(
            1 for decision in decision_queue if decision.status == "blocked"
        ),
    )
    return _ga4_response_with_marketer_labels(response)


def build_ga4_diagnostics_cached() -> Ga4DiagnosticsResponse:
    """Reuse one GA4 read contract across daily-check and the diagnostics route."""
    cached = _read_ga4_diagnostics_cache()
    if cached is not None:
        return cached
    with _ga4_diagnostics_cache_lock:
        cached = _read_ga4_diagnostics_cache()
        if cached is not None:
            return cached
        diagnostics = build_ga4_diagnostics()
        _write_ga4_diagnostics_cache(diagnostics)
        return diagnostics


def clear_ga4_diagnostics_cache() -> None:
    global _cached_ga4_diagnostics
    with _ga4_diagnostics_cache_lock:
        _cached_ga4_diagnostics = None


def ga4_diagnostics_cache_ready() -> bool:
    return _ga4_diagnostics_cache_seconds() <= 0 or _read_ga4_diagnostics_cache() is not None


def _read_ga4_diagnostics_cache() -> Ga4DiagnosticsResponse | None:
    cache_seconds = _ga4_diagnostics_cache_seconds()
    if cache_seconds <= 0 or _cached_ga4_diagnostics is None:
        return None
    if monotonic() - _cached_ga4_diagnostics.created_at > cache_seconds:
        return None
    return _cached_ga4_diagnostics.diagnostics


def _write_ga4_diagnostics_cache(diagnostics: Ga4DiagnosticsResponse) -> None:
    global _cached_ga4_diagnostics
    if _ga4_diagnostics_cache_seconds() <= 0:
        return
    _cached_ga4_diagnostics = Ga4DiagnosticsCacheEntry(
        created_at=monotonic(),
        diagnostics=diagnostics,
    )


def _ga4_diagnostics_cache_seconds() -> float:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return 0.0
    configured = os.getenv("WILQ_GA4_DIAGNOSTICS_CACHE_SECONDS")
    if configured is None:
        return DEFAULT_GA4_DIAGNOSTICS_CACHE_SECONDS
    try:
        return max(0.0, float(configured))
    except ValueError:
        return DEFAULT_GA4_DIAGNOSTICS_CACHE_SECONDS
