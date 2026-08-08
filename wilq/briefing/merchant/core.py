from __future__ import annotations

import os
from dataclasses import dataclass
from time import monotonic

from wilq.actions.service import list_actions
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.connectors.registry import get_connector_status
from wilq.schemas import (
    ActionObject,
    ConnectorRefreshRun,
    MerchantDiagnosticsResponse,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
    connector_refresh_has_live_data,
)
from wilq.storage.metric_store import metric_store

from .feed_quality import (
    _current_facts_for_refresh,
    _current_tactical_items_for_refresh,
    _feed_health_section,
    _issue_queue_section,
    _merchant_freshness_assessment,
    _merchant_issue_clusters,
    _merchant_unknowns,
    _numeric_metric_or_refresh_summary,
)
from .labels import (
    _merchant_change_preview_with_operator_labels,
    _merchant_connector_status_label,
    _merchant_live_data_status_label,
    _merchant_metric_fact_with_labels,
    _merchant_refresh_status_label,
    _merchant_response_with_operator_labels,
)
from .operator_summary import (
    _merchant_decision_queue,
    _merchant_decisions_with_lineage,
    _merchant_decisions_with_price_impact_review,
    _merchant_decisions_with_product_state_review,
    _merchant_preview_cards,
    _operator_summary,
    _product_action_safety_section,
)
from .products import (
    _merchant_price_impact_readiness,
    _merchant_product_performance_readiness,
    _merchant_product_sample_readiness,
)
from .shared import (
    DEFAULT_MERCHANT_DIAGNOSTICS_CACHE_SECONDS,
    MERCHANT_CONNECTOR_ID,
    MERCHANT_METRIC_FACT_LIMIT,
    _latest_connector_refresh,
    _merchant_action_ids,
    _unique,
)


@dataclass(frozen=True)
class MerchantDiagnosticsCacheEntry:
    created_at: float
    diagnostics: MerchantDiagnosticsResponse


_cached_merchant_diagnostics: MerchantDiagnosticsCacheEntry | None = None


def build_merchant_diagnostics(
    *,
    tactical_items: list[TacticalQueueItem] | None = None,
    actions: list[ActionObject] | None = None,
    metric_facts: list[MetricFact] | None = None,
) -> MerchantDiagnosticsResponse:
    connector = get_connector_status(MERCHANT_CONNECTOR_ID)
    if connector is None:
        raise RuntimeError("Merchant Center connector is not registered.")
    latest_refresh = _latest_merchant_refresh()
    metric_facts = (
        metric_facts
        if metric_facts is not None
        else metric_store().list_metric_facts(
            connector_id=MERCHANT_CONNECTOR_ID,
            limit=MERCHANT_METRIC_FACT_LIMIT,
        )
    )
    metric_facts = [_merchant_metric_fact_with_labels(fact) for fact in metric_facts]
    live_data_available = bool(metric_facts) and (
        latest_refresh is None
        or connector_refresh_has_live_data(latest_refresh)
    )
    trusted_facts = metric_facts if live_data_available else []
    tactical_items = [
        item
        for item in (tactical_items if tactical_items is not None else build_tactical_queue().items)
        if item.domain == OpportunityDomain.merchant
    ]
    current_issue_facts = _current_facts_for_refresh(latest_refresh, trusted_facts)
    current_tactical_items = _current_tactical_items_for_refresh(latest_refresh, tactical_items)
    actions = actions if actions is not None else list_actions()
    action_ids = _merchant_action_ids(actions)
    issue_clusters = _merchant_issue_clusters(current_issue_facts, action_ids)
    sections = [
        _feed_health_section(latest_refresh, trusted_facts, action_ids),
        _issue_queue_section(
            latest_refresh,
            current_issue_facts,
            current_tactical_items,
            issue_clusters,
            action_ids,
        ),
        _product_action_safety_section(
            latest_refresh,
            trusted_facts,
            current_tactical_items,
            action_ids,
        ),
    ]
    decision_queue = _merchant_decision_queue(
        latest_refresh=latest_refresh,
        facts=current_issue_facts,
        tactical_items=current_tactical_items,
        issue_clusters=issue_clusters,
        action_ids=action_ids,
    )
    freshness_assessment = _merchant_freshness_assessment(latest_refresh)
    product_sample_readiness = _merchant_product_sample_readiness(
        issue_clusters,
        decision_queue,
    )
    product_performance_readiness = _merchant_product_performance_readiness(
        issue_clusters=issue_clusters,
        product_sample_readiness=product_sample_readiness,
    )
    price_impact_readiness = _merchant_price_impact_readiness(product_performance_readiness)
    price_impact_readiness = price_impact_readiness.model_copy(
        update={
            "change_preview": [
                _merchant_change_preview_with_operator_labels(preview)
                for preview in price_impact_readiness.change_preview
            ],
            "preview_cards": _merchant_preview_cards(price_impact_readiness.change_preview),
        }
    )
    decision_queue = _merchant_decisions_with_product_state_review(
        decision_queue,
        product_performance_readiness,
        action_ids,
    )
    decision_queue = _merchant_decisions_with_price_impact_review(
        decision_queue,
        price_impact_readiness,
        action_ids,
    )
    decision_queue = _merchant_decisions_with_lineage(decision_queue)
    response = MerchantDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connector=connector,
        connector_status_label=_merchant_connector_status_label(connector.status),
        latest_refresh=latest_refresh,
        latest_refresh_status_label=_merchant_refresh_status_label(latest_refresh)
        if latest_refresh
        else None,
        live_data_available=live_data_available,
        live_data_status_label=_merchant_live_data_status_label(live_data_available),
        product_count=_numeric_metric_or_refresh_summary(
            trusted_facts,
            latest_refresh,
            "total_products",
        ),
        issue_count=_numeric_metric_or_refresh_summary(
            trusted_facts,
            latest_refresh,
            "item_level_issue_count",
        ),
        freshness_assessment=freshness_assessment,
        unknowns=_merchant_unknowns(
            issue_clusters,
            decision_queue,
            product_performance_readiness,
        ),
        product_sample_readiness=product_sample_readiness,
        product_performance_readiness=product_performance_readiness,
        price_impact_readiness=price_impact_readiness,
        operator_summary=_operator_summary(
            decision_queue,
            issue_clusters,
            sections,
            action_ids,
        ),
        issue_clusters=issue_clusters,
        decision_queue=decision_queue,
        sections=sections,
        evidence_ids=_unique(
            [
                *(evidence_id for section in sections for evidence_id in section.evidence_ids),
                *(
                    evidence_id
                    for decision in decision_queue
                    for evidence_id in decision.evidence_ids
                ),
            ]
        ),
        action_ids=_unique(
            [
                *(action_id for section in sections for action_id in section.action_ids),
                *(action_id for decision in decision_queue for action_id in decision.action_ids),
            ]
        ),
        blocker_count=sum(1 for section in sections if section.status == "blocked"),
    )
    return _merchant_response_with_operator_labels(response)


