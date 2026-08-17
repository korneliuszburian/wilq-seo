from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from wilq.content.operator_copy import unique_present
from wilq.schemas import MetricFact

__all__ = [
    "CONTENT_REFRESH_ACTION_TYPE",
    "CONTENT_BRIEF_PREVIEW_CONTRACT",
    "CONTENT_URL_REVIEW_CONTRACT",
    "WORDPRESS_DRAFT_PAYLOAD_PREVIEW_CONTRACT",
    "POST_PUBLICATION_MEASUREMENT_PLAN_CONTRACT",
    "CONTENT_SOURCE_SITE_HOSTS",
    "CONTENT_SOURCE_CONNECTORS",
    "GSC_METRIC_NAMES",
    "AHREFS_GAP_FACT_NAMES",
    "AHREFS_RELEVANCE_TERMS",
    "AHREFS_RELEVANT_COMPETITOR_DOMAINS",
    "AHREFS_OFF_TOPIC_TERMS",
    "CONTENT_BLOCKED_CLAIMS",
    "CONTENT_CONTRACT_LABELS",
    "_prioritized_content_contract_values",
    "_string_list",
    "_normalized_url",
    "_content_preview_url_semantics",
    "_gsc_metric_snapshot",
    "_gsc_metric_snapshot_labels",
    "_gsc_brief_goal",
    "_content_angle",
    "_content_intent",
    "_ahrefs_content_angle",
    "_ahrefs_content_intent",
    "_content_audience",
    "_key_objections",
    "_h1_direction",
    "_seo_title_direction",
    "_meta_description_direction",
    "_h2_direction",
    "_faq_direction",
    "_schema_direction",
    "_cta_direction",
    "_legal_review_notes",
    "_brand_voice_notes",
    "_publication_blockers",
    "_internal_link_direction",
    "_gsc_source_facts",
    "_gsc_missing_evidence",
    "_ahrefs_source_facts",
    "_brief_outline",
    "_gsc_required_validation",
    "_ahrefs_topic",
    "_ahrefs_preview_score",
    "_metric_numeric_sort_value",
    "_normalize_text",
    "_metric_sum",
    "_metric_sum_or_missing",
    "_first_metric_or_missing",
    "_normalized_path",
    "_short_path",
    "_url_host",
    "_candidate_slug_for_page",
    "_slug",
]



CONTENT_REFRESH_ACTION_TYPE = "wordpress_content_refresh"


CONTENT_BRIEF_PREVIEW_CONTRACT = "content_brief_preview_v1"


CONTENT_URL_REVIEW_CONTRACT = "content_url_preflight_review_v1"


WORDPRESS_DRAFT_PAYLOAD_PREVIEW_CONTRACT = "wordpress_draft_payload_preview_v1"


POST_PUBLICATION_MEASUREMENT_PLAN_CONTRACT = "post_publication_measurement_plan_v1"


CONTENT_SOURCE_SITE_HOSTS = {
    "www.ekologus.pl",
    "ekologus.pl",
    "sklep.ekologus.pl",
}


CONTENT_SOURCE_CONNECTORS = {
    "google_search_console",
    "wordpress_ekologus",
    "wordpress_sklep",
    "google_analytics_4",
    "ahrefs",
}


GSC_METRIC_NAMES = {"clicks", "impressions", "ctr", "average_position"}


AHREFS_GAP_FACT_NAMES = {
    "ahrefs_content_gap_count",
    "ahrefs_organic_keyword_gap_count",
    "ahrefs_top_page_gap_count",
    "ahrefs_competitor_page_count",
}


AHREFS_RELEVANCE_TERMS = (
    "bdo",
    "odpady",
    "odpad",
    "srodowisko",
    "srodowiskowy",
    "remediacja",
    "operat",
    "wodnoprawny",
    "pozwolenie",
    "zintegrowane",
    "zielony lad",
    "ppwr",
    "recykling",
    "emisja",
    "esg",
    "beczka",
    "sorbent",
    "magazynowanie",
    "substancje",
    "chemiczne",
    "denios",
)


