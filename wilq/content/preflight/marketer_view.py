from __future__ import annotations

from collections.abc import Iterable

from wilq.actions.content_refresh import content_contract_label
from wilq.content.canonical.urls import content_decision_final_canonical_url
from wilq.content.planning.decisions import (
    ContentDecisionType,
    format_percent,
    wordpress_match_tile,
)
from wilq.content.preflight.verdicts import (
    content_preflight_mode,
    content_preflight_next_step,
    content_preflight_query_overlap,
    content_preflight_similar_urls,
    content_preflight_status,
)
from wilq.operator_labels import evidence_count_label
from wilq.schemas import (
    ContentDecisionItem,
    ContentDiagnosticSection,
    ContentMarketerDecision,
    ContentPreflightItem,
)

CONTENT_WORDPRESS_MATCH_LABELS = {
    "found": "potwierdzony",
    "missing": "niepotwierdzone w WordPress",
}
CONTENT_WORDPRESS_MATCH_CONFIDENCE_LABELS = {
    "exact_url": "dokładny URL",
    "host_alias_sitemap": "alias hosta z sitemap",
    "path_fallback": "dopasowanie ścieżki",
    "missing": "dopasowanie niepotwierdzone",
}
CONTENT_PREFLIGHT_MODE_LABELS = {
    "preserve": "zachować",
    "refresh": "odświeżyć",
    "merge": "scalić",
    "create": "utworzyć",
    "block": "zablokować",
}
CONTENT_PREFLIGHT_STATUS_LABELS = {
    "allowed": "można przygotować",
    "review_required": "wymaga sprawdzenia",
    "blocked": "zablokowane",
}


def build_content_marketer_decision(
    decisions: list[ContentDecisionItem],
    sections: list[ContentDiagnosticSection],
) -> ContentMarketerDecision | None:
    if not decisions:
        return None
    decision = decisions[0]
    blocked_claims = content_marketer_blocked_claims(
        [
            *decision.blocked_claims,
            *(claim for section in sections for claim in section.blocked_claims),
        ]
    )
    source_public_url = decision.source_public_url or decision.page
    preview_url = decision.preview_url
    intended_final_url = decision.intended_final_url or source_public_url
    final_canonical_url = content_decision_final_canonical_url(decision)
    missing_inputs = content_marketer_missing_inputs(
        decision,
        final_canonical_url=final_canonical_url,
    )
    return ContentMarketerDecision(
        id=f"marketer_{decision.id}",
        technical_decision_id=decision.id,
        status=decision.status,
        decision=_content_marketer_decision_text(decision),
        mode_label=_content_marketer_mode_label(decision.decision_type),
        why_it_matters=_content_marketer_why(decision),
        safe_next_action=_content_marketer_next_action(decision),
        review_decision_after_review=_content_marketer_review_decision(decision),
        review_question_for_wilku=_content_marketer_review_question(decision),
        review_next_safe_click=_content_marketer_review_next_click(decision),
        review_action_ids=_content_marketer_review_action_ids(decision),
        metric_tiles=_content_marketer_metric_tiles(decision),
        content_angle=_content_marketer_content_angle(decision),
        h1_direction=_content_marketer_h1_direction(decision),
        h2_direction=_content_marketer_h2_direction(decision),
        faq_direction=_content_marketer_faq_direction(decision),
        cta_direction=_content_marketer_cta_direction(decision),
        source_facts=_content_marketer_source_facts(decision),
        blocked_claims=blocked_claims,
        missing_inputs=missing_inputs,
        evidence_summary=_content_marketer_evidence_summary(decision),
        source_connectors=decision.source_connectors,
        evidence_ids=decision.evidence_ids,
        measurement_plan=_content_marketer_measurement_plan(decision),
        source_public_url=source_public_url,
        preview_url=preview_url,
        intended_final_url=intended_final_url,
        final_canonical_url=final_canonical_url,
    )


