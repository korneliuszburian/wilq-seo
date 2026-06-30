from __future__ import annotations

from collections.abc import Iterable

from wilq.actions.content_refresh import content_contract_label
from wilq.actions.service import list_actions
from wilq.briefing.marketing_brief import STRICT_BRIEF_INSTRUCTION
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import get_connector_status
from wilq.content.canonical.urls import content_decision_has_public_final_canonical
from wilq.content.measurement.decisions import ga4_tracking_gap_decisions
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
from wilq.content.preflight.vendor_read import (
    content_blocker_reason,
    content_vendor_read_blocker_decision,
    refresh_or_connector_evidence_ids,
)
from wilq.evidence.registry import connector_evidence_id
from wilq.operator_labels import (
    action_count_label,
    evidence_count_label,
    source_connector_label,
    source_connector_labels,
)
from wilq.schemas import (
    ActionObject,
    ActionRisk,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorStatus,
    ContentDecisionItem,
    ContentDiagnosticSection,
    ContentDiagnosticsResponse,
    ContentOperatorSummary,
    ContentPreflightResponse,
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
CONTENT_GSC_METRIC_FACT_LIMIT = 1200
CONTENT_WORDPRESS_METRIC_FACT_LIMIT = 1200
GSC_CONTENT_KNOWLEDGE_CARD_IDS = (
    "card_gsc_seo_content_playbook",
    "card_wordpress_content_refresh_playbook",
)
GSC_CONTENT_EXPERT_RULE_IDS = (
    "seo_gsc_opportunities_v1",
    "seo_query_page_matrix_v1",
    "seo_content_decay_v1",
    "seo_cannibalization_v1",
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
GA4_TRACKING_KNOWLEDGE_CARD_IDS = ("card_ga4_behavior_diagnostics_playbook",)
GA4_TRACKING_EXPERT_RULE_IDS = ("ga4_diagnostics_v1",)
CONTENT_CONNECTOR_STATUS_LABELS = {
    "configured": "dostęp skonfigurowany",
    "missing_credentials": "brakuje dostępu",
    "disabled": "źródło wyłączone",
    "missing_dependency": "brak zależności",
    "unreachable": "źródło niedostępne",
    "auth_error": "błąd dostępu",
    "rate_limited": "limit odczytu",
    "error": "błąd źródła",
}
CONTENT_REFRESH_STATUS_LABELS = {
    "completed": "zakończony",
    "blocked": "zablokowany",
    "failed": "błąd",
}
CONTENT_METRIC_FACT_LABELS = {
    "ahrefs_backlink_gap_count": "Luki linków z Ahrefs",
    "ahrefs_competitor_page_count": "Strony konkurencji z Ahrefs",
    "ahrefs_content_gap_count": "Luki treści z Ahrefs",
    "ahrefs_organic_keyword_gap_count": "Luki fraz z Ahrefs",
    "ahrefs_referring_domain_gap_count": "Luki domen linkujących z Ahrefs",
    "ahrefs_top_page_gap_count": "Mocne strony konkurencji",
    "average_position": "Pozycja",
    "clicks": "Kliknięcia",
    "content_object_count": "Obiekty WordPress",
    "content_object_seen": "Treść w spisie",
    "ctr": "CTR",
    "engaged_sessions": "Sesje zaangażowane",
    "engagement_rate": "Współczynnik zaangażowania",
    "impressions": "Wyświetlenia",
    "pages_total": "Strony WordPress",
    "posts_total": "Wpisy WordPress",
    "sessions": "Sesje",
}
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
    latest_refreshes = _latest_refreshes(CONTENT_CONNECTOR_IDS)
    metric_facts = (
        metric_facts if metric_facts is not None else _content_metric_facts(CONTENT_CONNECTOR_IDS)
    )
    metric_facts = [_content_metric_fact_with_api_label(fact) for fact in metric_facts]
    live_data_available = _primary_content_data_available(metric_facts, latest_refreshes)
    trusted_facts = metric_facts if live_data_available else []
    all_tactical_items = (
        tactical_items if tactical_items is not None else build_tactical_queue().items
    )
    content_tactical_items = [
        item
        for item in all_tactical_items
        if item.domain == OpportunityDomain.gsc_seo
        or item.source_connectors.count("wordpress_ekologus") > 0
    ]
    action_ids = _content_action_ids(actions if actions is not None else list_actions())
    decision_queue = _content_decision_queue(
        all_tactical_items,
        trusted_facts,
        action_ids,
        latest_refreshes,
    )
    sections = [
        _query_page_section(latest_refreshes, trusted_facts, content_tactical_items, action_ids),
        _inventory_match_section(
            latest_refreshes,
            trusted_facts,
            content_tactical_items,
            action_ids,
        ),
        _content_action_safety_section(
            latest_refreshes,
            trusted_facts,
            content_tactical_items,
            action_ids,
        ),
    ]
    sections = [_content_section_with_api_labels(section) for section in sections]
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
    query_page_count = _query_page_count(content_tactical_items)
    matched_inventory_count = _matched_inventory_count(content_tactical_items)
    response_source_connectors = _unique(
        [
            *(connector for section in sections for connector in section.source_connectors),
            *(connector for decision in decision_queue for connector in decision.source_connectors),
        ]
    )
    return ContentDiagnosticsResponse(
        strict_instruction=STRICT_BRIEF_INSTRUCTION,
        connectors=[_content_connector_with_api_label(connector) for connector in connectors],
        latest_refreshes=[_content_refresh_with_api_label(refresh) for refresh in latest_refreshes],
        live_data_available=live_data_available,
        live_data_status_label=_content_live_data_status_label(live_data_available),
        query_page_count=query_page_count,
        matched_inventory_count=matched_inventory_count,
        operator_summary=_operator_summary(
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


def _operator_summary(
    decisions: list[ContentDecisionItem],
    sections: list[ContentDiagnosticSection],
    action_ids: list[str],
    *,
    query_page_count: int,
    matched_inventory_count: int,
) -> ContentOperatorSummary:
    top_decisions = decisions[:4]
    current_site_match_count = sum(
        1 for decision in decisions if content_decision_has_public_final_canonical(decision)
    )
    ahrefs_wordpress_overlap_count = _ahrefs_wordpress_overlap_count(decisions)
    return ContentOperatorSummary(
        title="Co marketer ma zrobić teraz z treściami",
        summary=(
            "WILQ łączy zapytania i adresy z GSC ze spisem treści WordPress. "
            "Najpierw obsłuż istniejące URL-e i klastry zapytań, potem dopiero "
            "twórz nowe treści. Bez dowodów nie wolno twierdzić, że wzrosną "
            "leady, pozycje albo konwersje."
        ),
        next_step=(
            "Przejdź przez top decyzje contentowe: odśwież, scal, utwórz albo "
            "zablokuj. Potem sprawdź w WILQ tylko właściwą akcję."
        ),
        top_decision_ids=[decision.id for decision in top_decisions],
        confirmed_wordpress_count=sum(
            1 for decision in decisions if decision.wordpress_match == "found"
        ),
        missing_wordpress_count=sum(
            1 for decision in decisions if decision.wordpress_match == "missing"
        ),
        current_site_match_count=current_site_match_count,
        decision_type_labels=_unique(
            content_decision_type_summary_label(decision.decision_type) for decision in decisions
        ),
        source_connectors=_unique(
            connector for decision in top_decisions for connector in decision.source_connectors
        ),
        evidence_ids=_unique(
            evidence_id for decision in top_decisions for evidence_id in decision.evidence_ids
        ),
        evidence_summary_label=evidence_count_label(
            _unique(
                evidence_id for decision in top_decisions for evidence_id in decision.evidence_ids
            )
        ),
        action_ids=action_ids,
        action_summary_label=action_count_label(action_ids),
        blocked_claims=_unique(claim for section in sections for claim in section.blocked_claims),
        blocked_claim_labels=content_blocked_claim_labels(
            claim for section in sections for claim in section.blocked_claims
        ),
        metric_tiles={
            "Zapytania i adresy z GSC": query_page_count,
            "Treści znalezione w WordPress": matched_inventory_count,
            "Luki Ahrefs powiązane z WordPress": ahrefs_wordpress_overlap_count,
            "Decyzje treści": len(decisions),
        },
    )


def _ahrefs_wordpress_overlap_count(decisions: list[ContentDecisionItem]) -> int:
    for decision in decisions:
        if decision.decision_type == "review_ahrefs_gap_records":
            value = decision.metric_tiles.get("Powiązanie z WordPress")
            if isinstance(value, (int, float)):
                return int(value)
    return 0


def _content_metric_facts(connector_ids: Iterable[str]) -> list[MetricFact]:
    facts_by_connector = metric_store().list_metric_facts_by_connector(
        list(connector_ids),
        limit_per_connector=CONTENT_WORDPRESS_METRIC_FACT_LIMIT,
    )
    facts: list[MetricFact] = []
    for connector_id in connector_ids:
        connector_limit = _content_connector_metric_fact_limit(connector_id)
        facts.extend(facts_by_connector.get(connector_id, [])[:connector_limit])
    return facts


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
            summary=content_blocker_reason(latest_refreshes, "google_search_console"),
            diagnosis=(
                "WILQ nie ma metryk zapytań i URL-i z Google Search Console, więc nie może "
                "wskazać odświeżenia, nowej treści ani scalenia bez zmyślania intencji."
            ),
            next_step=("Uruchom odczyt danych z GSC i dopiero potem buduj kolejkę treści."),
            source_connectors=["google_search_console"],
            evidence_ids=refresh_or_connector_evidence_ids(
                latest_refreshes,
                "google_search_console",
            ),
            action_ids=action_ids,
            knowledge_card_ids=["card_gsc_seo_content_playbook"],
            expert_rule_ids=[
                "seo_gsc_opportunities_v1",
                "seo_query_page_matrix_v1",
            ],
            blocked_claims=["CTR opportunity", "ranking win", "content intent"],
            risk=ActionRisk.medium,
        )
    return ContentDiagnosticSection(
        id="content_query_page_matrix",
        title="GSC: zapytania i URL-e",
        status="ready",
        summary=(f"WILQ ma {len(gsc_items)} zadań GSC i {len(gsc_facts)} metryk zapytań i URL-i."),
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
        knowledge_card_ids=list(GSC_CONTENT_KNOWLEDGE_CARD_IDS),
        expert_rule_ids=[
            "seo_gsc_opportunities_v1",
            "seo_query_page_matrix_v1",
        ],
        blocked_claims=["wzrost liczby leadów", "wzrost konwersji", "wpływ na przychód"],
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
        item for item in tactical_items if item.dimensions.get("wordpress_match") == "found"
    ]
    missing_items = [
        item for item in tactical_items if item.dimensions.get("wordpress_match") == "missing"
    ]
    if not inventory_facts:
        return ContentDiagnosticSection(
            id="content_inventory_match",
            title="WordPress: brak spisu treści",
            status="blocked",
            summary=content_blocker_reason(latest_refreshes, "wordpress_ekologus"),
            diagnosis=(
                "WILQ nie ma spisu treści WordPress, więc nie może odróżnić "
                "odświeżenia albo scalenia od nowej treści bez ryzyka duplikacji."
            ),
            next_step="Odśwież spis treści WordPress i dopiero potem przygotuj plany treści.",
            source_connectors=["wordpress_ekologus", "wordpress_sklep"],
            evidence_ids=refresh_or_connector_evidence_ids(
                latest_refreshes,
                "wordpress_ekologus",
            ),
            action_ids=action_ids,
            knowledge_card_ids=["card_wordpress_content_refresh_playbook"],
            expert_rule_ids=["content_duplication_rules_v1", "content_brief_rules_v1"],
            blocked_claims=[
                "uniknięcie duplikacji",
                "plan odświeżenia",
                "plan scalenia",
            ],
            risk=ActionRisk.medium,
        )
    return ContentDiagnosticSection(
        id="content_inventory_match",
        title="WordPress: ochrona przed duplikacją",
        status="ready",
        summary=(
            f"WILQ ma {len(inventory_facts)} metryk spisu treści, "
            f"{len(matched_items)} potwierdzonych dopasowań i "
            f"{len(missing_items)} braków dopasowania."
        ),
        diagnosis=(
            "Spis treści WordPress chroni marketera przed pisaniem drugi raz tego samego. "
            "Potwierdzone dopasowania idą w odświeżenie lub scalenie, a brak "
            "dopasowania wymaga ręcznej kontroli przed nowym planem treści."
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
        knowledge_card_ids=list(GSC_CONTENT_KNOWLEDGE_CARD_IDS),
        expert_rule_ids=[
            "content_duplication_rules_v1",
            "content_brief_rules_v1",
        ],
        blocked_claims=["nowa treść bez kontroli spisu treści", "gwarancja braku duplikatów"],
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
            "Akcje contentowe pozostają w trybie przygotowania do czasu sprawdzenia "
            "podglądu zmian i audytu."
        ),
        diagnosis=(
            "WILQ może przygotować kolejkę odświeżenia, tworzenia, scalania albo "
            "blokowania oraz podgląd zmian, ale nie może publikować ani zmieniać "
            "WordPress bez sprawdzenia i zgody operatora."
        ),
        next_step="Sprawdź `act_prepare_content_refresh_queue` w WILQ i pokaż podgląd zmian.",
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
        knowledge_card_ids=["card_wordpress_content_refresh_playbook"],
        expert_rule_ids=["content_brief_rules_v1", "content_voice_rules_v1"],
        blocked_claims=[
            "zapis do WordPress bez potwierdzenia",
            "automatyczna publikacja",
            "gwarancja pozycji",
        ],
        risk=ActionRisk.medium,
    )


def _query_page_count(items: list[TacticalQueueItem]) -> int:
    return sum(1 for item in items if item.domain == OpportunityDomain.gsc_seo)


def _matched_inventory_count(items: list[TacticalQueueItem]) -> int:
    return sum(1 for item in items if item.dimensions.get("wordpress_match") == "found")


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
                _content_metric_fact_with_api_label(fact) for fact in decision.metric_facts
            ],
        }
    )


