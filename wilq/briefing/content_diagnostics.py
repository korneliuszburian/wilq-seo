from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import TypedDict

from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.metric_fact_identity import latest_metric_facts_by_identity
from wilq.briefing.tactical_queue import (
    build_gsc_content_tactical_items,
    build_tactical_queue,
)
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.content.planning.ahrefs import ahrefs_gap_record_decisions
from wilq.content.planning.decisions import (
    content_decision_sort_key,
    gsc_content_decisions,
)
from wilq.content.preflight.marketer_view import (
    build_content_marketer_decision,
    build_content_preflight_item,
    content_blocked_claim_labels,
    content_decision_type_summary_label,
    content_gate_label,
    content_wordpress_match_confidence_label,
    content_wordpress_match_label,
)
from wilq.content.preflight.vendor_read import content_vendor_read_blocker_decision
from wilq.content.view_models.labels import (
    content_connector_with_api_label,
    content_live_data_status_label,
    content_metric_fact_with_api_label,
    content_refresh_with_api_label,
    content_section_with_api_labels,
)
from wilq.content.view_models.sections import (
    content_action_safety_section,
    inventory_match_section,
    query_page_section,
)
from wilq.content.view_models.summary import (
    build_content_operator_summary,
    content_matched_inventory_count,
    content_query_page_count,
)
from wilq.operator_labels import (
    action_count_label,
    evidence_count_label,
    source_connector_labels,
)
from wilq.schemas import (
    ActionObject,
    ConnectorCoveredWindow,
    ConnectorQualityState,
    ConnectorRefreshRun,
    ConnectorSettlementState,
    ConnectorStatus,
    ContentDecisionItem,
    ContentDiagnosticsResponse,
    ContentFreshnessAssessment,
    ContentGscSearchAnalyticsContract,
    ContentPreflightResponse,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
    connector_refresh_has_live_data,
)
from wilq.storage.metric_store import metric_store

CONTENT_CONNECTOR_IDS = (
    "google_search_console",
    "wordpress_ekologus",
    "wordpress_sklep",
    "google_analytics_4",
    "ahrefs",
)
PRIMARY_CONTENT_CONNECTORS = ("google_search_console", "wordpress_ekologus")
# The shop WordPress connector is relevant only when the selected work item is
# a product/shop page. Its freshness must remain visible in quality fields, but
# it cannot block ordinary ekologus.pl content decisions.
OPTIONAL_CONTENT_FRESHNESS_CONNECTORS = {"wordpress_sklep"}
CONTENT_METRIC_FACT_LIMIT = 300
CONTENT_GSC_METRIC_FACT_LIMIT = 1200
CONTENT_WORDPRESS_METRIC_FACT_LIMIT = 1200


class _ContentFreshnessQualityFields(TypedDict):
    connector_refresh_run_ids: dict[str, str]
    connector_covered_windows: dict[str, ConnectorCoveredWindow]
    connector_settlement_states: dict[str, ConnectorSettlementState]
    connector_quality_states: dict[str, ConnectorQualityState]
    connector_quality_caveats: dict[str, list[str]]
CONTENT_STALE_AFTER_HOURS = 48
GSC_CONTENT_KNOWLEDGE_CARD_IDS = (
    "card_gsc_seo_content_playbook",
    "card_wordpress_content_refresh_playbook",
)
GSC_CONTENT_EXPERT_RULE_IDS = (
    "seo_gsc_opportunities_v1",
    "seo_query_page_matrix_v1",
    "content_duplication_rules_v1",
    "content_brief_rules_v1",
)
AHREFS_CONTENT_KNOWLEDGE_CARD_IDS = (
    "card_ahrefs_content_gap_playbook",
    "card_gsc_seo_content_playbook",
    "card_wordpress_content_refresh_playbook",
)
AHREFS_CONTENT_EXPERT_RULE_IDS = (
    "content_brief_rules_v1",
    "content_duplication_rules_v1",
)

# Keep one expensive startup diagnostics build alive through the dashboard's
# initial request waterfall; refresh/mutation paths explicitly invalidate it.
DEFAULT_CONTENT_DIAGNOSTICS_CACHE_SECONDS = 60.0