def build_content_preflight_item(decision: ContentDecisionItem) -> ContentPreflightItem:
    recommended_mode = content_preflight_mode(decision)
    status = content_preflight_status(decision, recommended_mode)
    source_public_url = decision.source_public_url or decision.page
    final_canonical_url = content_decision_final_canonical_url(decision)
    missing_inputs = content_marketer_missing_inputs(
        decision,
        final_canonical_url=final_canonical_url,
    )
    claim_gate_status = (
        "needs_claim_review" if decision.blocked_claims else "ready_for_claim_review"
    )
    service_fit_status = (
        "needs_service_review"
        if decision.decision_type in {"review_ahrefs_gap_records", "inventory_check_before_create"}
        else "ready_for_service_review"
    )
    return ContentPreflightItem(
        id=f"preflight_{decision.id}",
        technical_decision_id=decision.id,
        recommended_mode=recommended_mode,
        recommended_mode_label=content_preflight_mode_label(recommended_mode),
        status=status,
        status_label=content_preflight_status_label(status),
        create_allowed=recommended_mode == "create" and status == "allowed",
        draft_allowed=False,
        wordpress_draft_allowed=False,
        sales_brief_allowed=status in {"allowed", "review_required"}
        and recommended_mode in {"preserve", "refresh", "merge"},
        source_public_url=source_public_url,
        preview_url=decision.preview_url,
        intended_final_url=decision.intended_final_url or source_public_url,
        final_canonical_url=final_canonical_url,
        inventory_gate_status=decision.inventory_gate_status,
        inventory_gate_status_label=content_gate_label(decision.inventory_gate_status),
        canonical_gate_status=decision.canonical_gate_status,
        canonical_gate_status_label=content_gate_label(decision.canonical_gate_status),
        duplicate_gate_status=decision.duplicate_gate_status,
        duplicate_gate_status_label=content_gate_label(decision.duplicate_gate_status),
        claim_gate_status=claim_gate_status,
        claim_gate_status_label=content_contract_label(claim_gate_status),
        service_fit_status=service_fit_status,
        service_fit_status_label=content_contract_label(service_fit_status),
        similar_existing_urls=content_preflight_similar_urls(decision),
        query_overlap_summary=content_preflight_query_overlap(decision),
        blocked_claims=content_marketer_blocked_claims(decision.blocked_claims),
        missing_inputs=missing_inputs,
        evidence_ids=decision.evidence_ids,
        evidence_summary_label=evidence_count_label(decision.evidence_ids),
        source_connectors=decision.source_connectors,
        next_step=content_preflight_next_step(decision, recommended_mode, status),
    )


def content_decision_type_summary_label(decision_type: ContentDecisionType) -> str:
    if decision_type == "block_until_vendor_read":
        return "blokada do czasu odczytu danych"
    if decision_type == "refresh_or_merge":
        return "odświeżenie albo scalenie"
    if decision_type == "merge_create_after_inventory_check":
        return "scalenie albo nowa treść po kontroli spisu"
    if decision_type == "inventory_check_before_create":
        return "blokada nowej treści do czasu kontroli spisu"
    if decision_type == "block_as_tracking_not_content":
        return "problem pomiaru, nie treści"
    return "luki Ahrefs do ręcznej oceny"


def content_gate_label(value: str | None) -> str | None:
    if not value:
        return None
    return content_contract_label(value)


def content_preflight_mode_label(value: str) -> str:
    return CONTENT_PREFLIGHT_MODE_LABELS.get(value, content_contract_label(value))


def content_preflight_status_label(value: str) -> str:
    return CONTENT_PREFLIGHT_STATUS_LABELS.get(value, content_contract_label(value))


def content_wordpress_match_label(value: str | None) -> str | None:
    if not value:
        return None
    return CONTENT_WORDPRESS_MATCH_LABELS.get(value, content_contract_label(value))


def content_wordpress_match_confidence_label(value: str | None) -> str | None:
    if not value:
        return None
    return CONTENT_WORDPRESS_MATCH_CONFIDENCE_LABELS.get(value, content_contract_label(value))


