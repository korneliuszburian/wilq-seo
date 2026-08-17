from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from wilq.actions.google_ads.business_context import ADS_BUSINESS_CONTEXT_ACTION_ID
from wilq.actions.localo.visibility import LOCALO_VISIBILITY_REVIEW_ACTION_ID
from wilq.briefing.blocked_claim_labels import operator_blocked_claims
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.content.operator_copy import unique
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionObject,
    ActionRisk,
    CommandCenterBriefItem,
    ConnectorRefreshRun,
    ConnectorStatus,
    MetricFact,
    OpportunityDomain,
    TacticalQueueItem,
    TacticalQueueResponse,
    connector_refresh_has_live_data,
)

from .labels import (
    _count_phrase,
    _localo_contracts_phrase,
    _metric_tiles_sentence,
)
from .metrics import (
    _ads_campaign_count,
    _ads_currency_tile_from_summary,
    _ads_derived_kpi_metric_tiles,
    _ads_distinct_dimension_count,
    _ads_recommendation_count,
    _ads_review_search_term_count,
    _ads_search_term_count,
    _ahrefs_content_metric_tiles,
    _ahrefs_gap_facts,
    _dimensioned_ga4_facts,
    _first_numeric_fact,
    _ga4_landing_group_count,
    _ga4_measurement_issue_count,
    _ga4_traffic_quality_count,
    _localo_blocked_claims_for_missing_contracts,
    _localo_metric_facts_for_run,
    _localo_metric_tiles,
    _localo_missing_value_contracts,
    _localo_value_facts,
    _merchant_issue_cluster_count,
    _merchant_issue_type_count,
    _merchant_item_product_count,
    _numeric_tile,
    _source_connectors_with_evidence,
    _sum_numeric_facts,
    _sum_tactical_metric,
    _summary_int_tile,
    _summary_number_tile,
)
from .shared import (
    AHREFS_CONNECTOR_ID,
    CONFIGURE_GOOGLE_ADS_ACTION_ID,
    DAILY_ADS_REVIEW_ACTION_IDS,
    GA4_COMMAND_CENTER_DECISION_LIMIT,
    GA4_CONNECTOR_ID,
    GOOGLE_ADS_CONNECTOR_ID,
    GOOGLE_MERCHANT_CONNECTOR_ID,
    _action_ids_for,
    _facts_for_latest_refresh,
    _limited_ids,
    _refresh_has_live_data,
    _resolve_latest_connector_refresh,
    _risk_rank,
    _tactical_items_for_latest_refresh,
)


def tactical_item_count() -> int:
    return len(build_tactical_queue().items)