@dataclass(frozen=True)
class ContentDiagnosticsCacheEntry:
    created_at: float
    refresh_identity: tuple[tuple[str, str, str, tuple[str, ...]], ...]
    diagnostics: ContentDiagnosticsResponse


_cached_content_diagnostics: ContentDiagnosticsCacheEntry | None = None
_content_diagnostics_cache_lock = Lock()


def build_content_diagnostics(
    tactical_items: list[TacticalQueueItem] | None = None,
    actions: list[ActionObject] | None = None,
    metric_facts: list[MetricFact] | None = None,
) -> ContentDiagnosticsResponse:
    connectors = [
        connector
        for connector_id in CONTENT_CONNECTOR_IDS
        if (connector := get_connector_status(connector_id)) is not None
    ]
    connector_freshness = {connector.id: connector.freshness.state for connector in connectors}
    latest_refreshes = _latest_refreshes(CONTENT_CONNECTOR_IDS)
    content_facts_by_connector = None
    if metric_facts is None:
        content_facts_by_connector = _content_metric_facts_by_connector(CONTENT_CONNECTOR_IDS)
        metric_facts = [
            fact
            for connector_facts in content_facts_by_connector.values()
            for fact in connector_facts
        ]
    metric_facts = [content_metric_fact_with_api_label(fact) for fact in metric_facts]
    metric_facts = latest_metric_facts_by_identity(metric_facts)
    live_data_available = _primary_content_data_available(metric_facts, latest_refreshes)
    trusted_facts = metric_facts if live_data_available else []
    all_tactical_items = (
        tactical_items
        if tactical_items is not None
        else build_tactical_queue(facts_by_connector=content_facts_by_connector).items
    )
    content_tactical_items = [
        item
        for item in all_tactical_items
        if item.domain == OpportunityDomain.gsc_seo
        or item.source_connectors.count("wordpress_ekologus") > 0
    ]
    action_ids = _content_action_ids(actions if actions is not None else _list_actions())
    decision_tactical_items = (
        all_tactical_items
        if tactical_items is not None
        else build_gsc_content_tactical_items(
            trusted_facts,
            wordpress_action_ids=action_ids,
        )
    )
    decision_queue = _content_decision_queue(
        decision_tactical_items,
        trusted_facts,
        action_ids,
        latest_refreshes,
        connector_freshness,
    )
    sections = [
        query_page_section(
            latest_refreshes,
            trusted_facts,
            content_tactical_items,
            action_ids,
            knowledge_card_ids=GSC_CONTENT_KNOWLEDGE_CARD_IDS,
            expert_rule_ids=("seo_gsc_opportunities_v1", "seo_query_page_matrix_v1"),
        ),
        inventory_match_section(
            latest_refreshes,
            trusted_facts,
            content_tactical_items,
            action_ids,
            knowledge_card_ids=GSC_CONTENT_KNOWLEDGE_CARD_IDS,
            expert_rule_ids=("content_duplication_rules_v1", "content_brief_rules_v1"),
        ),
        content_action_safety_section(
            latest_refreshes,
            trusted_facts,
            content_tactical_items,
            action_ids,
            content_connector_ids=CONTENT_CONNECTOR_IDS,
        ),
    ]
    sections = [content_section_with_api_labels(section) for section in sections]
    evidence_ids = _unique(
        [
            *(evidence_id for section in sections for evidence_id in section.evidence_ids),
            *(evidence_id for decision in decision_queue for evidence_id in decision.evidence_ids),
        ]
    )
    action_ids = _unique(
        [
            *(action_id for section in sections for action_id in section.action_ids),
            *(action_id for decision in decision_queue for action_id in decision.action_ids),
        ]
    )
    query_page_count = content_query_page_count(content_tactical_items)
    matched_inventory_count = content_matched_inventory_count(content_tactical_items)
    response_source_connectors = _unique(
        [
            *(connector for section in sections for connector in section.source_connectors),
            *(connector for decision in decision_queue for connector in decision.source_connectors),
        ]
    )
    return ContentDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connectors=[content_connector_with_api_label(connector) for connector in connectors],
        latest_refreshes=[content_refresh_with_api_label(refresh) for refresh in latest_refreshes],
        live_data_available=live_data_available,
        live_data_status_label=content_live_data_status_label(live_data_available),
        freshness_assessment=_content_freshness_assessment(
            connectors,
            latest_refreshes,
            live_data_available=live_data_available,
        ),
        gsc_search_analytics_contract=_gsc_search_analytics_contract(latest_refreshes),
        query_page_count=query_page_count,
        matched_inventory_count=matched_inventory_count,
        operator_summary=build_content_operator_summary(
            decision_queue,
            sections,
            action_ids,
            query_page_count=query_page_count,
            matched_inventory_count=matched_inventory_count,
        ),
        marketer_decision=build_content_marketer_decision(decision_queue, sections),
        decision_queue=decision_queue,
        sections=sections,
        evidence_ids=evidence_ids,
        evidence_summary_label=evidence_count_label(evidence_ids),
        source_connector_labels=source_connector_labels(response_source_connectors),
        action_ids=action_ids,
        action_summary_label=action_count_label(action_ids),
        blocker_count=sum(1 for section in sections if section.status == "blocked"),
    )


