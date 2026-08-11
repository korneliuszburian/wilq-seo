from __future__ import annotations

from typing import Any, Literal

from wilq.actions.google_ads.business_context import ADS_BUSINESS_CONTEXT_ACTION_ID
from wilq.actions.google_ads.campaign_review import CAMPAIGN_REVIEW_ACTION_ID
from wilq.actions.google_ads.custom_segments import CUSTOM_SEGMENT_ACTION_ID
from wilq.actions.google_ads.negative_keywords import NEGATIVE_KEYWORD_ACTION_ID
from wilq.actions.google_ads.recommendations import RECOMMENDATION_REVIEW_ACTION_ID
from wilq.actions.localo.visibility import LOCALO_VISIBILITY_REVIEW_ACTION_ID
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    CommandCenterActionPlanItem,
    CommandCenterBriefItem,
    OpportunityDomain,
)

from .labels import (
    _count_phrase,
    _localo_claims_phrase,
)
from .metrics import (
    _source_connectors_with_evidence,
)
from .shared import (
    CONFIGURE_GOOGLE_ADS_ACTION_ID,
    GA4_CONNECTOR_ID,
    GOOGLE_ADS_CONNECTOR_ID,
    GOOGLE_MERCHANT_CONNECTOR_ID,
)


def _command_center_action_stubs() -> list[ActionObject]:
    return [
        _command_center_action_stub(
            CONFIGURE_GOOGLE_ADS_ACTION_ID,
            connector=GOOGLE_ADS_CONNECTOR_ID,
            domain=OpportunityDomain.google_ads,
        ),
        _command_center_action_stub(
            CAMPAIGN_REVIEW_ACTION_ID,
            connector=GOOGLE_ADS_CONNECTOR_ID,
            domain=OpportunityDomain.google_ads,
        ),
        _command_center_action_stub(
            RECOMMENDATION_REVIEW_ACTION_ID,
            connector=GOOGLE_ADS_CONNECTOR_ID,
            domain=OpportunityDomain.google_ads,
        ),
        _command_center_action_stub(
            CUSTOM_SEGMENT_ACTION_ID,
            connector=GOOGLE_ADS_CONNECTOR_ID,
            domain=OpportunityDomain.google_ads,
        ),
        _command_center_action_stub(
            NEGATIVE_KEYWORD_ACTION_ID,
            connector=GOOGLE_ADS_CONNECTOR_ID,
            domain=OpportunityDomain.google_ads,
        ),
        _command_center_action_stub(
            ADS_BUSINESS_CONTEXT_ACTION_ID,
            connector=GOOGLE_ADS_CONNECTOR_ID,
            domain=OpportunityDomain.google_ads,
        ),
        _command_center_action_stub(
            "act_review_merchant_feed_issues",
            connector=GOOGLE_MERCHANT_CONNECTOR_ID,
            domain=OpportunityDomain.merchant,
        ),
        _command_center_action_stub(
            "act_review_ga4_tracking_quality",
            connector=GA4_CONNECTOR_ID,
            domain=OpportunityDomain.ga4,
        ),
        _command_center_action_stub(
            "act_prepare_content_refresh_queue",
            connector="wordpress_ekologus",
            domain=OpportunityDomain.content,
        ),
        _command_center_action_stub(
            "act_prepare_wordpress_draft_handoff",
            connector="wordpress_ekologus",
            domain=OpportunityDomain.content,
        ),
        _command_center_action_stub(
            LOCALO_VISIBILITY_REVIEW_ACTION_ID,
            connector="localo",
            domain=OpportunityDomain.localo,
        ),
    ]


def _command_center_action_stub(
    action_id: str,
    *,
    connector: str,
    domain: OpportunityDomain,
) -> ActionObject:
    return ActionObject(
        id=action_id,
        title=action_id,
        domain=domain,
        connector=connector,
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=[connector_evidence_id(connector)],
        human_diagnosis="Skrócona referencja akcji dla Centrum pracy.",
        recommended_reason="Użyj dedykowanego widoku dla pełnego zakresu akcji.",
        payload={},
        validation_status="not_validated",
        created_by="command_center_stub",
    )


