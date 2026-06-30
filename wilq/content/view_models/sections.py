from __future__ import annotations

from collections.abc import Iterable

from wilq.content.preflight.vendor_read import (
    content_blocker_reason,
    refresh_or_connector_evidence_ids,
)
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionRisk,
    ConnectorRefreshRun,
    ContentDiagnosticSection,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
)


def query_page_section(
    latest_refreshes: list[ConnectorRefreshRun],
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
    *,
    knowledge_card_ids: tuple[str, ...],
    expert_rule_ids: tuple[str, ...],
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
        knowledge_card_ids=list(knowledge_card_ids),
        expert_rule_ids=list(expert_rule_ids),
        blocked_claims=["wzrost liczby leadów", "wzrost konwersji", "wpływ na przychód"],
        risk=ActionRisk.low,
    )


def inventory_match_section(
    latest_refreshes: list[ConnectorRefreshRun],
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
    *,
    knowledge_card_ids: tuple[str, ...],
    expert_rule_ids: tuple[str, ...],
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
        knowledge_card_ids=list(knowledge_card_ids),
        expert_rule_ids=list(expert_rule_ids),
        blocked_claims=["nowa treść bez kontroli spisu treści", "gwarancja braku duplikatów"],
        risk=ActionRisk.low,
    )


def content_action_safety_section(
    latest_refreshes: list[ConnectorRefreshRun],
    facts: list[MetricFact],
    tactical_items: list[TacticalQueueItem],
    action_ids: list[str],
    *,
    content_connector_ids: tuple[str, ...],
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
        source_connectors=list(content_connector_ids),
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


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values