def build_content_diagnostics_cached() -> ContentDiagnosticsResponse:
    """Reuse one diagnostics build across the initial content workflow reads."""
    refresh_identity = _content_diagnostics_refresh_identity()
    cached = _read_content_diagnostics_cache(refresh_identity)
    if cached is not None:
        return cached
    with _content_diagnostics_cache_lock:
        refresh_identity = _content_diagnostics_refresh_identity()
        cached = _read_content_diagnostics_cache(refresh_identity)
        if cached is not None:
            return cached
        diagnostics = build_content_diagnostics()
        _write_content_diagnostics_cache(diagnostics, refresh_identity)
        return diagnostics


def build_content_freshness_assessment_fast(
    relevant_connector_ids: Iterable[str] | None = None,
) -> ContentFreshnessAssessment:
    """Build only connector freshness for the selected decision read."""
    connectors = [
        connector
        for connector_id in CONTENT_CONNECTOR_IDS
        if (connector := get_connector_status(connector_id)) is not None
    ]
    latest_refreshes = _latest_refreshes(CONTENT_CONNECTOR_IDS)
    latest_by_connector = {refresh.connector_id: refresh for refresh in latest_refreshes}
    live_data_available = all(
        connector_refresh_has_live_data(latest_by_connector[connector_id])
        for connector_id in PRIMARY_CONTENT_CONNECTORS
        if connector_id in latest_by_connector
    ) and all(connector_id in latest_by_connector for connector_id in PRIMARY_CONTENT_CONNECTORS)
    return _content_freshness_assessment(
        connectors,
        latest_refreshes,
        live_data_available=live_data_available,
        relevant_connector_ids=relevant_connector_ids,
    )


def clear_content_diagnostics_cache() -> None:
    global _cached_content_diagnostics
    with _content_diagnostics_cache_lock:
        _cached_content_diagnostics = None


def content_diagnostics_cache_ready() -> bool:
    return (
        _content_diagnostics_cache_seconds() <= 0
        or _read_content_diagnostics_cache(_content_diagnostics_refresh_identity()) is not None
    )


def _read_content_diagnostics_cache(
    refresh_identity: tuple[tuple[str, str, str, tuple[str, ...]], ...] | None = None,
) -> ContentDiagnosticsResponse | None:
    cache_seconds = _content_diagnostics_cache_seconds()
    if cache_seconds <= 0 or _cached_content_diagnostics is None:
        return None
    if monotonic() - _cached_content_diagnostics.created_at > cache_seconds:
        return None
    if (
        refresh_identity is not None
        and refresh_identity != _cached_content_diagnostics.refresh_identity
    ):
        return None
    return _cached_content_diagnostics.diagnostics


def _write_content_diagnostics_cache(
    diagnostics: ContentDiagnosticsResponse,
    refresh_identity: tuple[tuple[str, str, str, tuple[str, ...]], ...],
) -> None:
    global _cached_content_diagnostics
    if _content_diagnostics_cache_seconds() <= 0:
        return
    _cached_content_diagnostics = ContentDiagnosticsCacheEntry(
        created_at=monotonic(),
        refresh_identity=refresh_identity,
        diagnostics=diagnostics,
    )