def content_blocked_claim_labels(claims: Iterable[str]) -> list[str]:
    return content_marketer_blocked_claims(claims)


def content_marketer_missing_inputs(
    decision: ContentDecisionItem,
    *,
    final_canonical_url: str | None,
) -> list[str]:
    values: list[str] = []
    if decision.wordpress_match == "missing":
        values.append("potwierdzenie, czy temat istnieje już w WordPress")
    if decision.inventory_gate_status and decision.inventory_gate_status not in {
        "confirmed_current_inventory",
        "not_applicable",
    }:
        values.append("kontrola spisu treści i istniejącego URL")
    if decision.canonical_gate_status and decision.canonical_gate_status not in {
        "public_canonical_confirmed",
        "not_applicable",
    }:
        values.append("potwierdzony adres kanoniczny na ekologus.pl")
    if decision.duplicate_gate_status and decision.duplicate_gate_status not in {
        "existing_public_content_requires_refresh_or_merge",
        "not_applicable",
    }:
        values.append("kontrola duplikacji i kanibalizacji")
    if not decision.evidence_ids:
        values.append("dowód źródłowy w WILQ")
    return _unique(values) or ["brak dodatkowych danych przed sprawdzeniem"]


def content_marketer_blocked_claims(claims: Iterable[str]) -> list[str]:
    labels = {
        "wordpress_publish": "publikacja w WordPress bez sprawdzenia",
        "wordpress_write": "zapis do WordPress bez potwierdzenia",
        "wordpress_draft_ready_claim": "twierdzenie, że szkic jest gotowy do sprawdzenia",
        "automatyczna publikacja": "automatyczna publikacja",
        "lead_" + "up" + "lift": "wzrost liczby leadów",
        "ranking_guarantee": "gwarancja wzrostu pozycji",
        "revenue_impact": "wpływ na przychód",
        "traffic_" + "up" + "lift": "wzrost ruchu",
        "wzrost liczby leadów": "wzrost liczby leadów",
        "gwarancja wzrostu pozycji": "gwarancja wzrostu pozycji",
        "wpływ na przychód": "wpływ na przychód",
        "wzrost ruchu": "wzrost ruchu",
        "rekomendacja bez danych źródłowych": "rekomendacja bez danych źródłowych",
    }
    return _unique(labels.get(claim, "obietnica do sprawdzenia") for claim in claims)


def _content_marketer_decision_text(decision: ContentDecisionItem) -> str:
    if decision.decision_type == "block_until_vendor_read":
        return (
            "Nie podejmuj decyzji contentowej, dopóki WILQ nie ma świeżych "
            "danych z GSC i WordPress."
        )
    if decision.decision_type == "refresh_or_merge":
        return (
            "Zachowaj istniejącą treść i przygotuj odświeżenie albo scalenie, "
            "zamiast pisać nowy tekst od zera."
        )
    if decision.decision_type == "merge_create_after_inventory_check":
        return (
            "Najpierw sprawdź, czy temat nie dubluje istniejącej treści; "
            "dopiero potem wybierz scalenie albo utworzenie nowej treści."
        )
    if decision.decision_type == "inventory_check_before_create":
        return (
            "Nie pisz jeszcze nowej treści; najpierw potwierdź, czy temat "
            "nie istnieje już w WordPress."
        )
    if decision.decision_type == "block_as_tracking_not_content":
        return "To wygląda jak problem pomiaru GA4, nie zadanie do pisania treści."
    return (
        "Sprawdź lukę contentową z Ahrefs tylko jako materiał do oceny, "
        "nie jako samodzielny powód do publikacji."
    )


def _content_marketer_mode_label(decision_type: ContentDecisionType) -> str:
    labels: dict[ContentDecisionType, str] = {
        "block_until_vendor_read": "blokada danych",
        "refresh_or_merge": "zachować i odświeżyć",
        "merge_create_after_inventory_check": "sprawdzić duplikację",
        "inventory_check_before_create": "sprawdzić istniejącą treść",
        "block_as_tracking_not_content": "naprawić pomiar",
        "review_ahrefs_gap_records": "sprawdzić lukę",
    }
    return labels[decision_type]