def _ads_item_from_facts(
    facts: list[MetricFact],
    actions: list[ActionObject],
    *,
    latest_refresh: ConnectorRefreshRun | None = None,
    allow_refresh_lookup: bool = True,
) -> CommandCenterBriefItem:
    latest_refresh = _resolve_latest_connector_refresh(
        GOOGLE_ADS_CONNECTOR_ID,
        latest_refresh,
        allow_refresh_lookup=allow_refresh_lookup,
    )
    latest_summary = latest_refresh.metric_summary if latest_refresh is not None else {}
    live_data_available = _refresh_has_live_data(latest_refresh) and (
        bool(facts) or bool(latest_summary)
    )
    campaign_count = _ads_campaign_count(facts)
    search_term_count = _ads_search_term_count(facts)
    budget_preview_count = _ads_distinct_dimension_count(facts, "budget_id")
    recommendation_count = _ads_recommendation_count(facts)
    review_term_count = _ads_review_search_term_count(facts)
    derived_kpi_tiles = _ads_derived_kpi_metric_tiles(facts)
    ads_action_ids = _action_ids_for(actions, connector=GOOGLE_ADS_CONNECTOR_ID)
    if live_data_available:
        action_ids = [
            action_id for action_id in DAILY_ADS_REVIEW_ACTION_IDS if action_id in ads_action_ids
        ]
    else:
        action_ids = [
            action_id for action_id in ads_action_ids if action_id == CONFIGURE_GOOGLE_ADS_ACTION_ID
        ]
    metric_tiles: dict[str, float | int | str] = {
        "kampanie": _summary_int_tile(latest_summary, ("row_count",), campaign_count),
        "zapytania": _summary_int_tile(
            latest_summary,
            ("search_term_row_count",),
            search_term_count,
        ),
        "kliknięcia": _summary_number_tile(
            latest_summary,
            "clicks",
            _sum_numeric_facts(facts, "clicks"),
        ),
        "wyświetlenia": _summary_number_tile(
            latest_summary,
            "impressions",
            _sum_numeric_facts(facts, "impressions"),
        ),
        "koszt": _ads_currency_tile_from_summary(
            latest_summary,
            facts,
            "cost_micros",
            divide_by_million=True,
        ),
        "konwersje": _summary_number_tile(
            latest_summary,
            "conversions",
            _sum_numeric_facts(facts, "conversions"),
        ),
        "wartość konwersji": _ads_currency_tile_from_summary(
            latest_summary,
            facts,
            "conversion_value",
        ),
        "podgląd budżetu": _summary_int_tile(
            latest_summary,
            ("budgeted_campaign_count", "recommended_budget_count"),
            budget_preview_count,
        ),
        "rekomendacje": _summary_int_tile(
            latest_summary,
            ("recommendation_row_count", "recommendation_campaign_count"),
            recommendation_count,
        ),
        "wykluczenia": review_term_count,
        "segmenty": review_term_count,
    }
    metric_tiles.update(derived_kpi_tiles)
    return CommandCenterBriefItem(
        id="daily_ads_status",
        title=(
            "Google Ads: kolejki budżetu, rekomendacji i zapytań"
            if live_data_available
            else "Google Ads: blokada OAuth przed oceną kosztów"
        ),
        route="/ads-doctor",
        status="ready" if live_data_available else "blocked",
        priority=16 if live_data_available else 5,
        summary=(
            _ads_ready_summary(metric_tiles)
            if live_data_available
            else "Google Ads nie ma aktualnych danych dla Centrum pracy."
        ),
        next_step=(
            _ads_ready_next_step(metric_tiles)
            if live_data_available
            else (
                "Otwórz widok Google Ads i wykonaj bezpieczną ścieżkę naprawy OAuth "
                "przez sprawdzenie w WILQ."
            )
        ),
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_limited_ids(
            unique(
                [
                    *(latest_refresh.evidence_ids if latest_refresh is not None else []),
                    *(fact.evidence_id for fact in facts),
                    connector_evidence_id(GOOGLE_ADS_CONNECTOR_ID),
                ]
            )
        ),
        action_ids=action_ids,
        metric_tiles=metric_tiles if live_data_available else {"blokady": 1},
        blocked_claims=(
            [
                "CPA",
                "zwrot z reklam",
                "marnowanie budżetu na zapytaniach",
                "dodanie wykluczających słów kluczowych",
                "zmiana budżetu",
                "zapis rekomendacji",
                "opłacalność",
                "zmarnowany budżet",
            ]
            if live_data_available
            else [
                "wydatki reklamowe",
                "CPA",
                "zwrot z reklam",
                "zapytania z reklam",
                "zmarnowany budżet",
            ]
        ),
        risk=ActionRisk.medium,
    )