def _content_diagnostics_refresh_identity() -> tuple[tuple[str, str, str, tuple[str, ...]], ...]:
    latest = _latest_refreshes(CONTENT_CONNECTOR_IDS)
    latest_by_connector = {run.connector_id: run for run in latest}
    return tuple(
        (
            connector_id,
            latest_by_connector[connector_id].id,
            latest_by_connector[connector_id].status.value,
            tuple(latest_by_connector[connector_id].evidence_ids),
        )
        for connector_id in CONTENT_CONNECTOR_IDS
        if connector_id in latest_by_connector
    )


def _content_diagnostics_cache_seconds() -> float:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return 0.0
    configured = os.getenv("WILQ_CONTENT_DIAGNOSTICS_CACHE_SECONDS")
    if configured is None:
        return DEFAULT_CONTENT_DIAGNOSTICS_CACHE_SECONDS
    try:
        return max(0.0, float(configured))
    except ValueError:
        return DEFAULT_CONTENT_DIAGNOSTICS_CACHE_SECONDS


def build_content_preflight(
    diagnostics: ContentDiagnosticsResponse | None = None,
) -> ContentPreflightResponse:
    diagnostics = diagnostics or build_content_diagnostics()
    items = [build_content_preflight_item(decision) for decision in diagnostics.decision_queue]
    primary_item = next((item for item in items if item.status != "blocked"), None)
    source_connectors = _unique(connector for item in items for connector in item.source_connectors)
    return ContentPreflightResponse(
        strict_instruction=(
            "Bramka pisania działa przed planem treści i szkicem. Nie wolno pisać "
            "ani przygotowywać szkicu bez wyniku bramki pisania, planu treści, "
            "sprawdzenia ryzykownych obietnic i decyzji człowieka."
        ),
        primary_item=primary_item or (items[0] if items else None),
        items=items,
        evidence_ids=_unique(evidence_id for item in items for evidence_id in item.evidence_ids),
        source_connectors=source_connectors,
        source_connector_labels=source_connector_labels(source_connectors),
        blocker_count=sum(1 for item in items if item.status == "blocked"),
    )


def _content_metric_facts(connector_ids: Iterable[str]) -> list[MetricFact]:
    facts_by_connector = _content_metric_facts_by_connector(connector_ids)
    facts: list[MetricFact] = []
    for connector_id in connector_ids:
        connector_limit = _content_connector_metric_fact_limit(connector_id)
        facts.extend(facts_by_connector.get(connector_id, [])[:connector_limit])
    return facts


def _content_metric_facts_by_connector(
    connector_ids: Iterable[str],
) -> dict[str, list[MetricFact]]:
    # Content diagnostics only consume the latest fact groups.  The historical
    # ``previous_*`` lineage is intentionally not part of this read model and
    # computing it here forces DuckDB to window over the complete metric store
    # on every cold snapshot (124k+ facts in the local Ekologus store).
    facts_by_connector = metric_store().list_latest_metric_facts_by_connector(
        list(connector_ids),
        limit_per_connector=CONTENT_WORDPRESS_METRIC_FACT_LIMIT,
    )
    return {
        connector_id: facts_by_connector.get(connector_id, [])[
            : _content_connector_metric_fact_limit(connector_id)
        ]
        for connector_id in connector_ids
    }


def _content_connector_metric_fact_limit(connector_id: str) -> int:
    if connector_id == "google_search_console":
        return CONTENT_GSC_METRIC_FACT_LIMIT
    if connector_id.startswith("wordpress"):
        return CONTENT_WORDPRESS_METRIC_FACT_LIMIT
    return CONTENT_METRIC_FACT_LIMIT


def _latest_refreshes(connector_ids: Iterable[str]) -> list[ConnectorRefreshRun]:
    latest: list[ConnectorRefreshRun] = []
    for connector_id in connector_ids:
        runs = list_connector_refresh_runs(connector_id=connector_id)
        if runs:
            latest.append(runs[0])
    return latest