def _content_marketer_why(decision: ContentDecisionItem) -> str:
    if decision.decision_type == "refresh_or_merge":
        query = f" dla zapytania `{decision.primary_query}`" if decision.primary_query else ""
        return (
            f"WordPress potwierdza istniejący URL{query}, więc bezpieczniej wzmocnić "
            "obecną treść niż tworzyć konkurującą stronę."
        )
    if decision.decision_type in {
        "merge_create_after_inventory_check",
        "inventory_check_before_create",
    }:
        return (
            "GSC pokazuje popyt, ale WILQ nie ma pełnego potwierdzenia, że temat "
            "nie istnieje już w treściach. Pisanie bez tej kontroli grozi duplikacją."
        )
    if decision.decision_type == "block_as_tracking_not_content":
        return (
            "Braki w wymiarach GA4 mogą fałszować ocenę strony wejścia, więc najpierw "
            "trzeba poprawić pomiar."
        )
    if decision.decision_type == "review_ahrefs_gap_records":
        return (
            "Ahrefs może wskazać temat do sprawdzenia, ale sama luka konkurencji nie "
            "wystarcza do decyzji o nowej publikacji bez GSC i spisu treści."
        )
    return (
        "Brakuje podstawowych danych z GSC lub WordPress, więc WILQ może pokazać "
        "tylko blocker, nie rekomendację."
    )


def _content_marketer_next_action(decision: ContentDecisionItem) -> str:
    if decision.decision_type == "refresh_or_merge":
        return (
            "Przejrzyj wskazany URL, zachowaj sekcje nadal aktualne, wypisz braki "
            "w H1/H2/FAQ/CTA i dopiero potem przygotuj plan treści do sprawdzenia."
        )
    if decision.decision_type in {
        "merge_create_after_inventory_check",
        "inventory_check_before_create",
    }:
        return (
            "Potwierdź istniejący URL, kanoniczny adres i ryzyko duplikacji. Jeśli "
            "kontrola przejdzie, WILQ może przygotować plan treści; "
            "jeśli nie, temat zostaje zablokowany."
        )
    if decision.decision_type == "block_as_tracking_not_content":
        return "Napraw lub potwierdź tracking GA4, a potem wróć do oceny treści."
    if decision.decision_type == "review_ahrefs_gap_records":
        return (
            "Porównaj lukę z GSC i WordPress; traktuj ją jako inspirację "
            "do sprawdzenia, nie gotową decyzję."
        )
    return "Uruchom odczyt danych GSC i spisu treści WordPress, potem odśwież widok treści."


def _content_marketer_review_decision(decision: ContentDecisionItem) -> str:
    if decision.decision_type == "refresh_or_merge":
        return (
            "Po sprawdzeniu strony zatwierdź odświeżenie albo scalenie istniejącego URL-a, "
            "nie nowy artykuł."
        )
    if decision.decision_type in {
        "merge_create_after_inventory_check",
        "inventory_check_before_create",
    }:
        return (
            "Po kontroli spisu treści wybierz scalenie z istniejącym URL-em, nową treść "
            "albo blokadę tematu."
        )
    if decision.decision_type == "block_as_tracking_not_content":
        return "Najpierw potwierdź problem pomiaru; decyzja contentowa zostaje zablokowana."
    if decision.decision_type == "review_ahrefs_gap_records":
        return (
            "Traktuj lukę jako temat do ręcznej oceny; decyzja powstaje dopiero po "
            "sprawdzeniu GSC i WordPress."
        )
    return "Nie zatwierdzaj decyzji contentowej, dopóki nie wrócą dane GSC i WordPress."