def build_command_center_action_plan(
    items: list[CommandCenterBriefItem],
    tactical_items: list[Any] | None = None,
) -> list[CommandCenterActionPlanItem]:
    items_by_id = {item.id: item for item in items}
    if tactical_items is None:
        tactical_items = build_tactical_queue().items
    plan: list[CommandCenterActionPlanItem] = []
    for item_id in (
        "daily_merchant_feed",
        "daily_content_queue",
        "daily_ga4_landing_quality",
        "daily_ads_status",
        "daily_ads_business_context",
        "daily_localo_visibility_facts",
        "daily_localo_readiness",
    ):
        item = items_by_id.get(item_id)
        if item is None:
            continue
        if item.id == "daily_localo_readiness" and item.status == "ready":
            continue
        plan.append(_action_plan_item(item, tactical_items))
    return plan


def _action_plan_item(
    item: CommandCenterBriefItem,
    tactical_items: list[Any],
) -> CommandCenterActionPlanItem:
    related_tactics = _related_tactical_items(item, tactical_items)
    if item.id == "daily_merchant_feed":
        return _merchant_feed_action_plan_item(item)
    if item.id == "daily_content_queue":
        return _content_queue_action_plan_item(item, related_tactics)
    if item.id == "daily_ga4_landing_quality":
        return _ga4_landing_quality_action_plan_item(item)
    if item.id == "daily_ads_business_context":
        return _ads_business_context_action_plan_item(item)
    if item.id == "daily_ads_status":
        return _ads_status_action_plan_item(item)
    if item.id == "daily_localo_visibility_facts":
        return _localo_visibility_facts_action_plan_item(item)
    if item.id == "daily_localo_readiness":
        return _localo_readiness_action_plan_item(item)
    return _default_action_plan_item(item)


def _merchant_feed_action_plan_item(
    item: CommandCenterBriefItem,
) -> CommandCenterActionPlanItem:
    issue_count = item.metric_tiles.get("zgłoszenia", item.metric_tiles.get("issues", 0))
    product_count_label = _count_phrase(
        item.metric_tiles.get("produkty", 0),
        "produkt",
        "produkty",
        "produktów",
    )
    issue_count_label = _count_phrase(
        issue_count,
        "zgłoszenie problemu",
        "zgłoszenia problemów",
        "zgłoszeń problemów",
    )
    return CommandCenterActionPlanItem(
        id="plan_review_merchant_feed_issues",
        title="Przejrzyj kolejkę problemów Merchant Center",
        route=item.route,
        status=_action_plan_status(item),
        priority=10,
        category="Merchant Center",
        why_it_matters=(
            f"WILQ widzi {product_count_label} i "
            f"{issue_count_label} pliku produktowego. To może blokować "
            "widoczność produktów, ale wymaga sprawdzenia przez człowieka przed zmianami."
        ),
        operator_action=(
            "Otwórz widok Merchant, sprawdź kolejkę problemów i sprawdź propozycję w WILQ."
        ),
        skill_id="wilq-merchant-feed-operator",
        codex_prompt=(
            "Użyj skilla wilq-merchant-feed-operator. Przejrzyj Merchant Center "
            "dla Ekologus, pogrupuj problemy pliku produktowego, wskaż najbezpieczniejszą "
            "kolejkę oceny i nie twierdź, że produkty zostały ponownie zatwierdzone "
            "albo że przychód został odzyskany."
        ),
        codex_context_endpoint="/api/codex/context-pack",
        expected_codex_output=(
            "Polskie podsumowanie przeglądu problemów pliku produktowego "
            "z dowodami źródłowymi, akcją "
            "i listą twierdzeń, których nie wolno używać."
        ),
        source_connectors=item.source_connectors,
        evidence_ids=item.evidence_ids,
        action_ids=item.action_ids,
        blocked_claims=item.blocked_claims,
        risk=item.risk,
    )


def _content_queue_action_plan_item(
    item: CommandCenterBriefItem,
    related_tactics: list[Any],
) -> CommandCenterActionPlanItem:
    evidence_ids = _merge_ids(item.evidence_ids, related_tactics)
    return CommandCenterActionPlanItem(
        id="plan_prepare_content_refresh_queue",
        title="Przejrzyj kolejkę SEO z GSC i WordPress",
        route=item.route,
        status=_action_plan_status(item),
        priority=12,
        category="Content + SEO",
        why_it_matters=(f"{item.summary} Pełne szczegóły zapytań i URL-i są w widoku Treści."),
        operator_action=item.next_step,
        skill_id="wilq-content-strategist",
        codex_prompt=(
            "Użyj skilla wilq-content-strategist. Zbuduj kolejkę zachowania, "
            "odświeżenia, scalenia, nowej treści albo blokady dla Ekologus "
            "na podstawie GSC, spisu treści WordPress, GA4 i dowodów Ahrefs. "
            "Nie obiecuj leadów, przychód ani wzrostów pozycji."
        ),
        codex_context_endpoint="/api/codex/context-pack",
        expected_codex_output=(
            "Polska kolejka decyzji treści z dowodami źródłowymi, źródłami danych "
            "i następnym krokiem."
        ),
        source_connectors=_source_connectors_with_evidence(
            item.source_connectors,
            evidence_ids,
        ),
        evidence_ids=evidence_ids,
        action_ids=item.action_ids,
        blocked_claims=item.blocked_claims,
        risk=item.risk,
    )


