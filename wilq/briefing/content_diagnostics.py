from __future__ import annotations

from collections.abc import Iterable

from wilq.actions.service import list_actions
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionObject,
    ActionRisk,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ContentDiagnosticSection,
    ContentDiagnosticsResponse,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
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
CONTENT_METRIC_FACT_LIMIT = 300


def build_content_diagnostics() -> ContentDiagnosticsResponse:
    connectors = [
        connector
        for connector_id in CONTENT_CONNECTOR_IDS
        if (connector := get_connector_status(connector_id)) is not None
    ]
    latest_refreshes = _latest_refreshes(CONTENT_CONNECTOR_IDS)
    metric_facts = _content_metric_facts(CONTENT_CONNECTOR_IDS)
    live_data_available = _primary_content_data_available(metric_facts, latest_refreshes)
    trusted_facts = metric_facts if live_data_available else []
    tactical_items = [
        item
        for item in build_tactical_queue().items
        if item.domain == OpportunityDomain.gsc_seo
        or item.source_connectors.count("wordpress_ekologus") > 0
    ]
    action_ids = _content_action_ids(list_actions())
    sections = [
        _query_page_section(latest_refreshes, trusted_facts, tactical_items, action_ids),
        _inventory_match_section(latest_refreshes, trusted_facts, tactical_items, action_ids),
        _content_action_safety_section(latest_refreshes, trusted_facts, tactical_items, action_ids),
    ]
    return ContentDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connectors=connectors,
        latest_refreshes=latest_refreshes,
        live_data_available=live_data_available,
        query_page_count=_query_page_count(tactical_items),
        matched_inventory_count=_matched_inventory_count(tactical_items),
        sections=sections,
        evidence_ids=_unique(
            evidence_id for section in sections for evidence_id in section.evidence_ids
        ),
        action_ids=_unique(action_id for section in sections for action_id in section.action_ids),
        blocker_count=sum(1 for section in sections if section.status == "blocked"),
    )


def _content_metric_facts(connector_ids: Iterable[str]) -> list[MetricFact]:
    facts: list[MetricFact] = []
    for connector_id in connector_ids:
        facts.extend(
            metric_store().list_metric_facts(
                connector_id=connector_id,
                limit=CONTENT_METRIC_FACT_LIMIT,
            )
        )
    return facts


def _latest_refreshes(connector_ids: Iterable[str]) -> list[ConnectorRefreshRun]:
    latest: list[ConnectorRefreshRun] = []
    for connector_id in connector_ids:
        runs = list_connector_refresh_runs(connector_id=connector_id)
        if runs:
            latest.append(runs[0])
    return latest


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
        if latest.status != ConnectorRefreshStatus.completed or not latest.vendor_data_collected:
            return False
    return True


def _content_action_ids(actions: list[ActionObject]) -> list[str]:
    return [
        action.id
        for action in actions
        if action.id == "act_prepare_content_refresh_queue"
        or action.domain == OpportunityDomain.content
    ]