def _content_freshness_assessment(
    connectors: Iterable[ConnectorStatus],
    latest_refreshes: Iterable[ConnectorRefreshRun],
    *,
    live_data_available: bool,
    relevant_connector_ids: Iterable[str] | None = None,
) -> ContentFreshnessAssessment:
    connector_by_id = {connector.id: connector for connector in connectors}
    refresh_by_connector = {refresh.connector_id: refresh for refresh in latest_refreshes}

    missing_ids = [
        connector_id
        for connector_id in PRIMARY_CONTENT_CONNECTORS
        if connector_id not in refresh_by_connector
    ]
    blocked_ids = [
        connector_id
        for connector_id in PRIMARY_CONTENT_CONNECTORS
        if (refresh := refresh_by_connector.get(connector_id)) is not None
        and not connector_refresh_has_live_data(refresh)
    ]
    scoped_connector_ids = set(relevant_connector_ids or CONTENT_CONNECTOR_IDS)
    include_optional_stale = relevant_connector_ids is not None
    stale_ids = [
        connector_id
        for connector_id in scoped_connector_ids
        if include_optional_stale or connector_id not in OPTIONAL_CONTENT_FRESHNESS_CONNECTORS
        if connector_by_id.get(connector_id) is not None
        and connector_by_id[connector_id].freshness.state == "stale"
    ]
    requiring_refresh_ids = _unique([*missing_ids, *blocked_ids, *stale_ids])
    requiring_refresh_labels = [
        _content_connector_short_label(connector_by_id.get(connector_id), connector_id)
        for connector_id in requiring_refresh_ids
    ]
    quality_fields: _ContentFreshnessQualityFields = {
        "connector_refresh_run_ids": {
            connector_id: refresh.id for connector_id, refresh in refresh_by_connector.items()
        },
        "connector_covered_windows": {
            connector_id: refresh.covered_window
            for connector_id, refresh in refresh_by_connector.items()
        },
        "connector_settlement_states": {
            connector_id: refresh.settlement_state
            for connector_id, refresh in refresh_by_connector.items()
        },
        "connector_quality_states": {
            connector_id: refresh.quality_state
            for connector_id, refresh in refresh_by_connector.items()
        },
        "connector_quality_caveats": {
            connector_id: refresh.covered_window.interpretation_caveats
            for connector_id, refresh in refresh_by_connector.items()
            if refresh.covered_window.interpretation_caveats
        },
    }

    if missing_ids:
        return ContentFreshnessAssessment(
            state="missing",
            state_label="brak odczytu treści",
            stale_after_hours=CONTENT_STALE_AFTER_HOURS,
            requires_refresh=True,
            missing_connector_ids=missing_ids,
            blocked_connector_ids=blocked_ids,
            stale_connector_ids=stale_ids,
            connector_labels_requiring_refresh=requiring_refresh_labels,
            **quality_fields,
            summary=(
                "Brakuje podstawowego odczytu danych treści dla: "
                f"{_join_labels(requiring_refresh_labels)}."
            ),
            next_step=(
                "Uruchom odczyt GSC i WordPress przed decyzją o odświeżeniu, "
                "scaleniu albo utworzeniu treści."
            ),
        )

    if blocked_ids or not live_data_available:
        blocked_labels = [
            _content_connector_short_label(connector_by_id.get(connector_id), connector_id)
            for connector_id in (blocked_ids or list(PRIMARY_CONTENT_CONNECTORS))
        ]
        return ContentFreshnessAssessment(
            state="blocked",
            state_label="odczyt treści zablokowany",
            stale_after_hours=CONTENT_STALE_AFTER_HOURS,
            requires_refresh=True,
            missing_connector_ids=missing_ids,
            blocked_connector_ids=blocked_ids,
            stale_connector_ids=stale_ids,
            connector_labels_requiring_refresh=requiring_refresh_labels or blocked_labels,
            **quality_fields,
            summary=(
                "Podstawowe dane treści nie mają pełnego odczytu metryk dla: "
                f"{_join_labels(blocked_labels)}."
            ),
            next_step=(
                "Napraw blocker odczytu i uruchom ponownie GSC i WordPress, zanim WILQ "
                "zarekomenduje aktualną decyzję contentową."
            ),
        )

    if stale_ids:
        return ContentFreshnessAssessment(
            state="stale",
            state_label="dane treści wymagają odświeżenia",
            stale_after_hours=CONTENT_STALE_AFTER_HOURS,
            requires_refresh=True,
            missing_connector_ids=missing_ids,
            blocked_connector_ids=blocked_ids,
            stale_connector_ids=stale_ids,
            connector_labels_requiring_refresh=requiring_refresh_labels,
            **quality_fields,
            summary=(
                "Dane treści są do odświeżenia dla: "
                f"{_join_labels(requiring_refresh_labels)}. "
                "Można je czytać jako review nieświeżych sygnałów, ale nie jako "
                "bieżącą decyzję publikacyjną."
            ),
            next_step=(
                "Uruchom odczyt danych dla wskazanych źródeł, jeśli pytanie dotyczy "
                "aktualnych zapytań, spisu treści, luk Ahrefs albo jakości ruchu."
            ),
        )

    return ContentFreshnessAssessment(
        state="fresh",
        state_label="dane treści świeże",
        stale_after_hours=CONTENT_STALE_AFTER_HOURS,
        requires_refresh=False,
        **quality_fields,
        summary=(
            f"Podstawowe dane treści mieszczą się w progu {CONTENT_STALE_AFTER_HOURS}h."
        ),
        next_step="Można użyć content diagnostics do review bez dodatkowego odświeżenia.",
    )