def _ga4_landing_quality_action_plan_item(
    item: CommandCenterBriefItem,
) -> CommandCenterActionPlanItem:
    landing_groups = item.metric_tiles.get("grupy ruchu", 0)
    decision_count = item.metric_tiles.get("decyzje", 0)
    measurement_count = item.metric_tiles.get("pomiar", 0)
    traffic_review_count = item.metric_tiles.get("jakość ruchu", 0)
    landing_groups_label = _count_phrase(
        landing_groups,
        "grupę stron wejścia, źródeł ruchu i kampanii",
        "grupy stron wejścia, źródeł ruchu i kampanii",
        "grup stron wejścia, źródeł ruchu i kampanii",
    )
    decision_count_label = _count_phrase(
        decision_count,
        "decyzję GA4 do sprawdzenia",
        "decyzje GA4 do sprawdzenia",
        "decyzji GA4 do sprawdzenia",
    )
    measurement_count_label = _count_phrase(
        measurement_count,
        "problem pomiaru",
        "problemy pomiaru",
        "problemów pomiaru",
    )
    traffic_review_count_label = _count_phrase(
        traffic_review_count,
        "decyzję jakości ruchu",
        "decyzje jakości ruchu",
        "decyzji jakości ruchu",
    )
    return CommandCenterActionPlanItem(
        id="plan_review_ga4_landing_quality",
        title=item.title,
        route=item.route,
        status=_action_plan_status(item),
        priority=14,
        category="GA4",
        why_it_matters=(
            f"WILQ ma {landing_groups_label} i {decision_count_label}: "
            f"{measurement_count_label} oraz {traffic_review_count_label}. "
            "To jest kolejka analityczna, "
            "nie ocena skuteczności. Wnioski o zwrocie z reklam, przychodzie, "
            "spadku konwersji i naprawionym pomiarze pozostają zablokowane bez osobnych danych."
        ),
        operator_action=(
            "Otwórz widok GA4, przejdź przez kolejkę decyzji pomiaru i jakości "
            "ruchu, a potem przejdź przez propozycję przeglądu GA4 w WILQ. "
            "Zapis zmian wymaga sprawdzenia w WILQ. Nie oceniaj opłacalności."
        ),
        skill_id="wilq-ga4-analyst",
        codex_prompt=(
            "Użyj skilla wilq-ga4-analyst. Sprawdź jakość ruchu Ekologus po "
            "stronie wejścia, źródle ruchu i kampanii z kolejki decyzji GA4, "
            "rozdziel problem marketingowy od problemu pomiaru i nie wyciągaj "
            "wniosków o zwrocie z reklam, przychodzie ani konwersjach bez dowodów."
        ),
        codex_context_endpoint="/api/codex/context-pack",
        expected_codex_output=(
            "Polska diagnoza GA4 z faktami strony wejścia, źródła ruchu i kampanii, "
            "blokadami pomiaru i akcją."
        ),
        source_connectors=item.source_connectors,
        evidence_ids=item.evidence_ids,
        action_ids=item.action_ids,
        blocked_claims=item.blocked_claims,
        risk=item.risk,
    )