def _query_page_section(
    latest_refreshes: list[ConnectorRefreshRun],
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> ContentDiagnosticSection:
    gsc_items = [item for item in tactical_items if item.domain == OpportunityDomain.gsc_seo]
    gsc_facts = [
        fact
        for fact in facts
        if fact.source_connector == "google_search_console"
        and {"query", "page"}.issubset(fact.dimensions)
    ]
    if not gsc_items and not gsc_facts:
        return ContentDiagnosticSection(
            id="content_query_page_matrix",
            title="GSC: brak query/page matrix",
            status="blocked",
            summary=_content_blocker_reason(latest_refreshes, "google_search_console"),
            diagnosis=(
                "WILQ nie ma query/page facts z Google Search Console, więc nie może "
                "wskazać refresh/create/merge bez zmyślania intencji."
            ),
            next_step="Uruchom read-only GSC vendor_read i dopiero potem buduj content queue.",
            source_connectors=["google_search_console"],
            evidence_ids=_refresh_or_connector_evidence_ids(
                latest_refreshes,
                "google_search_console",
            ),
            action_ids=action_ids,
            blocked_claims=["CTR opportunity", "ranking win", "content intent"],
            risk=ActionRisk.medium,
        )
    return ContentDiagnosticSection(
        id="content_query_page_matrix",
        title="GSC: query/page matrix",
        status="ready",
        summary=(
            f"WILQ ma {len(gsc_items)} GSC tactical items i "
            f"{len(gsc_facts)} query/page metric facts."
        ),
        diagnosis=(
            "Query/page matrix pozwala wskazać konkretne strony i zapytania do "
            "refresh/create/merge. To nie jest ogólny brainstorming tematów."
        ),
        next_step="Otwórz najwyższe priorytety i sprawdź intent oraz WordPress match.",
        source_connectors=["google_search_console"],
        evidence_ids=_unique(
            [
                *(fact.evidence_id for fact in gsc_facts),
                *(evidence_id for item in gsc_items for evidence_id in item.evidence_ids),
            ]
        ),
        metric_facts=gsc_facts[:10],
        tactical_items=gsc_items[:8],
        action_ids=action_ids,
        blocked_claims=["lead uplift", "conversion uplift", "revenue impact"],
        risk=ActionRisk.low,
    )


def _inventory_match_section(
    latest_refreshes: list[ConnectorRefreshRun],
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> ContentDiagnosticSection:
    inventory_facts = [
        fact
        for fact in facts
        if fact.source_connector.startswith("wordpress")
        and fact.name
        in {"content_object_count", "content_object_seen", "pages_total", "posts_total"}
    ]
    matched_items = [
        item
        for item in tactical_items
        if item.dimensions.get("wordpress_match") == "found"
    ]
    missing_items = [
        item
        for item in tactical_items
        if item.dimensions.get("wordpress_match") == "missing"
    ]
    if not inventory_facts:
        return ContentDiagnosticSection(
            id="content_inventory_match",
            title="WordPress: brak inventory facts",
            status="blocked",
            summary=_content_blocker_reason(latest_refreshes, "wordpress_ekologus"),
            diagnosis=(
                "WILQ nie ma WordPress inventory, więc nie może odróżnić refresh/merge "
                "od nowej treści bez ryzyka duplikacji."
            ),
            next_step="Odśwież WordPress inventory i dopiero potem generuj briefy treści.",
            source_connectors=["wordpress_ekologus", "wordpress_sklep"],
            evidence_ids=_refresh_or_connector_evidence_ids(
                latest_refreshes,
                "wordpress_ekologus",
            ),
            action_ids=action_ids,
            blocked_claims=["duplicate avoidance", "refresh plan", "merge plan"],
            risk=ActionRisk.medium,
        )
    return ContentDiagnosticSection(
        id="content_inventory_match",
        title="WordPress: inventory protection",
        status="ready",
        summary=(
            f"WILQ ma {len(inventory_facts)} inventory facts, "
            f"{len(matched_items)} matched queue items i {len(missing_items)} missing matches."
        ),
        diagnosis=(
            "WordPress inventory chroni marketera przed pisaniem drugi raz tego samego. "
            "Matched items idą w refresh/merge, missing items wymagają ręcznej kontroli "
            "przed nowym briefem."
        ),
        next_step=(
            "Najpierw obsłuż matched refresh/merge; nowe treści twórz tylko "
            "po duplicate check."
        ),
        source_connectors=_unique(fact.source_connector for fact in inventory_facts),
        evidence_ids=_unique(
            [
                *(fact.evidence_id for fact in inventory_facts),
                *(evidence_id for item in matched_items for evidence_id in item.evidence_ids),
            ]
        ),
        metric_facts=inventory_facts[:10],
        tactical_items=[*matched_items[:5], *missing_items[:3]],
        action_ids=action_ids,
        blocked_claims=["new article without inventory check", "duplicate-free guarantee"],
        risk=ActionRisk.low,
    )


def _content_action_safety_section(
    latest_refreshes: list[ConnectorRefreshRun],
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
) -> ContentDiagnosticSection:
    return ContentDiagnosticSection(
        id="content_action_safety",
        title="Content Planner: bezpieczne akcje",
        status="ready" if facts or tactical_items else "blocked",
        summary="Content actions pozostają prepare-only do czasu walidacji payloadu i audytu.",
        diagnosis=(
            "WILQ może przygotować kolejkę refresh/create/merge/block i payload preview, "
            "ale nie może publikować ani zmieniać WordPress bez walidacji i zgody operatora."
        ),
        next_step="Waliduj `act_prepare_content_refresh_queue` i pokaż payload preview.",
        source_connectors=list(CONTENT_CONNECTOR_IDS),
        evidence_ids=_unique(
            [
                *(
                    evidence_id
                    for refresh in latest_refreshes
                    for evidence_id in refresh.evidence_ids
                ),
                *(evidence_id for item in tactical_items for evidence_id in item.evidence_ids),
            ]
        )
        or [connector_evidence_id("google_search_console")],
        tactical_items=tactical_items[:6],
        action_ids=action_ids,
        blocked_claims=["wordpress write", "auto publish", "ranking guarantee"],
        risk=ActionRisk.medium,
    )


def _query_page_count(items: list[TacticalQueueItem]) -> int:
    return sum(1 for item in items if item.domain == OpportunityDomain.gsc_seo)


def _matched_inventory_count(items: list[TacticalQueueItem]) -> int:
    return sum(1 for item in items if item.dimensions.get("wordpress_match") == "found")


def _content_blocker_reason(
    latest_refreshes: list[ConnectorRefreshRun],
    connector_id: str,
) -> str:
    latest = next((run for run in latest_refreshes if run.connector_id == connector_id), None)
    if latest and latest.errors:
        return latest.errors[0]
    if latest and latest.summary:
        return latest.summary
    return f"Brak wykonanego {connector_id} vendor_read."


def _refresh_or_connector_evidence_ids(
    latest_refreshes: list[ConnectorRefreshRun],
    connector_id: str,
) -> list[str]:
    latest = next((run for run in latest_refreshes if run.connector_id == connector_id), None)
    if latest:
        return latest.evidence_ids
    return [connector_evidence_id(connector_id)]


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values