def _gsc_search_analytics_contract(
    latest_refreshes: Iterable[ConnectorRefreshRun],
) -> ContentGscSearchAnalyticsContract | None:
    refresh = next(
        (
            item
            for item in latest_refreshes
            if item.connector_id == "google_search_console"
            and connector_refresh_has_live_data(item)
        ),
        None,
    )
    if refresh is None:
        return None
    summary = refresh.metric_summary
    if summary.get("api") != "search_console_search_analytics":
        return None
    detail_date_end = _optional_text(summary.get("date_end"))
    row_limit = _optional_int(summary.get("query_page_row_limit"))
    max_rows = _optional_int(summary.get("query_page_max_rows"))
    rows_truncated = _bool_metric(summary.get("query_page_rows_truncated"))
    aggregate_clicks = _optional_int(summary.get("aggregate_clicks"))
    aggregate_impressions = _optional_int(summary.get("aggregate_impressions"))
    return ContentGscSearchAnalyticsContract(
        evidence_ids=refresh.evidence_ids,
        data_availability_checked=_bool_metric(summary.get("data_availability_checked")),
        date_availability_status=_text(summary.get("date_availability_status")),
        availability_date_start=_optional_text(summary.get("availability_date_start")),
        availability_date_end=_optional_text(summary.get("availability_date_end")),
        detail_date_start=_optional_text(summary.get("date_start")),
        detail_date_end=detail_date_end,
        latest_available_detail_date=detail_date_end,
        search_type=_text(summary.get("search_type")),
        detail_dimensions=_text(summary.get("detail_dimensions")),
        detail_data_completeness=_text(summary.get("detail_data_completeness")),
        query_page_row_limit=row_limit,
        query_page_max_rows=max_rows,
        query_page_rows_truncated=rows_truncated,
        aggregate_date_start=_optional_text(summary.get("aggregate_date_start")),
        aggregate_date_end=_optional_text(summary.get("aggregate_date_end")),
        aggregate_dimensions=_text(summary.get("aggregate_dimensions")),
        aggregate_aggregation_type=_text(summary.get("aggregate_aggregation_type")),
        aggregate_data_completeness=_text(summary.get("aggregate_data_completeness")),
        aggregate_row_count=_optional_int(summary.get("aggregate_row_count")),
        aggregate_clicks=aggregate_clicks,
        aggregate_impressions=aggregate_impressions,
        aggregate_ctr=_optional_float(summary.get("aggregate_ctr")),
        aggregate_average_position=_optional_float(summary.get("aggregate_average_position")),
        aggregate_summary_label=_gsc_aggregate_summary_label(
            aggregate_clicks,
            aggregate_impressions,
            _optional_text(summary.get("aggregate_date_end")),
        ),
        summary_label=_gsc_search_analytics_summary_label(detail_date_end),
        partial_detail_warning_label=(
            "Częściowe dane zapytań i adresów z Search Analytics są sygnałem "
            "do decyzji treściowej, nie pełną sumą całego ruchu."
        ),
        paging_label=_gsc_search_analytics_paging_label(row_limit, max_rows, rows_truncated),
        official_limits_label=(
            "Oficjalny wzorzec GSC: dane zwykle pojawiają się po 2-3 dniach; "
            "dla pełniejszych odczytów pobieraj pojedynczy dzień i stronicuj "
            "do 25 000 wierszy na żądanie, maksymalnie 50 000 wierszy dziennie "
            "dla danego typu wyszukiwania."
        ),
        wilq_internal_cap_label=(
            "Ten odczyt WILQ jest operacyjnie ograniczony do zapytań i adresów "
            f"rowLimit={row_limit or 'unknown'} i max rows={max_rows or 'unknown'}; "
            "to bezpieczny sygnał decyzyjny, nie eksport całego Search Analytics."
        ),
    )