def _content_marketer_review_question(decision: ContentDecisionItem) -> str:
    topic = _content_marketer_topic(decision)
    if decision.decision_type == "refresh_or_merge":
        return (
            f"Czy istniejąca strona ma dalej obsługiwać intencję `{topic}`, czy lepiej "
            "przenieść część tematu do osobnej podstrony usługowej?"
        )
    if decision.decision_type in {
        "merge_create_after_inventory_check",
        "inventory_check_before_create",
    }:
        return (
            f"Czy temat `{topic}` już istnieje w treściach Ekologus, a jeśli tak, "
            "który adres ma być kanoniczny?"
        )
    if decision.decision_type == "block_as_tracking_not_content":
        return "Czy problem dotyczy pomiaru GA4, czy faktycznie treści na stronie?"
    if decision.decision_type == "review_ahrefs_gap_records":
        return (
            f"Czy temat `{topic}` pasuje do oferty Ekologus i ma potwierdzenie poza Ahrefs?"
        )
    return "Czy możemy odświeżyć dane GSC i WordPress przed decyzją?"


def _content_marketer_review_next_click(decision: ContentDecisionItem) -> str:
    if "act_prepare_content_refresh_queue" in decision.action_ids:
        return (
            "Kliknij podgląd `act_prepare_content_refresh_queue`; to przygotuje review, "
            "bez zapisu i bez publikacji."
        )
    if decision.action_ids:
        return (
            f"Kliknij podgląd `{decision.action_ids[0]}`; to jest krok review, "
            "bez zapisu i bez publikacji."
        )
    return "Najpierw odśwież dane albo wybierz decyzję z kolejki; nie publikuj."


def _content_marketer_review_action_ids(decision: ContentDecisionItem) -> list[str]:
    return _unique(
        action_id
        for action_id in decision.action_ids
        if action_id == "act_prepare_content_refresh_queue"
    )


def _content_marketer_metric_tiles(decision: ContentDecisionItem) -> dict[str, int | float | str]:
    tiles: dict[str, int | float | str] = {}
    if decision.query_count:
        tiles["Zapytania"] = decision.query_count
    if decision.total_clicks is not None:
        tiles["Kliknięcia"] = decision.total_clicks
    if decision.total_impressions is not None:
        tiles["Wyświetlenia"] = decision.total_impressions
    if decision.aggregate_ctr is not None:
        tiles["CTR"] = format_percent(decision.aggregate_ctr)
    if decision.best_average_position is not None:
        tiles["Pozycja"] = round(decision.best_average_position, 2)
    if not tiles:
        tiles.update(decision.metric_tiles)
    return dict(list(tiles.items())[:4])


def _content_marketer_topic(decision: ContentDecisionItem) -> str:
    return decision.primary_query or decision.title or "ten temat"


def _content_marketer_content_angle(decision: ContentDecisionItem) -> str:
    topic = _content_marketer_topic(decision)
    if decision.decision_type == "refresh_or_merge":
        return (
            f"Zachowaj istniejącą treść i odśwież ją wokół intencji: {topic}. "
            "Nie obiecuj wzrostu pozycji, leadów ani przychodu."
        )
    if decision.decision_type in {
        "merge_create_after_inventory_check",
        "inventory_check_before_create",
    }:
        return (
            f"Najpierw sprawdź, czy temat {topic} nie dubluje istniejącej treści. "
            "Plan pisania powstaje dopiero po kontroli spisu i kanonicznego URL-a."
        )
    if decision.decision_type == "block_as_tracking_not_content":
        return (
            "To nie jest jeszcze temat do pisania. Najpierw trzeba potwierdzić jakość pomiaru GA4."
        )
    if decision.decision_type == "review_ahrefs_gap_records":
        return (
            f"Traktuj temat {topic} jako inspirację do sprawdzenia, nie jako gotowy brief. "
            "Potrzebne jest zestawienie z GSC i WordPress."
        )
    return "Brakuje danych źródłowych, więc WILQ pokazuje tylko blokadę decyzji contentowej."