def _ads_business_context_item_from_facts(
    facts: list[MetricFact],
    actions: list[ActionObject],
    *,
    latest_refresh: ConnectorRefreshRun | None = None,
    allow_refresh_lookup: bool = True,
) -> CommandCenterBriefItem | None:
    latest_refresh = _resolve_latest_connector_refresh(
        GOOGLE_ADS_CONNECTOR_ID,
        latest_refresh,
        allow_refresh_lookup=allow_refresh_lookup,
    )
    if not (_refresh_has_live_data(latest_refresh) and facts):
        return None
    action_ids = [
        action_id
        for action_id in _action_ids_for(actions, connector=GOOGLE_ADS_CONNECTOR_ID)
        if action_id == ADS_BUSINESS_CONTEXT_ACTION_ID
    ]
    if not action_ids:
        return None
    return CommandCenterBriefItem(
        id="daily_ads_business_context",
        title="Google Ads: brakuje kontekstu biznesowego do decyzji budżetowych",
        route="/ads-doctor",
        status="blocked",
        priority=18,
        summary=(
            "Ads ma aktualne dowody, ale WILQ nie ma kompletnego kontekstu "
            "biznesowego do decyzji budżetowych: marży, celu, docelowego kosztu "
            "pozyskania celu i docelowego zwrotu z reklam "
            "i potwierdzonej oceny strategii. Bez tego wskaźniki są tylko wstępnym przeglądem, "
            "nie oceną opłacalności."
        ),
        next_step=(
            "Otwórz widok Ads i uzupełnij marżę, cel biznesowy, cel budżetu "
            "oraz docelowy koszt pozyskania celu albo zwrot z reklam. Potem sprawdź "
            "w WILQ zasady bezpieczeństwa celu i ocenę strategii zanim ocenisz "
            "opłacalność albo skalowanie budżetu."
        ),
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=_limited_ids(
            unique(
                [
                    *(latest_refresh.evidence_ids if latest_refresh is not None else []),
                    *(fact.evidence_id for fact in facts),
                    connector_evidence_id(GOOGLE_ADS_CONNECTOR_ID),
                ]
            )
        ),
        action_ids=action_ids,
        metric_tiles={
            "braki": 5,
            "marża": "marża niepodana",
            "cel biznesowy": "cel niepotwierdzony",
        },
        blocked_claims=[
            "opłacalność",
            "zmarnowany budżet",
            "skalowanie budżetu",
            "ocena docelowego kosztu pozyskania celu",
            "ocena docelowego zwrotu z reklam",
        ],
        risk=ActionRisk.medium,
    )