AHREFS_RELEVANT_COMPETITOR_DOMAINS = {
    "denios.pl",
    "dla-przemyslu.pl",
    "manutan.pl",
}


AHREFS_OFF_TOPIC_TERMS = (
    "prawo jazdy",
    "kalkulator oc",
    "ubezpieczenie",
    "samochod",
    "samochodu",
    "cuk.pl",
    "ltesty.pl",
)


CONTENT_BLOCKED_CLAIMS = [
    "wzrost liczby leadów",
    "wpływ na przychód",
    "gwarancja pozycji",
    "wzrost ruchu",
    "wzrost autorytetu",
    "automatyczna publikacja WordPress",
]


CONTENT_CONTRACT_LABELS = {
    "api_mutation_ready_false": "zapis zmian nie jest gotowy",
    "approve_outline_for_editorial_review": "zatwierdź plan do redakcji",
    "automatyczna publikacja WordPress": "automatyczna publikacja WordPress",
    "automatic_wordpress_write": "automatyczny zapis WordPress",
    "block_until_public_inventory_known": "blokada do czasu spisu publicznych treści",
    "blocked_preview_only": "zablokowane do czasu kontroli",
    "block": "zablokuj",
    "business_relevance_review": "sprawdzenie dopasowania biznesowego",
    "canonical_review": "kontrola URL-a kanonicznego",
    "canonical_needs_target_confirmation": "trzeba potwierdzić URL kanoniczny",
    "canonical_review_outcome": "wynik kontroli URL-a kanonicznego",
    "candidate_id": "ID wybranej propozycji",
    "confirm_existing_public_url": "potwierdź istniejący publiczny URL",
    "confirm_final_canonical_url": "potwierdź finalny URL kanoniczny",
    "content_draft_readiness_review": "kontrola gotowości szkicu",
    "content_draft_generation_v1": "generowanie szkicu",
    "content_url_preflight_review": "potwierdzenie publicznego URL-a",
    "content_url_preflight_review_v1": "potwierdzenie publicznego URL-a",
    "content_url_review_recorded_review_only": "kontrola URL-a zapisana do sprawdzenia",
    "create": "utwórz po kontroli",
    "duplicate_free_claim_without_review": "obietnica braku duplikacji bez kontroli",
    "duplicate_free_claim": "obietnica braku duplikacji",
    "duplicate_or_cannibalization_check": "kontrola duplikacji i kanibalizacji",
    "duplicate_review_outcome": "wynik kontroli duplikacji",
    "evidence_ids_present": "dowody są podpięte",
    "final_canonical_review": "kontrola URL-a kanonicznego",
    "inventory_check": "sprawdź spis treści",
    "legal_factual_review": "kontrola prawna i faktograficzna",
    "legal_factual_review_outcome": "wynik kontroli prawnej i faktograficznej",
    "human_confirm_before_wordpress_write": "potwierdzenie człowieka przed zapisem WordPress",
    "mark_preview_design_context_not_required": "podgląd projektu nie jest wymagany",
    "operator_review_approved_for_prepare": "operator zatwierdził przygotowanie",
    "merge_required_before_draft": "najpierw trzeba rozstrzygnąć scalenie",
    "merge": "scal z istniejącą treścią",
    "needs_canonical_fix": "trzeba poprawić kanoniczny URL",
    "needs_duplicate_resolution": "trzeba rozstrzygnąć duplikację",
    "needs_expert_review": "wymaga kontroli eksperta",
    "needs_claim_review": "wymaga kontroli obietnic",
    "needs_service_review": "wymaga dopasowania do usługi",
    "new_content_without_inventory_check": "nowa treść bez sprawdzenia spisu",
    "notes": "notatki",
    "outline_only_until_checks_complete": "plan treści do czasu kontroli",
    "present": "jest",
    "prepare_only_review_recorded": "zapisano ocenę przygotowania",
    "non_public_url_as_final_canonical": "niepubliczny URL jako finalny URL kanoniczny",
    "publish_ready_claim": "obietnica gotowości do publikacji",
    "production_wordpress_write": "zapis na produkcyjnym WordPressie",
    "public_content_inventory_required": "wymagany spis publicznych treści",
    "ready_for_review": "gotowe do sprawdzenia",
    "ready_for_claim_review": "gotowe do kontroli obietnic",
    "ready_for_service_review": "gotowe do sprawdzenia dopasowania usługi",
    "review": "do sprawdzenia",
    "ranking_guarantee": "gwarancja pozycji",
    "refresh": "odśwież istniejącą treść",
    "review_only": "do kontroli",
    "wordpress_draft_handoff_action_required": "wymagany osobny krok WordPress",
    "wordpress_draft_handoff_v1": "zapis szkicu WordPress",
    "wordpress_draft_payload_preview": "podgląd wpisu WordPress",
    "wordpress_draft_payload_preview_required": "wymagany podgląd wpisu WordPress",
    "wordpress_draft_payload_review": "kontrola podglądu wpisu WordPress",
    "wordpress_draft_write": "zapis szkicu WordPress",
    "wordpress_draft_write_not_requested": "zapis szkicu WordPress nie został zlecony",
    "wordpress_publish": "publikacja WordPress",
    "wordpress_write_not_requested": "zapis WordPress nie został zlecony",
    "gsc_query_page_check": "sprawdzenie zapytań i URL-i z GSC",
    "gsc_demand_check": "sprawdzenie popytu w GSC",
    "wordpress_existing_url_confirmed": "istniejący URL potwierdzony w WordPress",
    "wordpress_inventory_check": "sprawdzenie spisu treści WordPress",
    "source_connectors_present": "źródła danych są podpięte",
    "source_public_url": "publiczny URL źródłowy",
    "final_canonical_url": "finalny URL kanoniczny",
    "intended_final_url": "docelowy URL publiczny",
    "confirmed_current_inventory": "spis potwierdzony na obecnej stronie",
    "public_canonical_confirmed": "publiczny URL kanoniczny potwierdzony",
    "existing_public_content_requires_refresh_or_merge": (
        "istniejąca publiczna treść wymaga odświeżenia albo scalenia"
    ),
    "missing_inventory_match": "brak dopasowania w spisie treści",
    "blocked_until_inventory_review": "zablokowane do sprawdzenia spisu",
    "blocked_until_content_url_review": "zablokowane do sprawdzenia URL-a",
    "blocked_until_relevance_review": "zablokowane do sprawdzenia dopasowania",
    "create_blocked_until_duplicate_check": "utworzenie zablokowane do kontroli duplikacji",
    "manual_merge_or_create_review": "ręcznie rozstrzygnij scalenie albo utworzenie",
    "missing": "zakres treści niepotwierdzony",
    "not_applicable": "nie dotyczy",
    "28d_before_publish": "28 dni przed publikacją",
    "7d_after_publish": "7 dni po publikacji",
    "28d_after_publish": "28 dni po publikacji",
    "90d_after_publish": "90 dni po publikacji",
    "google_search_console": "Google Search Console",
    "google_analytics_4": "GA4",
    "gwarancja pozycji": "gwarancja pozycji",
    "wordpress_ekologus": "WordPress Ekologus",
    "wpływ na przychód": "wpływ na przychód",
    "wzrost autorytetu": "wzrost autorytetu",
    "wzrost liczby leadów": "wzrost liczby leadów",
    "wzrost ruchu": "wzrost ruchu",
    "ranking_gain_claim": "obietnica wzrostu pozycji",
    "revenue_impact_claim": "obietnica wpływu na przychód",
    "content_success_verdict": "werdykt skuteczności treści",
    "automatic_refresh_followup": "automatyczne odświeżenie po publikacji",
    "published_url_confirmed": "opublikowany URL potwierdzony",
    "baseline_window_captured": "punkt odniesienia zapisany",
    "followup_window_captured": "okno pomiaru po publikacji zapisane",
    "gsc_query_page": "Google Search Console",
    "ahrefs_gap_review": "Ahrefs do sprawdzenia",
    "same_url_or_redirect_mapping_confirmed": "ten sam URL albo przekierowanie potwierdzone",
    "tracking_quality_review": "kontrola jakości pomiaru",
    "gsc_query_page_clicks_impressions_ctr_position": (
        "kliknięcia, wyświetlenia, CTR i pozycja z GSC"
    ),
    "ga4_landing_engagement_and_key_events": "zaangażowanie i zdarzenia GA4",
    "wordpress_publish_metadata": "metadane publikacji WordPress",
    "reviewable_polish_draft_preview": "polska wersja robocza do kontroli",
    "prepare_existing_content_draft": "wersja robocza istniejącej treści",
    "prepare_new_content_draft_review": "wersja robocza nowej treści do sprawdzenia",
    "draft": "szkic",
    "pending": "czeka na sprawdzenie",
    "future": "zaplanowany",
    "private": "prywatny",
    "publish": "opublikowany",
    "blocked_until_review": "zablokowane do sprawdzenia",
    "blocked_until_content_review": "zablokowany do kontroli treści i URL-a",
    "blocked_pending_canonical_duplicate_review": "zablokowany do kontroli URL-i i duplikatów",
    "blocked_pending_canonical_duplicate_review_after_url_review": (
        "zablokowany do kontroli URL-i i duplikatów"
    ),
    "blocked_missing_public_inventory": "zablokowany bez spisu publicznych treści",
    "legal_compliance_guarantee": "gwarancja zgodności prawnej",
    "request_duplicate_or_canonical_review": "poproś o kontrolę duplikacji albo URL-a kanonicznego",
    "review_outcome": "wynik sprawdzenia",
    "human_review_outcome": "wynik decyzji człowieka",
    "reviewed_by": "sprawdzający",
    "reject_until_source_evidence": "odrzuć do czasu uzupełnienia dowodów",
    "needs_legal_review": "wymaga kontroli prawnej",
}