def _content_connector_with_api_label(connector: ConnectorStatus) -> ConnectorStatus:
    return connector.model_copy(
        update={"status_label": _content_connector_status_label(str(connector.status))}
    )


def _content_refresh_with_api_label(refresh: ConnectorRefreshRun) -> ConnectorRefreshRun:
    return refresh.model_copy(
        update={
            "connector_label": source_connector_label(refresh.connector_id),
            "status_label": _content_refresh_status_label(str(refresh.status)),
        }
    )


def _content_live_data_status_label(live_data_available: bool) -> str:
    return (
        "dane GSC i WordPress dostępne"
        if live_data_available
        else "brak danych GSC lub WordPress do decyzji"
    )


def _content_section_with_api_labels(
    section: ContentDiagnosticSection,
) -> ContentDiagnosticSection:
    return section.model_copy(
        update={
            "metric_facts": [
                _content_metric_fact_with_api_label(fact) for fact in section.metric_facts
            ],
            "evidence_summary_label": evidence_count_label(section.evidence_ids),
            "action_summary_label": action_count_label(section.action_ids),
            "blocked_claim_labels": content_blocked_claim_labels(section.blocked_claims),
        }
    )


def _content_metric_fact_with_api_label(fact: MetricFact) -> MetricFact:
    return fact.model_copy(update={"metric_label": _content_metric_fact_label(fact.name)})


def _content_connector_status_label(value: str) -> str:
    return CONTENT_CONNECTOR_STATUS_LABELS.get(value, content_contract_label(value))


def _content_refresh_status_label(value: str) -> str:
    return CONTENT_REFRESH_STATUS_LABELS.get(value, content_contract_label(value))


def _content_metric_fact_label(value: str) -> str:
    return CONTENT_METRIC_FACT_LABELS.get(value, content_contract_label(value))


def _content_decision_queue(
    items: list[TacticalQueueItem],
    metric_facts: list[MetricFact],
    action_ids: list[str],
    latest_refreshes: list[ConnectorRefreshRun],
) -> list[ContentDecisionItem]:
    decisions = [
        *gsc_content_decisions(
            items,
            knowledge_card_ids=GSC_CONTENT_KNOWLEDGE_CARD_IDS,
            expert_rule_ids=GSC_CONTENT_EXPERT_RULE_IDS,
        ),
        *ga4_tracking_gap_decisions(
            items,
            knowledge_card_ids=GA4_TRACKING_KNOWLEDGE_CARD_IDS,
            expert_rule_ids=GA4_TRACKING_EXPERT_RULE_IDS,
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
            for decision in sorted(decisions, key=content_decision_sort_key)[:5]
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