def _ads_business_context_action_plan_item(
    item: CommandCenterBriefItem,
) -> CommandCenterActionPlanItem:
    return CommandCenterActionPlanItem(
        id="plan_ads_business_context_before_budget_decisions",
        title="Uzupełnij kontekst biznesowy Ads przed decyzjami budżetowymi",
        route=item.route,
        status="blocked",
        priority=18,
        category="Google Ads",
        why_it_matters=(
            "Ads ma aktualne metryki i kolejki do sprawdzenia, "
            "ale bez marży, celu biznesowego, "
            "celu budżetu oraz docelowego zwrotu z reklam albo kosztu pozyskania "
            "celu WILQ nie może uczciwie mówić o rentowności, zmarnowanym budżecie "
            "ani skalowaniu."
        ),
        operator_action=(
            "Otwórz widok Ads i uzupełnij WILQ_ADS_PROFIT_MARGIN, "
            "WILQ_ADS_BUSINESS_GOAL, WILQ_ADS_BUDGET_GOAL oraz WILQ_ADS_TARGET_ROAS "
            "albo WILQ_ADS_TARGET_CPA_MICROS. Potem sprawdź w WILQ zasady "
            "bezpieczeństwa celu i ocenę strategii zanim ocenisz opłacalność albo "
            "skalowanie budżetu."
        ),
        skill_id="wilq-ads-doctor",
        codex_prompt=(
            "Użyj skilla wilq-ads-doctor. Wyjaśnij blokadę kontekstu biznesowego "
            "Ads dla Ekologus, wskaż brakujące pola .env i nie twierdź "
            "rentowności, zmarnowanego budżetu ani skalowania budżetu bez tych danych."
        ),
        codex_context_endpoint="/api/codex/context-pack",
        expected_codex_output=(
            "Polskie podsumowanie blokady Ads z brakującymi polami kontekstu biznesowego, "
            "dowodami źródłowymi i listą twierdzeń, których nie wolno dopowiadać."
        ),
        source_connectors=item.source_connectors,
        evidence_ids=item.evidence_ids,
        action_ids=item.action_ids,
        blocked_claims=item.blocked_claims,
        risk=item.risk,
    )


def _ads_status_action_plan_item(
    item: CommandCenterBriefItem,
) -> CommandCenterActionPlanItem:
    if item.status == "ready":
        return CommandCenterActionPlanItem(
            id="plan_review_ads_campaign_metrics",
            title="Przejrzyj aktualny odczyt Ads bez zapisu zmian",
            route=item.route,
            status="ready",
            priority=16,
            category="Google Ads",
            why_it_matters=(
                f"{item.summary} To jest aktualny odczyt Ads i zestaw decyzji do "
                "sprawdzenia, a nie lista źródeł danych ani ścieżka zapisu zmian: budżet, "
                "rekomendacje, wykluczenia i segmenty mają dowody oraz "
                "akcje do sprawdzenia, ale zapis pozostaje zablokowany."
            ),
            operator_action=(
                "Otwórz widok Ads: aktualny odczyt wartości Ads jest na górze, "
                "a potem przejrzyj: podgląd budżetów, podgląd rekomendacji, "
                "wskaźniki kampanii, przegląd wykluczeń i podgląd segmentów. "
                "Sprawdź propozycje w WILQ, ale nie traktuj wskaźników jako oceny "
                "opłacalności i nie zapisuj zmian."
            ),
            skill_id="wilq-ads-doctor",
            codex_prompt=(
                "Użyj skilla wilq-ads-doctor. Przejrzyj aktualny odczyt Google "
                "Ads dla Ekologus oraz kolejkę oceny: budżety, rekomendacje, "
                "wskaźniki kampanii, zapytania wyszukiwane, wykluczenia i segmenty "
                "niestandardowe. "
                "Cytuj dowody źródłowe i akcje do sprawdzenia. Nie twierdź "
                "opłacalności, zmarnowanego budżetu "
                "ani zapisu zmian; wskaż bezpieczne decyzje do sprawdzenia "
                "i brakujące kontrakty."
            ),
            codex_context_endpoint="/api/codex/context-pack",
            expected_codex_output=(
                "Polska kolejka oceny Ads z dowodami źródłowymi, akcjami do sprawdzenia, "
                "zablokowanymi obietnicami i następnymi krokami bez zapisu zmian."
            ),
            source_connectors=item.source_connectors,
            evidence_ids=item.evidence_ids,
            action_ids=item.action_ids,
            blocked_claims=item.blocked_claims,
            risk=ActionRisk.medium,
        )
    return CommandCenterActionPlanItem(
        id="plan_fix_ads_oauth_before_spend_analysis",
        title="Napraw Google Ads OAuth zanim padną wnioski o kosztach",
        route=item.route,
        status="blocked",
        priority=5,
        category="Google Ads",
        why_it_matters=(
            "Google Ads ma blokadę OAuth. WILQ nie pokaże kosztu, "
            "kosztu pozyskania celu, zwrotu z reklam ani "
            "wyszukiwanych haseł bez świeżych dowodów Ads."
        ),
        operator_action=(
            "Otwórz widok Google Ads i przejdź ścieżkę naprawy przez sprawdzenie w WILQ."
        ),
        skill_id="wilq-ads-doctor",
        codex_prompt=(
            "Użyj skilla wilq-ads-doctor. Zweryfikuj blokadę Ads dla Ekologus "
            "i przygotuj ścieżkę naprawy bez diagnozowania kosztu, "
            "kosztu pozyskania celu, zwrotu z reklam ani wyszukiwanych haseł."
        ),
        codex_context_endpoint="/api/codex/context-pack",
        expected_codex_output=(
            "Polskie podsumowanie blokady z dowodami źródłowymi i bez zmyślonych metryk Ads."
        ),
        source_connectors=item.source_connectors,
        evidence_ids=item.evidence_ids,
        action_ids=item.action_ids,
        blocked_claims=item.blocked_claims,
        risk=ActionRisk.medium,
    )