def _merchant_item_from_tactical(
    tactical_items: list[TacticalQueueItem],
    actions: list[ActionObject],
    facts: list[MetricFact],
    *,
    latest_refresh: ConnectorRefreshRun | None = None,
    allow_refresh_lookup: bool = True,
) -> CommandCenterBriefItem:
    latest_refresh = _resolve_latest_connector_refresh(
        GOOGLE_MERCHANT_CONNECTOR_ID,
        latest_refresh,
        allow_refresh_lookup=allow_refresh_lookup,
    )
    facts = _facts_for_latest_refresh(latest_refresh, facts)
    merchant_items = [item for item in tactical_items if item.domain == OpportunityDomain.merchant]
    has_current_issue_facts = any(
        fact.name == "issue_product_count" and fact.dimensions.get("issue_type") for fact in facts
    )
    merchant_items = (
        []
        if has_current_issue_facts
        else _tactical_items_for_latest_refresh(latest_refresh, merchant_items)
    )
    product_count = int(_first_numeric_fact(facts, "total_products"))
    issue_type_count = _merchant_issue_type_count(facts)
    issue_occurrence_count = int(_sum_numeric_facts(facts, "issue_product_count"))
    issue_cluster_count = _merchant_issue_cluster_count(facts)
    decision_count = max(len(merchant_items), min(issue_cluster_count, 8))
    live_data_available = bool(merchant_items or issue_occurrence_count)
    action_ids = unique(
        [
            *(action_id for item in merchant_items for action_id in item.action_ids),
            *_action_ids_for(actions, connector=GOOGLE_MERCHANT_CONNECTOR_ID),
        ]
    )
    top_item = (
        sorted(
            merchant_items,
            key=lambda item: (_risk_rank(item.risk), -_merchant_item_product_count(item), item.id),
        )[0]
        if merchant_items
        else None
    )
    summary = (
        _merchant_command_center_summary(
            product_count=product_count,
            issue_type_count=issue_type_count,
            issue_occurrence_count=issue_occurrence_count,
            decision_count=decision_count,
            top_title=top_item.title if top_item is not None else None,
        )
        if live_data_available
        else "Merchant nie ma gotowej kolejki decyzji z aktualnych danych źródłowych."
    )
    return CommandCenterBriefItem(
        id="daily_merchant_feed",
        title="Merchant: kolejka problemów pliku produktowego",
        route="/merchant",
        status="ready" if live_data_available else "blocked",
        priority=10 if live_data_available and issue_occurrence_count > 0 else 35,
        summary=(
            f"{summary} To jest kolejka do sprawdzenia, nie automatyczna naprawa "
            "pliku produktowego."
            if live_data_available
            else summary
        ),
        next_step=(
            "Otwórz widok Merchant i przejrzyj decyzje pliku produktowego przed "
            "sprawdzeniem propozycji w WILQ."
            if live_data_available
            else "Uruchom odczyt danych Merchant, potem wróć do widoku Merchant."
        ),
        source_connectors=[GOOGLE_MERCHANT_CONNECTOR_ID],
        evidence_ids=_limited_ids(
            unique(
                [
                    *(evidence_id for item in merchant_items for evidence_id in item.evidence_ids),
                    *(fact.evidence_id for fact in facts),
                    connector_evidence_id(GOOGLE_MERCHANT_CONNECTOR_ID),
                ]
            )
        ),
        action_ids=action_ids,
        metric_tiles={
            "produkty": product_count,
            "typy problemów": issue_type_count,
            "zgłoszenia": issue_occurrence_count,
            "decyzje": decision_count,
            "blokady": 0 if live_data_available else 1,
        },
        blocked_claims=operator_blocked_claims(
            unique(claim for item in merchant_items for claim in item.blocked_claims)
            or [
                "ponowne zatwierdzenie produktu",
                "odzyskany przychód",
                "automatyczna zmiana pliku produktowego",
            ]
        ),
        risk=ActionRisk.medium,
    )


def _merchant_command_center_summary(
    *,
    product_count: int,
    issue_type_count: int,
    issue_occurrence_count: int,
    decision_count: int,
    top_title: str | None,
) -> str:
    parts = [
        _count_phrase(product_count, "produkt", "produkty", "produktów"),
        _count_phrase(issue_type_count, "typ problemu", "typy problemów", "typów problemów"),
        _count_phrase(
            issue_occurrence_count,
            "zgłoszenie problemu",
            "zgłoszenia problemów",
            "zgłoszeń problemów",
        ),
        _count_phrase(
            decision_count, "decyzja do przejścia", "decyzje do przejścia", "decyzji do przejścia"
        ),
    ]
    summary = "Merchant Center ma " + ", ".join(parts) + "."
    if top_title:
        summary = f"{summary} Najpierw sprawdź: {top_title}."
    return summary


