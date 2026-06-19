from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

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
    ContentDecisionItem,
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
ContentDecisionType = Literal[
    "refresh_or_merge",
    "merge_create_after_inventory_check",
    "inventory_check_before_create",
    "block_as_tracking_not_content",
]


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
    all_tactical_items = build_tactical_queue().items
    tactical_items = [
        item
        for item in all_tactical_items
        if item.domain == OpportunityDomain.gsc_seo
        or item.source_connectors.count("wordpress_ekologus") > 0
    ]
    decision_queue = _content_decision_queue(all_tactical_items)
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
        decision_queue=decision_queue,
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
            title="GSC: brak metryk zapytań i URL",
            status="blocked",
            summary=_content_blocker_reason(latest_refreshes, "google_search_console"),
            diagnosis=(
                "WILQ nie ma metryk zapytań i URL-i z Google Search Console, więc nie może "
                "wskazać refresh/create/merge bez zmyślania intencji."
            ),
            next_step=(
                "Uruchom odczyt GSC w trybie vendor_read i dopiero potem buduj "
                "kolejkę treści."
            ),
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
        title="GSC: zapytania i URL-e",
        status="ready",
        summary=(
            f"WILQ ma {len(gsc_items)} zadań GSC i "
            f"{len(gsc_facts)} metryk zapytań i URL-i."
        ),
        diagnosis=(
            "Macierz zapytań i URL-i pozwala wskazać konkretne strony do "
            "odświeżenia, scalenia albo kontroli. To nie jest ogólny brainstorming tematów."
        ),
        next_step="Otwórz najwyższe priorytety i sprawdź intencję oraz dopasowanie WordPress.",
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
            title="WordPress: brak metryk inventory",
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
        title="WordPress: ochrona przed duplikacją",
        status="ready",
        summary=(
            f"WILQ ma {len(inventory_facts)} metryk inventory, "
            f"{len(matched_items)} potwierdzonych dopasowań i "
            f"{len(missing_items)} braków dopasowania."
        ),
        diagnosis=(
            "WordPress inventory chroni marketera przed pisaniem drugi raz tego samego. "
            "Potwierdzone dopasowania idą w odświeżenie lub scalenie, a brak "
            "dopasowania wymaga ręcznej kontroli przed nowym briefem."
        ),
        next_step=(
            "Najpierw obsłuż potwierdzone odświeżenia i scalenia; nowe treści "
            "twórz tylko po kontroli duplikacji."
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
        title="Bezpieczeństwo akcji contentowych",
        status="ready" if facts or tactical_items else "blocked",
        summary=(
            "Akcje contentowe pozostają w trybie przygotowania do czasu walidacji "
            "payloadu i audytu."
        ),
        diagnosis=(
            "WILQ może przygotować kolejkę odświeżenia, tworzenia, scalania albo "
            "blokowania oraz podgląd payloadu, ale nie może publikować ani zmieniać "
            "WordPress bez walidacji i zgody operatora."
        ),
        next_step="Waliduj `act_prepare_content_refresh_queue` i pokaż podgląd payloadu.",
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


def _content_decision_queue(items: list[TacticalQueueItem]) -> list[ContentDecisionItem]:
    decisions = [
        *_gsc_content_decisions(items),
        *_ga4_tracking_gap_decisions(items),
    ]
    return sorted(decisions, key=lambda decision: (decision.risk.value, decision.id))[:5]


def _gsc_content_decisions(items: list[TacticalQueueItem]) -> list[ContentDecisionItem]:
    page_groups: dict[str, list[TacticalQueueItem]] = {}
    for item in _unique_tactical_items(items):
        if item.domain != OpportunityDomain.gsc_seo:
            continue
        page = item.dimensions.get("page")
        if page:
            page_groups.setdefault(page, []).append(item)

    decisions: list[ContentDecisionItem] = []
    for page, page_items in page_groups.items():
        first = page_items[0]
        wordpress_match = first.dimensions.get("wordpress_match", "missing")
        query_count = _int_dimension(first, "gsc_page_query_count", len(page_items))
        queries = _unique(
            item.dimensions.get("query")
            for item in page_items
            if item.dimensions.get("query")
        )
        metric_facts = _unique_metric_facts(
            fact for item in page_items for fact in item.metric_facts
        )
        decision_type: ContentDecisionType
        if wordpress_match == "found":
            decision_type = "refresh_or_merge"
            title = f"Odśwież lub scal istniejącą treść: {page}"
            next_step = (
                "Przygotuj brief odświeżenia albo scalenia na podstawie GSC "
                "i inventory WordPress."
            )
            rationale = "Inventory WordPress potwierdza istniejącą stronę dla zapytania z GSC."
        elif query_count > 1:
            decision_type = "merge_create_after_inventory_check"
            title = f"Zweryfikuj klaster zapytań przed tworzeniem treści: {page}"
            next_step = (
                "Sprawdź mapowanie URL i duplikaty w WordPress przed utworzeniem "
                "albo odtworzeniem strony."
            )
            rationale = (
                "Wiele zapytań prowadzi do jednego URL, ale inventory nie potwierdza strony."
            )
        else:
            decision_type = "inventory_check_before_create"
            title = f"Sprawdź inventory przed briefem treści: {page}"
            next_step = "Najpierw potwierdź, czy URL istnieje w WordPress lub sitemap."
            rationale = "GSC pokazuje popyt, ale WordPress inventory nie potwierdza URL."
        decisions.append(
            ContentDecisionItem(
                id=f"content_decision_{_slug(page)}",
                decision_type=decision_type,
                title=title,
                page=page,
                normalized_page_path=first.dimensions.get("wordpress_requested_path"),
                queries=queries,
                query_count=query_count,
                wordpress_match=wordpress_match,
                wordpress_match_confidence=first.dimensions.get("wordpress_match_confidence"),
                wordpress_content_url=first.dimensions.get("wordpress_content_url"),
                source_connectors=_unique(
                    connector for item in page_items for connector in item.source_connectors
                ),
                evidence_ids=_unique(
                    evidence_id for item in page_items for evidence_id in item.evidence_ids
                ),
                metric_facts=metric_facts[:8],
                action_ids=_unique(
                    action_id for item in page_items for action_id in item.action_ids
                ),
                blocked_claims=_unique(
                    claim for item in page_items for claim in item.blocked_claims
                ),
                rationale=rationale,
                next_step=next_step,
                risk=ActionRisk.medium if wordpress_match == "missing" else ActionRisk.low,
            )
        )
    return decisions


def _ga4_tracking_gap_decisions(items: list[TacticalQueueItem]) -> list[ContentDecisionItem]:
    tracking_gaps = [
        item
        for item in _unique_tactical_items(items)
        if item.domain == OpportunityDomain.ga4 and item.intent == "tracking_gap"
    ]
    if not tracking_gaps:
        return []
    evidence_ids = _unique(
        evidence_id for item in tracking_gaps for evidence_id in item.evidence_ids
    )
    metric_facts = _unique_metric_facts(
        fact for item in tracking_gaps for fact in item.metric_facts
    )
    return [
        ContentDecisionItem(
            id="content_decision_ga4_tracking_gap_block",
            decision_type="block_as_tracking_not_content",
            title="Zablokuj GA4 tracking gaps jako zadania contentowe",
            source_connectors=["google_analytics_4"],
            evidence_ids=evidence_ids,
            metric_facts=metric_facts[:8],
            action_ids=_unique(
                action_id for item in tracking_gaps for action_id in item.action_ids
            ),
            blocked_claims=_unique(
                [
                    *(claim for item in tracking_gaps for claim in item.blocked_claims),
                    "content rewrite",
                    "conversion uplift",
                    "ROAS",
                ]
            ),
            rationale=(
                "GA4 `(not set)` i tracking_gap wskazują problem pomiaru, "
                "nie gotową rekomendację treści."
            ),
            next_step="Przekaż do GA4 tracking review zamiast tworzyć content rewrite.",
            risk=ActionRisk.medium,
        )
    ]


def _unique_tactical_items(items: Iterable[TacticalQueueItem]) -> list[TacticalQueueItem]:
    unique_items: dict[str, TacticalQueueItem] = {}
    for item in items:
        unique_items.setdefault(item.id, item)
    return list(unique_items.values())


def _unique_metric_facts(facts: Iterable[MetricFact]) -> list[MetricFact]:
    unique_facts: dict[tuple[str, str, tuple[tuple[str, str], ...]], MetricFact] = {}
    for fact in facts:
        key = (
            fact.source_connector,
            fact.name,
            tuple(sorted((str(key), str(value)) for key, value in fact.dimensions.items())),
        )
        unique_facts.setdefault(key, fact)
    return list(unique_facts.values())


def _int_dimension(item: TacticalQueueItem, key: str, fallback: int) -> int:
    try:
        return int(item.dimensions.get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def _slug(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value.lower()).strip(
        "_"
    )[:80]