def _localo_visibility_facts_action_plan_item(
    item: CommandCenterBriefItem,
) -> CommandCenterActionPlanItem:
    blocked_claims_phrase = _localo_claims_phrase(item.blocked_claims)
    return CommandCenterActionPlanItem(
        id="plan_review_localo_visibility_facts",
        title="Przejrzyj agregaty widoczności lokalnej z Localo",
        route=item.route,
        status="ready",
        priority=20,
        category="Localo",
        why_it_matters=(
            "Localo ma agregaty miejsc, fraz, profilu firmy w Google, konkurencji i "
            "recenzji. To pozwala zrobić przegląd lokalnej widoczności, ale "
            f"WILQ nadal blokuje obietnice: {blocked_claims_phrase} bez osobnych "
            "danych albo dowodu efektu."
        ),
        operator_action=(
            "Otwórz widok Localo i przejrzyj tylko agregaty widoczne w evidence. "
            f"Nie używaj zablokowanych obietnic: {blocked_claims_phrase}."
        ),
        skill_id="wilq-localo-operator",
        codex_prompt=(
            "Użyj skilla wilq-localo-operator. Przejrzyj agregaty Localo dla "
            "Ekologus na podstawie dowodów w WILQ i wskaż bezpieczne następne "
            f"kroki. Nie używaj zablokowanych obietnic: {blocked_claims_phrase}. "
            "Nie zdejmuj tych blokad bez osobnych "
            "danych albo dowodu efektu."
        ),
        codex_context_endpoint="/api/codex/context-pack",
        expected_codex_output=(
            "Polski przegląd Localo z dowodami źródłowymi, "
            "agregatami i zablokowanymi obietnicami."
        ),
        source_connectors=item.source_connectors,
        evidence_ids=item.evidence_ids,
        action_ids=item.action_ids,
        blocked_claims=item.blocked_claims,
        risk=ActionRisk.low,
    )