def _content_item_from_tactical(
    queue: TacticalQueueResponse,
    ahrefs_facts: list[MetricFact],
    actions: list[ActionObject],
    *,
    latest_ahrefs_refresh: ConnectorRefreshRun | None = None,
    allow_refresh_lookup: bool = True,
) -> CommandCenterBriefItem:
    content_groups = [
        group
        for group in queue.compact_groups
        if group.source_connectors and "google_search_console" in group.source_connectors
    ]
    content_items = [item for item in queue.items if item.domain == OpportunityDomain.gsc_seo]
    latest_ahrefs_refresh = _resolve_latest_connector_refresh(
        AHREFS_CONNECTOR_ID,
        latest_ahrefs_refresh,
        allow_refresh_lookup=allow_refresh_lookup,
    )
    ahrefs_facts = _facts_for_latest_refresh(latest_ahrefs_refresh, ahrefs_facts)
    ahrefs_gap_facts = _ahrefs_gap_facts(ahrefs_facts)
    ahrefs_metric_tiles = _ahrefs_content_metric_tiles(ahrefs_gap_facts)
    ahrefs_available = bool(ahrefs_gap_facts)
    live_data_available = bool(content_items)
    content_decision_count = len(content_groups) or len(content_items)
    decision_count = content_decision_count + (1 if ahrefs_available else 0)
    top_group = content_groups[0] if content_groups else None
    top_item = content_items[0] if content_items else None
    total_clicks = _sum_tactical_metric(content_items, "clicks")
    total_impressions = _sum_tactical_metric(content_items, "impressions")
    tactical_summary = (
        _content_tactical_summary(top_item, top_group.diagnosis)
        if top_group is not None
        else (
            _content_tactical_summary(top_item, "")
            if top_item is not None
            else (
                "Brak gotowej kolejki contentowej. WILQ potrzebuje zapytań i adresów z GSC "
                "i spisu treści WordPress."
            )
        )
    )
    summary = _content_summary_with_ahrefs(tactical_summary, ahrefs_metric_tiles)
    next_step = (
        top_group.next_step
        if top_group is not None
        else "Otwórz widok Treści i odśwież GSC oraz spis treści WordPress."
    )
    base_source_connectors = [
        *([AHREFS_CONNECTOR_ID] if ahrefs_available else []),
        "google_search_console",
        "wordpress_ekologus",
        "wordpress_sklep",
    ]
    evidence_ids = _limited_ids(
        unique(
            [
                *(fact.evidence_id for fact in ahrefs_gap_facts),
                *(evidence_id for item in content_items for evidence_id in item.evidence_ids),
            ]
        )
        or [connector_evidence_id("google_search_console")]
    )
    source_connectors = _source_connectors_with_evidence(
        base_source_connectors,
        evidence_ids,
    )
    action_ids = unique(
        [
            *(
                action_id
                for action_id in _action_ids_for(
                    actions,
                    connector="wordpress_ekologus",
                    domain=OpportunityDomain.content,
                )
                if action_id
                in {
                    "act_prepare_content_refresh_queue",
                    "act_prepare_wordpress_draft_handoff",
                }
            ),
            *(action_id for item in content_items for action_id in item.action_ids),
        ]
    )
    return CommandCenterBriefItem(
        id="daily_content_queue",
        title=(
            "Treści: kolejka SEO z GSC i WordPress"
            if live_data_available
            else "Treści: brak kolejki SEO"
        ),
        route="/content-workflow",
        status="ready" if live_data_available else "blocked",
        priority=12 if live_data_available else 40,
        summary=summary,
        next_step=next_step,
        source_connectors=source_connectors,
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        metric_tiles={
            "zapytania i adresy z GSC": len(content_items),
            "dopasowania WordPress": sum(
                1 for item in content_items if item.dimensions.get("wordpress_match") == "found"
            ),
            "decyzje": decision_count,
            "wyświetlenia": total_impressions,
            "kliknięcia": total_clicks,
            **ahrefs_metric_tiles,
            "blokady": 0 if live_data_available else 1,
        },
        blocked_claims=unique(claim for item in content_items for claim in item.blocked_claims)
        or ["wzrost liczby leadów", "wpływ na przychód", "gwarancja pozycji"],
        risk=ActionRisk.low if live_data_available else ActionRisk.medium,
    )