def build_merchant_diagnostics_cached() -> MerchantDiagnosticsResponse:
    """Reuse one Merchant diagnostics build across the initial dashboard reads."""
    cached = _read_merchant_diagnostics_cache()
    if cached is not None:
        return cached
    diagnostics = build_merchant_diagnostics()
    _write_merchant_diagnostics_cache(diagnostics)
    return diagnostics


def clear_merchant_diagnostics_cache() -> None:
    global _cached_merchant_diagnostics
    _cached_merchant_diagnostics = None


def _read_merchant_diagnostics_cache() -> MerchantDiagnosticsResponse | None:
    cache_seconds = _merchant_diagnostics_cache_seconds()
    if cache_seconds <= 0 or _cached_merchant_diagnostics is None:
        return None
    if monotonic() - _cached_merchant_diagnostics.created_at > cache_seconds:
        return None
    return _cached_merchant_diagnostics.diagnostics


def _write_merchant_diagnostics_cache(diagnostics: MerchantDiagnosticsResponse) -> None:
    global _cached_merchant_diagnostics
    if _merchant_diagnostics_cache_seconds() <= 0:
        return
    _cached_merchant_diagnostics = MerchantDiagnosticsCacheEntry(
        created_at=monotonic(),
        diagnostics=diagnostics,
    )


def _merchant_diagnostics_cache_seconds() -> float:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return 0.0
    configured = os.getenv("WILQ_MERCHANT_DIAGNOSTICS_CACHE_SECONDS")
    if configured is None:
        return DEFAULT_MERCHANT_DIAGNOSTICS_CACHE_SECONDS
    try:
        return max(0.0, float(configured))
    except ValueError:
        return DEFAULT_MERCHANT_DIAGNOSTICS_CACHE_SECONDS


def _latest_merchant_refresh() -> ConnectorRefreshRun | None:
    return _latest_connector_refresh(MERCHANT_CONNECTOR_ID)


__all__ = [
    "MerchantDiagnosticsCacheEntry",
    "build_merchant_diagnostics",
    "build_merchant_diagnostics_cached",
    "clear_merchant_diagnostics_cache",
]