def _localo_readiness_action_plan_item(
    item: CommandCenterBriefItem,
) -> CommandCenterActionPlanItem:
    if item.status == "ready":
        return CommandCenterActionPlanItem(
            id="plan_localo_access_ready_wait_for_visibility_facts",
            title="Dostęp Localo działa; brakuje rankingów i danych profilu firmy w Google",
            route=item.route,
            status="ready",
            priority=60,
            category="Localo",
            why_it_matters=(
                "WILQ potwierdził dostęp Localo, więc to nie jest już blokada OAuth. "
                "Nadal brakuje konkretnych lokalnych rankingów, danych profilu firmy "
                "w Google i danych konkurencji, więc lokalnych rekomendacji "
                "nie wolno dopowiadać."
            ),
            operator_action=(
                "Nie pokazuj tego jako pilnego zadania marketera. Traktuj widok Localo "
                "jako status źródła do czasu dodania danych rankingów, profilu firmy "
                "w Google, konkurencji i recenzji."
            ),
            skill_id="wilq-localo-operator",
            codex_prompt=(
                "Użyj skilla wilq-localo-operator. Potwierdź dostęp Localo dla "
                "Ekologus i wskaż, jakich konkretnych danych rankingów i profilu firmy "
                "w Google brakuje do lokalnych rekomendacji. Nie twierdź nic o lokalnej "
                "widoczności bez dowodów."
            ),
            codex_context_endpoint="/api/codex/context-pack",
            expected_codex_output=(
                "Polski status Localo: dostęp działa, danych rankingów i profilu firmy "
                "w Google jeszcze brak."
            ),
            source_connectors=item.source_connectors,
            evidence_ids=item.evidence_ids,
            action_ids=item.action_ids,
            blocked_claims=item.blocked_claims,
            risk=ActionRisk.low,
        )
    return CommandCenterActionPlanItem(
        id="plan_finish_localo_access_before_local_visibility",
        title="Dokończ dostęp Localo przed lokalnymi rekomendacjami",
        route=item.route,
        status="blocked",
        priority=20,
        category="Localo",
        why_it_matters=(
            "Localo nie ma świeżych dowodów lokalnej widoczności, więc WILQ blokuje "
            "obietnice o rankingach i wynikach profilu firmy w Google."
        ),
        operator_action="Otwórz widok Localo i pokaż blokadę dostępu zamiast metryk lokalnych.",
        skill_id="wilq-localo-operator",
        codex_prompt=(
            "Użyj skilla wilq-localo-operator. Sprawdź stan Localo dla Ekologus "
            "i pokaż tylko status oraz blokady, dopóki WILQ nie ma świeżych dowodów "
            "lokalnej widoczności, rankingów albo profilu firmy w Google."
        ),
        codex_context_endpoint="/api/codex/context-pack",
        expected_codex_output=(
            "Polskie podsumowanie gotowości Localo z blokadami i bez obietnic o rankingach."
        ),
        source_connectors=item.source_connectors,
        evidence_ids=item.evidence_ids,
        action_ids=item.action_ids,
        blocked_claims=item.blocked_claims,
        risk=ActionRisk.medium,
    )


def _default_action_plan_item(item: CommandCenterBriefItem) -> CommandCenterActionPlanItem:
    return CommandCenterActionPlanItem(
        id=f"plan_{item.id}",
        title=item.title,
        route=item.route,
        status="ready" if item.status == "ready" else "blocked",
        priority=item.priority,
        category="WILQ",
        why_it_matters=item.summary,
        operator_action=item.next_step,
        skill_id="wilq-daily-command",
        codex_prompt=(
            "Użyj skilla wilq-daily-command. Skondensuj ten element Centrum pracy "
            "do decyzji marketera po polsku, używając tylko dowodów w WILQ."
        ),
        codex_context_endpoint="/api/codex/context-pack",
        expected_codex_output="Polska decyzja operatora z dowodami źródłowymi i następnym krokiem.",
        source_connectors=item.source_connectors,
        evidence_ids=item.evidence_ids,
        action_ids=item.action_ids,
        blocked_claims=item.blocked_claims,
        risk=item.risk,
    )


def _related_tactical_items(item: CommandCenterBriefItem, tactical_items: list[Any]) -> list[Any]:
    source_connectors = set(item.source_connectors)
    return [
        tactic
        for tactic in tactical_items
        if source_connectors.intersection(set(tactic.source_connectors))
    ]


def _ga4_tactic_summary(tactical_items: list[Any]) -> str:
    landings: dict[str, int] = {}
    for tactic in tactical_items:
        landing = getattr(tactic, "dimensions", {}).get("landing_page")
        if not landing:
            continue
        landings[landing] = landings.get(landing, 0) + 1
    if not landings:
        return "Brak gotowych taktyk jakości ruchu; braki w pomiarze sprawdź w widoku GA4."
    summary_parts = [
        f"{_short_landing_label(landing)} ({count} {_polish_group_label(count)})"
        for landing, count in list(landings.items())[:3]
    ]
    return "Skondensowane obszary jakości ruchu: " + ", ".join(summary_parts) + "."


def _short_landing_label(landing: str) -> str:
    if landing == "/":
        return "strona główna"
    return landing[:64]


def _polish_group_label(count: int) -> str:
    if count == 1:
        return "grupa"
    if 2 <= count <= 4:
        return "grupy"
    return "grup"


def _action_plan_status(item: CommandCenterBriefItem) -> Literal["ready", "blocked"]:
    return "ready" if item.status == "ready" else "blocked"


def _merge_ids(base_ids: list[str], tactical_items: list[Any], limit: int = 12) -> list[str]:
    merged = list(base_ids)
    for tactic in tactical_items:
        for evidence_id in tactic.evidence_ids:
            if evidence_id not in merged:
                merged.append(evidence_id)
    return merged[:limit]