def _content_summary_with_ahrefs(
    tactical_summary: str,
    ahrefs_metric_tiles: dict[str, int],
) -> str:
    if not ahrefs_metric_tiles:
        return tactical_summary
    record_count = _count_phrase(
        ahrefs_metric_tiles.get("rekordy Ahrefs", 0),
        "rekord do sprawdzenia",
        "rekordy do sprawdzenia",
        "rekordów do sprawdzenia",
    )
    content_gap_count = _count_phrase(
        ahrefs_metric_tiles.get("luki Ahrefs", 0),
        "luka treści",
        "luki treści",
        "luk treści",
    )
    backlink_gap_count = _count_phrase(
        ahrefs_metric_tiles.get("luki linków", 0),
        "luka linków",
        "luki linków",
        "luk linków",
    )
    ahrefs_summary = (
        "Ahrefs ma kolejkę sprawdzenia luk SEO: "
        f"{record_count}, "
        f"{content_gap_count} i "
        f"{backlink_gap_count}. "
        "To jest materiał do połączenia z GSC i WordPress, nie obietnica wzrostu."
    )
    return f"{ahrefs_summary} {tactical_summary}".strip()


def _content_tactical_summary(
    item: TacticalQueueItem | None,
    fallback_summary: str,
) -> str:
    if item is None:
        return fallback_summary
    if item.dimensions.get("wordpress_match") == "found":
        return (
            f"{fallback_summary} WordPress potwierdza istniejącą stronę; "
            "bezpieczny kierunek to odświeżenie albo scalenie, nie tworzenie duplikatu."
        ).strip()
    if item.diagnosis:
        return item.diagnosis
    return fallback_summary


def _ads_ready_summary(metric_tiles: dict[str, float | int | str]) -> str:
    metric_sentence = _metric_tiles_sentence(metric_tiles)
    return (
        "Google Ads ma aktualny odczyt do oceny: "
        f"{metric_sentence}. "
        "To są kolejki oceny z dowodami i akcjami do sprawdzenia. Wskaźniki są "
        "sygnałem z bieżących danych źródłowych; to nadal nie jest ocena "
        "opłacalności, kosztu pozyskania celu, zwrotu z reklam ani ścieżka zapisu zmian."
    )


def _ads_ready_next_step(metric_tiles: dict[str, float | int | str]) -> str:
    review_parts: list[str] = []
    if _numeric_tile(metric_tiles, "podgląd budżetu") > 0:
        review_parts.append("budżety")
    if _numeric_tile(metric_tiles, "rekomendacje") > 0:
        review_parts.append("rekomendacje")
    if _numeric_tile(metric_tiles, "wskaźniki do sprawdzenia") > 0:
        review_parts.append("wskaźniki kampanii")
    if _numeric_tile(metric_tiles, "wykluczenia") > 0:
        review_parts.append("wykluczenia")
    if _numeric_tile(metric_tiles, "segmenty") > 0:
        review_parts.append("segmenty")
    if not review_parts:
        review_parts.append("kampanie i zapytania")
    return (
        "Otwórz widok Ads i przejdź przez ocenę: "
        f"{', '.join(review_parts)}. Zapis zmian wymaga sprawdzenia w WILQ, "
        "potwierdzenia i audytu."
    )