def _gsc_search_analytics_summary_label(detail_date_end: str | None) -> str:
    if detail_date_end:
        return (
            "GSC Search Analytics: najnowszy dostępny dzień szczegółów "
            f"{detail_date_end}; zapytania i adresy mogą być częściowe."
        )
    return "GSC Search Analytics: brak potwierdzonego dnia szczegółów zapytań i adresów."


def _gsc_aggregate_summary_label(
    clicks: int | None,
    impressions: int | None,
    aggregate_date_end: str | None,
) -> str:
    if clicks is None or impressions is None or not aggregate_date_end:
        return "GSC Search Analytics: brak osobnego agregatu ruchu bez wymiarów zapytań i adresów."
    return (
        "Agregat GSC bez wymiarów zapytań i adresów: "
        f"{clicks} kliknięć i {impressions} wyświetleń dla dnia {aggregate_date_end}."
    )


def _gsc_search_analytics_paging_label(
    row_limit: int | None,
    max_rows: int | None,
    rows_truncated: bool,
) -> str:
    if row_limit is None or max_rows is None:
        return "Brak potwierdzonej informacji o stronicowaniu zapytań i adresów."
    truncation = "wynik mógł zostać ucięty" if rows_truncated else "wynik nie zgłasza ucięcia"
    return (
        f"Paginacja zapytań i adresów: rowLimit={row_limit}, max rows={max_rows}; "
        f"{truncation}."
    )


def _content_connector_short_label(
    connector: ConnectorStatus | None,
    connector_id: str,
) -> str:
    if connector is not None and connector.label:
        return connector.label
    labels = {
        "google_search_console": "Google Search Console",
        "wordpress_ekologus": "WordPress ekologus.pl",
        "wordpress_sklep": "WordPress sklep.ekologus.pl",
        "google_analytics_4": "Google Analytics 4",
        "ahrefs": "Ahrefs",
    }
    return labels.get(connector_id, connector_id)


def _join_labels(labels: Iterable[str]) -> str:
    values = [label for label in labels if label]
    if not values:
        return "brak wskazanych źródeł"
    if len(values) == 1:
        return values[0]
    return ", ".join(values[:-1]) + f" i {values[-1]}"