def _prioritized_content_contract_values(
    values: Iterable[str],
    priority: Iterable[str],
) -> list[str]:
    value_list = list(values)
    priority_list = [item for item in priority if item in value_list]
    return [*priority_list, *[item for item in value_list if item not in priority_list]]


def _string_list(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _normalized_url(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    host = parsed.netloc.lower()
    path = _normalized_path(value)
    if not host or not path:
        return ""
    return f"{parsed.scheme.lower() or 'https'}://{host}{path}"


def _content_preview_url_semantics(
    *,
    source_url: str,
    wordpress_content_url: str | None,
) -> dict[str, str | bool | None]:
    source_public_url = source_url
    intended_final_url = (
        wordpress_content_url
        if _url_host(wordpress_content_url) in CONTENT_SOURCE_SITE_HOSTS
        else source_public_url
    )
    return {
        "source_public_url": source_public_url,
        "preview_url": None,
        "intended_final_url": intended_final_url,
        "final_canonical_url": intended_final_url,
    }


def _gsc_metric_snapshot(page_facts: list[MetricFact]) -> dict[str, int | float | str]:
    return {
        "queries": len(
            unique_present(
                fact.dimensions.get("query") for fact in page_facts if fact.dimensions.get("query")
            )
        ),
        "clicks": _metric_sum_or_missing(page_facts, "clicks"),
        "impressions": _metric_sum_or_missing(page_facts, "impressions"),
        "ctr": _first_metric_or_missing(page_facts, "ctr"),
        "average_position": _first_metric_or_missing(page_facts, "average_position"),
    }


def _gsc_metric_snapshot_labels() -> dict[str, str]:
    return {
        "queries": "zapytania",
        "clicks": "kliknięcia",
        "impressions": "wyświetlenia",
        "ctr": "CTR",
        "average_position": "pozycja",
    }


def _gsc_brief_goal(wordpress_match: bool, primary_query: str) -> str:
    if wordpress_match:
        return (
            f"Przygotuj plan odświeżenia albo scalenia istniejącej treści pod temat "
            f"`{primary_query}`: title, H1/H2, braki w sekcjach, CTA i ryzykowne obietnice."
        )
    return (
        f"Sprawdź spis treści i duplikaty przed planem treści dla `{primary_query}`. "
        "Bez potwierdzenia URL nie twórz nowej strony."
    )


def _content_angle(topic: str, wordpress_match: bool) -> str:
    if wordpress_match:
        return (
            f"Odśwież istniejącą treść tak, żeby szybciej odpowiadała na intencję "
            f"`{topic}` i prowadziła do właściwej usługi Ekologus bez obietnic wyniku."
        )
    return (
        f"Najpierw potwierdź, czy temat `{topic}` nie ma już kanonicznej strony; "
        "dopiero potem przygotuj nowy lub scalony plan treści."
    )


def _content_intent(topic: str, wordpress_match: bool) -> str:
    normalized = _normalize_text(topic)
    if "bdo" in normalized:
        base = (
            "informacyjno-konsultacyjna: użytkownik chce szybko zrozumieć "
            "obowiązek BDO i sprawdzić, czy potrzebuje wsparcia eksperta"
        )
    elif "zielony lad" in normalized or "esg" in normalized:
        base = (
            "edukacyjno-regulacyjna: użytkownik szuka prostego wyjaśnienia "
            "regulacji i konsekwencji dla firmy"
        )
    elif "operat" in normalized or "pozwolen" in normalized:
        base = (
            "konsultacyjna: użytkownik chce ustalić wymagania formalne i kolejny krok postępowania"
        )
    elif "odpad" in normalized or "beczk" in normalized or "sorbent" in normalized:
        base = (
            "produktowo-procesowa: użytkownik sprawdza rozwiązanie lub proces "
            "dla bezpiecznej gospodarki odpadami"
        )
    else:
        base = (
            "do potwierdzenia: WILQ ma sygnał popytu, ale ekspert musi "
            "doprecyzować intencję przed pisaniem"
        )
    if wordpress_match:
        return f"{base}; tryb odświeżenia albo scalenia istniejącej strony"
    return f"{base}; nowa treść zablokowana do kontroli spisu treści i duplikatów"


def _ahrefs_content_angle(topic: str) -> str:
    return (
        f"Potraktuj `{topic}` jako inspirację konkurencyjną do sprawdzenia, nie jako gotowy "
        "temat publikacji, dopóki GSC i WordPress nie potwierdzą sensu biznesowego."
    )


def _ahrefs_content_intent(topic: str) -> str:
    return (
        f"konkurencyjny sygnał do sprawdzenia: `{topic}` wymaga potwierdzenia "
        "popytu w GSC, dopasowania WordPress i braku duplikacji przed planem treści"
    )


def _content_audience(topic: str) -> str:
    normalized = _normalize_text(topic)
    if "bdo" in normalized:
        return "Przedsiębiorca lub osoba operacyjna sprawdzająca obowiązki BDO i ryzyka formalne."
    if "zielony lad" in normalized or "esg" in normalized:
        return "Decydent lub specjalista środowiskowy szukający prostego wyjaśnienia regulacji."
    if "odpad" in normalized or "beczk" in normalized or "sorbent" in normalized:
        return (
            "Firma potrzebująca bezpiecznego procesu, produktu albo konsultacji w obszarze odpadów."
        )
    return "Marketer i ekspert Ekologus powinni doprecyzować odbiorcę przed pisaniem treści."


def _key_objections(topic: str) -> list[str]:
    normalized = _normalize_text(topic)
    objections = [
        "czy temat jest aktualny prawnie i zgodny z realną usługą Ekologus",
        "czy nie istnieje już strona, którą trzeba odświeżyć zamiast tworzyć nową",
    ]
    if "bdo" in normalized:
        objections.append(
            "czy użytkownik potrzebuje definicji, checklisty obowiązków czy konsultacji"
        )
    elif "zielony lad" in normalized or "esg" in normalized:
        objections.append("czy tekst ma wyjaśniać pojęcie, obowiązki firmy czy wpływ na procesy")
    else:
        objections.append("czy intencja jest edukacyjna, zakupowa czy konsultacyjna")
    return objections


def _h1_direction(topic: str, wordpress_match: bool) -> str:
    if wordpress_match:
        return (
            f"H1 powinien jasno odpowiadać na intencję `{topic}` i nie sugerować "
            "nowej, osobnej strony."
        )
    return f"H1 roboczy dla `{topic}` dopiero po potwierdzeniu kanonicznego URL i braku duplikatu."


def _seo_title_direction(topic: str, wordpress_match: bool) -> str:
    action = "odświeżany URL" if wordpress_match else "kanoniczny URL po sprawdzeniu"
    return (
        f"Title powinien zawierać intencję `{topic}`, jasno opisywać {action} "
        "i nie obiecywać pozycji, leadów ani kompletnej zgodności prawnej."
    )


def _meta_description_direction(topic: str, wordpress_match: bool) -> str:
    if wordpress_match:
        return (
            f"Meta description ma streścić odpowiedź na `{topic}` i kierować do "
            "konsultacji Ekologus bez obietnicy wyniku."
        )
    return (
        f"Meta description dla `{topic}` dopiero po potwierdzeniu inventory, "
        "kanonicznego URL i decyzji create/merge."
    )


def _h2_direction(topic: str) -> list[str]:
    normalized = _normalize_text(topic)
    sections = [
        f"krótka odpowiedź: czym jest `{topic}`",
        "co firma powinna sprawdzić przed decyzją",
        "kiedy warto porozmawiać z ekspertem Ekologus",
    ]
    if "bdo" in normalized:
        sections.insert(1, "obowiązki BDO przedsiębiorcy w praktyce")
        sections.insert(2, "najczęstsze błędy i ryzyka formalne")
    elif "zielony lad" in normalized or "esg" in normalized:
        sections.insert(1, "wpływ regulacji na przedsiębiorstwo")
        sections.insert(2, "co zmienia się w obowiązkach środowiskowych")
    elif "odpad" in normalized or "beczk" in normalized or "sorbent" in normalized:
        sections.insert(1, "bezpieczny proces magazynowania lub obsługi")
        sections.insert(2, "dobór rozwiązania do ryzyka i miejsca pracy")
    return sections


def _faq_direction(topic: str) -> list[str]:
    normalized = _normalize_text(topic)
    if "bdo" in normalized:
        return [
            "Co to jest BDO?",
            "Kto musi mieć wpis do BDO?",
            "Kiedy warto skonsultować obowiązki BDO z ekspertem?",
        ]
    if "zielony lad" in normalized or "esg" in normalized:
        return [
            "Co oznacza Zielony Ład dla firmy?",
            "Jakie obowiązki środowiskowe warto sprawdzić?",
            "Czy Ekologus może pomóc w ocenie wpływu regulacji?",
        ]
    return [
        f"Co oznacza `{topic}` dla firmy?",
        "Jakie informacje trzeba potwierdzić przed zapisem zmian?",
        "Kiedy warto skontaktować się z Ekologus?",
    ]


def _schema_direction(topic: str) -> str:
    return (
        f"FAQ schema można rozważyć tylko dla pytań faktycznie użytych w treści "
        f"o `{topic}` i po ręcznej kontroli zgodności odpowiedzi."
    )


def _cta_direction(topic: str) -> str:
    normalized = _normalize_text(topic)
    if "bdo" in normalized:
        return "CTA do konsultacji lub weryfikacji obowiązków BDO, bez obietnicy uniknięcia kar."
    if "zielony lad" in normalized or "esg" in normalized:
        return (
            "CTA do rozmowy o wpływie regulacji na firmę, "
            "bez obietnicy przychodu ani wzrostu leadów."
        )
    return "CTA do kontaktu z ekspertem Ekologus po ręcznym potwierdzeniu intencji tematu."


def _legal_review_notes(topic: str) -> list[str]:
    normalized = _normalize_text(topic)
    notes = [
        "potwierdź aktualność regulacji i zakres usługi z ekspertem Ekologus",
        "nie obiecuj uniknięcia kar, leadów, pozycji ani pełnej zgodności bez audytu",
    ]
    if "bdo" in normalized:
        notes.append("sprawdź, czy opis obowiązków BDO nie zastępuje indywidualnej konsultacji")
    if "zielony lad" in normalized or "esg" in normalized:
        notes.append("oddziel wyjaśnienie regulacji od interpretacji prawnej dla konkretnej firmy")
    return notes


def _brand_voice_notes(topic: str) -> list[str]:
    return [
        f"pisz konkretnie dla przedsiębiorcy szukającego odpowiedzi na `{topic}`",
        "unikaj clickbaitowych obietnic i generycznego poradnikowego tonu",
        "prowadź do konsultacji lub weryfikacji, gdy temat wymaga danych firmy",
    ]


def _publication_blockers() -> list[str]:
    return [
        "content_url_preflight_review",
        "canonical_review",
        "duplicate_or_cannibalization_check",
        "legal_factual_review",
        "human_confirm_before_wordpress_write",
    ]


def _internal_link_direction(topic: str) -> list[str]:
    normalized = _normalize_text(topic)
    links = ["strona główna Ekologus lub główna strona usługowa potwierdzona w WordPress"]
    if "bdo" in normalized:
        links.append("powiązane treści o obowiązkach przedsiębiorcy i gospodarce odpadami")
    if "zielony lad" in normalized or "esg" in normalized:
        links.append("powiązane treści o regulacjach środowiskowych i ESG")
    if "odpad" in normalized or "beczk" in normalized or "sorbent" in normalized:
        links.append("powiązane treści lub kategorie dotyczące magazynowania i obsługi odpadów")
    return links


def _gsc_source_facts(page: str, page_facts: list[MetricFact], wordpress_match: bool) -> list[str]:
    snapshot = _gsc_metric_snapshot(page_facts)
    return [
        f"Strona z GSC: {page}",
        f"Zapytania GSC: {snapshot['queries']}",
        f"Kliknięcia GSC: {snapshot['clicks']}",
        f"Wyświetlenia GSC: {snapshot['impressions']}",
        f"CTR GSC: {snapshot['ctr']}",
        f"Średnia pozycja GSC: {snapshot['average_position']}",
        (
            "WordPress: treść znaleziona w spisie"
            if wordpress_match
            else "WordPress: brak potwierdzonej treści w spisie"
        ),
    ]


def _gsc_missing_evidence(wordpress_match: bool) -> list[str]:
    missing = [
        "brak dowodu jakości leadów, wpływu na przychód i wzrostu pozycji",
        "brak zatwierdzonego szkicu zmian WordPress",
    ]
    if not wordpress_match:
        missing.insert(0, "brak potwierdzonego kanonicznego URL w spisie treści WordPress")
    return missing


def _ahrefs_source_facts(fact: MetricFact, topic: str) -> list[str]:
    dimensions = fact.dimensions
    facts = [
        f"ahrefs_topic={topic}",
        f"metric_name={fact.name}",
        f"metric_value={fact.value}",
    ]
    for key in ("gap_type", "keyword", "competitor_domain", "source_url"):
        value = dimensions.get(key)
        if value:
            facts.append(f"{key}={value}")
    referenced_public_url = dimensions.get("referenced_public_url")
    if referenced_public_url:
        facts.append(f"referenced_public_url={referenced_public_url}")
    return facts


def _brief_outline(topic: str, wordpress_match: bool) -> list[dict[str, str]]:
    action = "odświeżenia istniejącej strony" if wordpress_match else "sprawdzenia tematu"
    return [
        {
            "section": "intent",
            "instruction": f"Opisz intencję użytkownika dla `{topic}` i zakres {action}.",
        },
        {
            "section": "title_h1",
            "instruction": "Zaproponuj kierunek title/H1 bez obietnic pozycji ani leadów.",
        },
        {
            "section": "missing_sections",
            "instruction": "Wskaż sekcje do sprawdzenia lub dopisania na podstawie evidence.",
        },
        {
            "section": "cta",
            "instruction": (
                "Dopasuj CTA do usługi Ekologus, "
                "ale bez obietnicy przychodu ani wzrostu leadów."
            ),
        },
    ]


def _gsc_required_validation(wordpress_match: bool) -> list[str]:
    checks = [
        "gsc_query_page_check",
        "duplicate_or_cannibalization_check",
        "human_confirm_before_wordpress_write",
    ]
    if wordpress_match:
        return ["wordpress_existing_url_confirmed", *checks]
    return ["wordpress_inventory_check", *checks]


def _ahrefs_topic(fact: MetricFact) -> str | None:
    dimensions = fact.dimensions
    for key in ("keyword", "source_url", "competitor_domain"):
        value = dimensions.get(key)
        if value:
            return value
    referenced_public_url = dimensions.get("referenced_public_url")
    if referenced_public_url:
        return referenced_public_url
    return None


def _ahrefs_preview_score(fact: MetricFact, topic: str | None) -> int:
    if not topic:
        return 0
    haystack = _normalize_text(
        " ".join(
            value
            for value in [
                topic,
                fact.dimensions.get("keyword"),
                fact.dimensions.get("source_url"),
                fact.dimensions.get("referenced_public_url"),
                fact.dimensions.get("competitor_domain"),
            ]
            if value
        )
    )
    if any(term in haystack for term in AHREFS_OFF_TOPIC_TERMS):
        return 0
    score = 0
    if any(term in haystack for term in AHREFS_RELEVANCE_TERMS):
        score += 4
    if fact.dimensions.get("competitor_domain") in AHREFS_RELEVANT_COMPETITOR_DOMAINS:
        score += 2
    if fact.dimensions.get("keyword"):
        score += 2
    if fact.dimensions.get("gap_type") in {
        "content_gap",
        "organic_keyword_gap",
        "top_page_gap",
    }:
        score += 2
    return score


def _metric_numeric_sort_value(fact: MetricFact) -> float:
    if isinstance(fact.value, int | float):
        return float(fact.value)
    return 0.0


def _normalize_text(value: str) -> str:
    replacements = {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ź": "z",
        "ż": "z",
    }
    normalized = value.lower()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def _metric_sum(facts: list[MetricFact], metric_name: str) -> float:
    return sum(
        float(fact.value)
        for fact in facts
        if fact.name == metric_name and isinstance(fact.value, int | float)
    )


def _metric_sum_or_missing(facts: list[MetricFact], metric_name: str) -> int | float | str:
    value = _metric_sum(facts, metric_name)
    if value == 0 and not any(fact.name == metric_name for fact in facts):
        return "metryka GSC niepotwierdzona"
    return int(value) if value.is_integer() else value


def _first_metric_or_missing(facts: list[MetricFact], metric_name: str) -> int | float | str:
    for fact in facts:
        if fact.name == metric_name and isinstance(fact.value, int | float):
            value = float(fact.value)
            return int(value) if value.is_integer() else value
    return "metryka GSC niepotwierdzona"


def _normalized_path(value: str) -> str:
    parsed = urlparse(value)
    path = parsed.path if parsed.scheme or parsed.netloc else value
    normalized = "/" + path.strip("/")
    return "/" if normalized == "/" else normalized


def _short_path(value: str) -> str:
    parsed = urlparse(value)
    if parsed.netloc:
        return f"{parsed.netloc}{parsed.path}".rstrip("/") or parsed.netloc
    return value


def _url_host(value: str | None) -> str | None:
    if not value:
        return None
    host = urlparse(value).netloc.lower()
    return host or None


def _candidate_slug_for_page(value: str) -> str:
    path = _normalized_path(value)
    if path and path != "/":
        return _slug(path)
    parsed = urlparse(value)
    if parsed.netloc:
        return _slug(parsed.netloc)
    return _slug(value) or "homepage"


def _slug(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value.lower())[
        :96
    ].strip("_")