def _ga4_item_from_tactical(
    tactical_items: list[TacticalQueueItem],
    actions: list[ActionObject],
    ga4_facts: list[MetricFact],
) -> CommandCenterBriefItem:
    ga4_items = [item for item in tactical_items if item.domain == OpportunityDomain.ga4]
    dimensioned_facts = _dimensioned_ga4_facts(ga4_facts)
    landing_group_count = max(len(ga4_items), _ga4_landing_group_count(dimensioned_facts))
    measurement_issue_count = max(
        sum(1 for item in ga4_items if item.intent == "tracking_gap"),
        _ga4_measurement_issue_count(dimensioned_facts),
    )
    decision_count = min(
        max(len(ga4_items), landing_group_count),
        GA4_COMMAND_CENTER_DECISION_LIMIT,
    )
    traffic_quality_count = max(
        sum(1 for item in ga4_items if item.intent == "landing_page_quality"),
        _ga4_traffic_quality_count(dimensioned_facts),
    )
    measurement_issue_count = min(measurement_issue_count, decision_count)
    traffic_quality_count = min(
        traffic_quality_count,
        max(decision_count - measurement_issue_count, 0),
    )
    matched_items = [
        item for item in ga4_items if item.dimensions.get("wordpress_match") == "found"
    ]
    action_ids = _action_ids_for(
        actions,
        connector=GA4_CONNECTOR_ID,
    )
    live_data_available = landing_group_count > 0
    summary_parts = [
        _count_phrase(
            landing_group_count,
            "grupę stron wejścia, źródeł ruchu i kampanii",
            "grupy stron wejścia, źródeł ruchu i kampanii",
            "grup stron wejścia, źródeł ruchu i kampanii",
        ),
        _count_phrase(
            measurement_issue_count,
            "problem pomiaru",
            "problemy pomiaru",
            "problemów pomiaru",
        ),
        _count_phrase(
            traffic_quality_count,
            "decyzję jakości ruchu",
            "decyzje jakości ruchu",
            "decyzji jakości ruchu",
        ),
        _count_phrase(
            len(matched_items),
            "dopasowanie WordPress",
            "dopasowania WordPress",
            "dopasowań WordPress",
        ),
    ]
    return CommandCenterBriefItem(
        id="daily_ga4_landing_quality",
        title=(
            "GA4: pomiar i jakość ruchu do kontroli"
            if live_data_available
            else "GA4: ocena ruchu niepotwierdzona"
        ),
        route="/ga4",
        status="blocked",
        priority=14 if live_data_available else 42,
        summary=(
            f"GA4 ma {summary_parts[0]}, {summary_parts[1]}, {summary_parts[2]} i "
            f"{summary_parts[3]}. "
            "Blokada oznacza, że nie ma potwierdzonych podstaw do wniosków o zwrocie "
            "z reklam, przychodzie, spadku konwersji i naprawionym pomiarze; "
            "to nie jest awaria źródła danych."
        ),
        next_step=(
            "Otwórz widok GA4, sprawdź kolejkę jakości ruchu i przejdź przez "
            "propozycję przeglądu GA4 w WILQ."
        ),
        source_connectors=[GA4_CONNECTOR_ID],
        evidence_ids=_limited_ids(
            unique(evidence_id for item in ga4_items for evidence_id in item.evidence_ids)
            or unique(fact.evidence_id for fact in dimensioned_facts)
            or [connector_evidence_id(GA4_CONNECTOR_ID)]
        ),
        action_ids=action_ids,
        metric_tiles={
            "grupy ruchu": landing_group_count,
            "decyzje": decision_count,
            "pomiar": measurement_issue_count,
            "jakość ruchu": traffic_quality_count,
            "brakujące dane": 1,
        },
        blocked_claims=["zwrot z reklam", "przychód", "spadek konwersji", "naprawiony pomiar"],
        risk=ActionRisk.medium,
    )