def _content_marketer_h1_direction(decision: ContentDecisionItem) -> str:
    topic = _content_marketer_topic(decision)
    if decision.decision_type == "block_until_vendor_read":
        return "H1 powstaje dopiero po odczycie GSC i spisu treści WordPress."
    if decision.decision_type == "block_as_tracking_not_content":
        return "Nie przygotowuj H1, dopóki problem pomiaru nie jest rozdzielony od jakości treści."
    return f"H1 ma jasno odpowiedzieć na intencję: {topic}."


def _content_marketer_h2_direction(decision: ContentDecisionItem) -> list[str]:
    topic = _content_marketer_topic(decision)
    if decision.decision_type == "block_until_vendor_read":
        return ["odczyt danych GSC", "spis treści WordPress"]
    if decision.decision_type == "refresh_or_merge":
        return [
            f"co już odpowiada na temat {topic}",
            "co wymaga aktualizacji",
            "czego nie wolno obiecać",
        ]
    if decision.decision_type in {
        "merge_create_after_inventory_check",
        "inventory_check_before_create",
    }:
        return [
            "istniejące treści do sprawdzenia",
            "ryzyko duplikacji",
            "decyzja: zachować, odświeżyć, scalić albo utworzyć",
        ]
    if decision.decision_type == "block_as_tracking_not_content":
        return ["brak pomiaru", "co trzeba naprawić przed oceną treści"]
    return ["luka do sprawdzenia", "popyt w GSC", "dopasowanie do oferty Ekologus"]


def _content_marketer_faq_direction(decision: ContentDecisionItem) -> list[str]:
    topic = _content_marketer_topic(decision)
    if decision.decision_type == "block_until_vendor_read":
        return ["Jakie dane muszą wrócić, zanim powstanie plan treści?"]
    if decision.decision_type == "block_as_tracking_not_content":
        return ["Czy problem wynika z pomiaru, czy z jakości treści?"]
    return [
        f"Co oznacza {topic} dla firmy?",
        "Kiedy warto skonsultować temat z Ekologus?",
    ]


def _content_marketer_cta_direction(decision: ContentDecisionItem) -> str:
    if decision.decision_type in {
        "block_until_vendor_read",
        "block_as_tracking_not_content",
    }:
        return "CTA zostaje zablokowane do czasu uzupełnienia danych."
    return "CTA do konsultacji wpływu wymagań środowiskowych na firmę, bez obietnic wyniku."


def _content_marketer_source_facts(decision: ContentDecisionItem) -> list[str]:
    facts: list[str] = []
    if decision.source_public_url or decision.page:
        facts.append(f"URL publiczny: {decision.source_public_url or decision.page}")
    if decision.primary_query:
        facts.append(f"Główne zapytanie: {decision.primary_query}")
    if decision.total_clicks is not None:
        facts.append(f"Kliknięcia GSC: {decision.total_clicks}")
    if decision.total_impressions is not None:
        facts.append(f"Wyświetlenia GSC: {decision.total_impressions}")
    if decision.wordpress_match_label:
        facts.append(f"Spis treści WordPress: {decision.wordpress_match_label}")
    elif decision.wordpress_match:
        facts.append(f"Spis treści WordPress: {wordpress_match_tile(decision.wordpress_match)}")
    return facts[:5]


def _content_marketer_evidence_summary(decision: ContentDecisionItem) -> str:
    connector_count = len(decision.source_connectors)
    evidence_count = len(decision.evidence_ids)
    if decision.primary_query:
        return (
            f"Decyzja opiera się na {evidence_count} dowodach z {connector_count} źródeł; "
            f"główne zapytanie: {decision.primary_query}."
        )
    return f"Decyzja opiera się na {evidence_count} dowodach z {connector_count} źródeł."


def _content_marketer_measurement_plan(decision: ContentDecisionItem) -> str:
    url = decision.final_canonical_url or decision.source_public_url or decision.page
    url_part = f" dla {url}" if url else ""
    return (
        f"Po publikacji lub odświeżeniu porównaj GSC i GA4 przed/po{url_part}. "
        "Bez okna pomiarowego WILQ nie może twierdzić, że zmiana poprawiła "
        "pozycje, leady albo konwersje."
    )


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values