def _optional_text(value: object) -> str | None:
    text = _text(value)
    return text or None


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _optional_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _bool_metric(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    if isinstance(value, int):
        return value != 0
    return False


def _primary_content_data_available(
    facts: list[MetricFact],
    latest_refreshes: list[ConnectorRefreshRun],
) -> bool:
    fact_connectors = {fact.source_connector for fact in facts}
    if not set(PRIMARY_CONTENT_CONNECTORS).issubset(fact_connectors):
        return False
    latest_by_connector = {run.connector_id: run for run in latest_refreshes}
    for connector_id in PRIMARY_CONTENT_CONNECTORS:
        latest = latest_by_connector.get(connector_id)
        if latest is None:
            continue
        if not connector_refresh_has_live_data(latest):
            return False
    return True


def _content_action_ids(actions: list[ActionObject]) -> list[str]:
    # Content diagnostics is the marketer's decision queue, not the full
    # content action registry. Draft handoff and Service Profile promotion
    # actions belong to their own reviewed workflow seams and must not inflate
    # the queue's single safe next action.
    return [
        action.id
        for action in actions
        if action.id == "act_prepare_content_refresh_queue"
    ]


def _list_actions() -> list[ActionObject]:
    from wilq.actions.service import list_actions_cached

    return list_actions_cached()


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values


def _content_decision_with_api_labels(decision: ContentDecisionItem) -> ContentDecisionItem:
    return decision.model_copy(
        update={
            "decision_type_label": content_decision_type_summary_label(decision.decision_type),
            "evidence_summary_label": evidence_count_label(decision.evidence_ids),
            "action_summary_label": action_count_label(decision.action_ids),
            "wordpress_match_label": content_wordpress_match_label(decision.wordpress_match),
            "wordpress_match_confidence_label": content_wordpress_match_confidence_label(
                decision.wordpress_match_confidence
            ),
            "inventory_gate_status_label": content_gate_label(decision.inventory_gate_status),
            "canonical_gate_status_label": content_gate_label(decision.canonical_gate_status),
            "duplicate_gate_status_label": content_gate_label(decision.duplicate_gate_status),
            "blocked_claim_labels": content_blocked_claim_labels(decision.blocked_claims),
            "metric_facts": [
                content_metric_fact_with_api_label(fact) for fact in decision.metric_facts
            ],
        }
    )


def _content_decision_queue(
    items: list[TacticalQueueItem],
    metric_facts: list[MetricFact],
    action_ids: list[str],
    latest_refreshes: list[ConnectorRefreshRun],
    connector_freshness: Mapping[str, str] | None = None,
) -> list[ContentDecisionItem]:
    decisions = [
        *gsc_content_decisions(
            items,
            knowledge_card_ids=GSC_CONTENT_KNOWLEDGE_CARD_IDS,
            expert_rule_ids=GSC_CONTENT_EXPERT_RULE_IDS,
        ),
        *ahrefs_gap_record_decisions(
            metric_facts,
            action_ids,
            knowledge_card_ids=AHREFS_CONTENT_KNOWLEDGE_CARD_IDS,
            expert_rule_ids=AHREFS_CONTENT_EXPERT_RULE_IDS,
        ),
    ]
    if decisions:
        return [
            _content_decision_with_api_labels(decision)
            for decision in _rank_content_decisions_for_diagnostics(
                decisions,
                connector_freshness or {},
            )
        ]
    return [
        _content_decision_with_api_labels(
            content_vendor_read_blocker_decision(
                latest_refreshes,
                action_ids,
                knowledge_card_ids=GSC_CONTENT_KNOWLEDGE_CARD_IDS,
                expert_rule_ids=GSC_CONTENT_EXPERT_RULE_IDS,
            )
        )
    ]


def _rank_content_decisions_for_diagnostics(
    decisions: list[ContentDecisionItem],
    connector_freshness: Mapping[str, str],
) -> list[ContentDecisionItem]:
    has_fresh_primary_ready = any(
        _decision_has_fresh_primary_content(decision, connector_freshness) for decision in decisions
    )

    def sort_key(decision: ContentDecisionItem) -> tuple[int, int, int, int, int, str]:
        base = content_decision_sort_key(decision)
        stale_secondary_penalty = (
            1
            if has_fresh_primary_ready
            and decision.decision_type == "review_ahrefs_gap_records"
            and _decision_has_stale_secondary_source(decision, connector_freshness)
            else 0
        )
        return (
            base[0],
            stale_secondary_penalty,
            base[1],
            base[2],
            base[3],
            base[4],
        )

    return sorted(decisions, key=sort_key)


def _decision_has_fresh_primary_content(
    decision: ContentDecisionItem,
    connector_freshness: Mapping[str, str],
) -> bool:
    if decision.status != "ready":
        return False
    return any(
        connector in PRIMARY_CONTENT_CONNECTORS and connector_freshness.get(connector) == "fresh"
        for connector in decision.source_connectors
    )


def _decision_has_stale_secondary_source(
    decision: ContentDecisionItem,
    connector_freshness: Mapping[str, str],
) -> bool:
    return any(
        connector not in PRIMARY_CONTENT_CONNECTORS
        and connector_freshness.get(connector) == "stale"
        for connector in decision.source_connectors
    )