def _localo_item(
    connector: ConnectorStatus,
    runs: list[ConnectorRefreshRun],
    metric_facts: list[MetricFact],
) -> CommandCenterBriefItem:
    successful_mcp_run = _latest_successful_localo_mcp_run(runs)
    latest_run = runs[0] if runs else None
    oauth_access_ready = successful_mcp_run is not None
    metric_facts = _localo_metric_facts_for_run(successful_mcp_run, metric_facts)
    value_facts = _localo_value_facts(metric_facts)
    has_value_facts = bool(value_facts)
    missing_value_contracts = _localo_missing_value_contracts(value_facts)
    missing_value_contracts_phrase = _localo_contracts_phrase(missing_value_contracts)
    missing = (
        ", ".join(connector.missing_credentials)
        if connector.missing_credentials
        else "brak świeżego odczytu danych Localo"
    )
    evidence_ids = [connector_evidence_id("localo")]
    if successful_mcp_run is not None:
        evidence_ids = successful_mcp_run.evidence_ids
    elif latest_run is not None:
        evidence_ids = latest_run.evidence_ids
    if has_value_facts:
        item_id = "daily_localo_visibility_facts"
        title = "Localo: agregaty widoczności i recenzji są gotowe"
        if missing_value_contracts:
            summary = (
                "Localo dostarczył część agregatów miejsc, monitorowanych fraz, "
                "profilu firmy w Google, konkurencji albo recenzji. WILQ nadal blokuje "
                f"{missing_value_contracts_phrase}, zapis zmian i obietnicę wzrostu "
                "widoczności bez osobnych danych albo dowodu efektu."
            )
            next_step = (
                "Otwórz widok Localo i przejrzyj agregaty fraz, pozycje w siatce "
                "lokalnej oraz recenzje. "
                f"Nie twierdź nic o {missing_value_contracts_phrase}, zapisie zmian ani "
                "wzroście widoczności bez dodatkowych dowodów."
            )
        else:
            summary = (
                "Localo dostarczył agregaty miejsc, monitorowanych fraz, profilu firmy "
                "w Google, konkurencji i recenzji. WILQ nadal blokuje zapis zmian oraz "
                "obietnicę wzrostu widoczności bez osobnego dowodu efektu."
            )
            next_step = (
                "Otwórz widok Localo i przejrzyj agregaty fraz, pozycje w siatce "
                "lokalnej, profil firmy w Google, konkurencję oraz recenzje. Zapis zmian "
                "i obietnicę wzrostu widoczności zostaw zablokowane do osobnego dowodu."
            )
        priority = 18
        blocked_claims = _localo_blocked_claims_for_missing_contracts(missing_value_contracts)
    elif oauth_access_ready:
        item_id = "daily_localo_readiness"
        title = "Localo: dostęp działa, brakuje rankingów i danych profilu firmy w Google"
        summary = (
            "Localo potwierdził dostęp do odczytu danych, ale WILQ nie ma jeszcze "
            "konkretnych rankingów, danych profilu firmy w Google ani konkurencji."
        )
        next_step = (
            "Otwórz widok Localo tylko jako status źródła; lokalne rekomendacje wymagają "
            "odczytu danych rankingów, profilu firmy w Google, konkurencji i recenzji."
        )
        priority = 60
        blocked_claims = [
            "lokalne rankingi",
            "wyniki profilu firmy w Google",
            "poprawa widoczności lokalnej",
        ]
    else:
        item_id = "daily_localo_readiness"
        title = "Localo: brak dostępu przed lokalnymi rekomendacjami"
        summary = f"Localo nie ma pełnego dostępu: {missing}."
        next_step = "Otwórz widok Localo i dokończ dostęp OAuth do danych Localo."
        priority = 20
        blocked_claims = [
            "lokalne rankingi",
            "wyniki profilu firmy w Google",
            "poprawa widoczności lokalnej",
        ]
    return CommandCenterBriefItem(
        id=item_id,
        title=title,
        route="/localo",
        status="ready" if oauth_access_ready or has_value_facts else "blocked",
        priority=priority,
        summary=summary,
        next_step=next_step,
        source_connectors=["localo"],
        evidence_ids=_limited_ids(evidence_ids),
        action_ids=[LOCALO_VISIBILITY_REVIEW_ACTION_ID] if has_value_facts else [],
        metric_tiles=_localo_metric_tiles(value_facts, oauth_access_ready),
        blocked_claims=blocked_claims,
        risk=ActionRisk.low if oauth_access_ready or has_value_facts else ActionRisk.medium,
    )


def _latest_successful_localo_mcp_run(
    runs: list[ConnectorRefreshRun],
) -> ConnectorRefreshRun | None:
    for run in runs:
        if (
            connector_refresh_has_live_data(run)
            and run.metric_summary.get("api") == "localo_mcp_oauth_probe"
            and run.metric_summary.get("mcp_initialize_status") == 200
        ):
            return run
    return None


def _first_blocked_section(sections: Iterable[Any]) -> Any | None:
    for section in sections:
        if getattr(section, "status", None) == "blocked":
            return section
    return None
