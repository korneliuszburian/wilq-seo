from __future__ import annotations

from collections.abc import Iterable

UNKNOWN_SOURCE_CONNECTOR_LABEL = "źródło danych do sprawdzenia"
UNKNOWN_REFRESH_STATUS_LABEL = "status odczytu do sprawdzenia"
UNKNOWN_ROUTE_LABEL = "widok do sprawdzenia"
UNKNOWN_MISSING_CONTRACT_LABEL = "brakujące dane do sprawdzenia"
UNKNOWN_BLOCKED_CLAIM_LABEL = "obietnica do sprawdzenia"
UNKNOWN_METRIC_FACT_LABEL = "metryka źródłowa"
UNKNOWN_ADS_CAMPAIGN_STATUS_LABEL = "status kampanii do sprawdzenia"
UNKNOWN_ADS_CHANNEL_TYPE_LABEL = "kanał kampanii do sprawdzenia"

ADS_CAMPAIGN_STATUS_LABELS: dict[str, str] = {
    "ENABLED": "aktywna",
    "PAUSED": "wstrzymana",
    "REMOVED": "usunięta",
    "UNKNOWN": "status nieznany",
    "UNSPECIFIED": "status nieokreślony",
}

ADS_CHANNEL_TYPE_LABELS: dict[str, str] = {
    "SEARCH": "sieć wyszukiwania",
    "PERFORMANCE_MAX": "Performance Max",
    "SHOPPING": "Zakupy Google",
    "DISPLAY": "sieć reklamowa",
    "DEMAND_GEN": "Demand Gen",
    "VIDEO": "wideo",
    "LOCAL": "lokalna",
    "SMART": "Smart",
    "UNKNOWN": "kanał nieznany",
    "UNSPECIFIED": "kanał nieokreślony",
}

COMMON_METRIC_FACT_LABELS: dict[str, str] = {
    "active_users": "aktywni użytkownicy",
    "average_position": "średnia pozycja",
    "budget_amount_micros": "budżet",
    "clicks": "kliknięcia",
    "content_object_count": "obiekty treści",
    "content_object_seen": "wykryty obiekt treści",
    "cost_micros": "koszt",
    "ctr": "współczynnik kliknięć",
    "domain_rating": "autorytet domeny",
    "ecommerce_purchases": "zakupy e-commerce",
    "engagement_rate": "współczynnik zaangażowania",
    "event_count": "zdarzenia",
    "impressions": "wyświetlenia",
    "issue_product_count": "zgłoszenia problemów",
    "key_events": "zdarzenia kluczowe",
    "pages_total": "strony",
    "posts_total": "wpisy",
    "purchase_revenue": "przychód z zakupów",
    "recommendation_available": "dostępne rekomendacje",
    "recommendation_campaign_count": "kampanie z rekomendacjami",
    "screen_page_views": "wyświetlenia stron",
    "sessions": "sesje",
}

CONNECTOR_METRIC_FACT_LABELS: dict[str, dict[str, str]] = {
    "ahrefs": {
        "ahrefs_backlink_gap_count": "luki linków",
        "ahrefs_competitor_page_count": "strony konkurencji",
        "ahrefs_content_gap_count": "luki treści",
        "ahrefs_organic_keyword_gap_count": "luki fraz organicznych",
        "blokady": "blokady",
        "decyzje": "decyzje",
        "dopasowania_wordpress": "dopasowania WordPress",
        "luki_ahrefs": "luki Ahrefs",
        "luki_linkow": "luki linków",
        "ocena_ahrefs": "ocena Ahrefs",
        "rekordy_ahrefs": "rekordy Ahrefs",
        "zapytania_url": "zapytania i URL-e",
    },
    "google_ads": {
        "account_currency_code": "waluta konta",
        "api_version": "wersja API",
        "budget_has_recommended_budget": "rekomendowany budżet dostępny",
        "clicks": "kliknięcia Ads",
        "conversion_value": "wartość konwersji",
        "conversions": "konwersje",
        "kampanie": "kampanie",
        "keyword_match_context_available": "kontekst dopasowań dostępny",
        "keyword_match_context_negative": "kontekst wykluczeń",
        "keyword_match_type": "typ dopasowania",
        "koszt": "koszt",
        "konwersje": "konwersje",
        "podglad_budzetu": "podgląd budżetu",
        "recommendation_impact_base_clicks": "kliknięcia bazowe rekomendacji",
        "recommendation_impact_base_cost_micros": "koszt bazowy rekomendacji",
        "recommendation_impact_base_impressions": "wyświetlenia bazowe rekomendacji",
        "rekomendacje": "rekomendacje",
        "row_count": "wiersze danych",
        "search_term_90d_clicks": "kliknięcia zapytania z 90 dni",
        "search_term_90d_conversion_value": "wartość konwersji zapytania z 90 dni",
        "search_term_90d_conversions": "konwersje zapytania z 90 dni",
        "search_term_90d_cost_micros": "koszt zapytania z 90 dni",
        "search_term_90d_impressions": "wyświetlenia zapytania z 90 dni",
        "search_term_clicks": "kliknięcia zapytania",
        "search_term_conversion_value": "wartość konwersji zapytania",
        "search_term_conversions": "konwersje zapytania",
        "search_term_cost_micros": "koszt zapytania",
        "search_term_impressions": "wyświetlenia zapytania",
        "segmenty": "segmenty",
        "wartosc_konwersji": "wartość konwersji",
        "wiersze_kosztu_pozyskania_celu": "wiersze kosztu pozyskania celu",
        "wiersze_zwrotu_z_reklam": "wiersze zwrotu z reklam",
        "wskazniki_do_sprawdzenia": "wskaźniki do sprawdzenia",
        "wykluczenia": "wykluczenia",
        "wyswietlenia": "wyświetlenia",
        "zapytania": "zapytania",
    },
    "google_analytics_4": {
        "brakujace_dane": "brakujące dane",
        "decyzje": "decyzje",
        "grupy_ruchu": "grupy ruchu",
        "jakosc_ruchu": "jakość ruchu",
        "pomiar": "pomiar",
    },
    "google_merchant_center": {
        "blokady": "blokady",
        "decyzje": "decyzje",
        "produkty": "produkty",
        "typy_problemow": "typy problemów",
        "zgloszenia": "zgłoszenia",
    },
    "google_search_console": {
        "clicks": "kliknięcia z GSC",
        "impressions": "wyświetlenia w GSC",
    },
    "localo": {
        "localo_active_place_count": "aktywne lokalizacje",
        "localo_avg_visibility_current": "średnia widoczność",
        "localo_competitor_change_count": "zmiany konkurencji",
        "localo_competitor_count": "konkurenci",
        "localo_favorite_competitor_count": "obserwowani konkurenci",
        "localo_gbp_actions_total": "działania w profilu firmy",
        "localo_gbp_impressions_total": "wyświetlenia profilu firmy",
        "localo_gbp_metric_point_count": "punkty metryk profilu firmy",
        "localo_reviews_count": "opinie",
        "localo_tracked_keyword_count": "monitorowane frazy",
    },
    "wordpress_ekologus": {
        "content_object_count": "obiekty treści ekologus.pl",
        "content_object_seen": "wykryta treść ekologus.pl",
    },
    "wordpress_sklep": {
        "content_object_seen": "wykryta treść sklepu",
    },
}

BLOCKED_CLAIM_LABELS: dict[str, str] = {
    "automatic_wordpress_write": "automatyczny zapis WordPress",
    "90-day negative keyword safety": "90-dniowe bezpieczeństwo wykluczeń",
    "90-dniowe bezpieczeństwo wykluczeń": "90-dniowe bezpieczeństwo wykluczeń",
    "automatyczne przyjęcie rekomendacji": "automatyczne przyjęcie rekomendacji",
    "automatyczna publikacja": "automatyczna publikacja",
    "automatyczna publikacja WordPress": "automatyczna publikacja WordPress",
    "automatyczna zmiana pliku produktowego": "automatyczna zmiana pliku produktowego",
    "budget change": "zmiana budżetu",
    "budget optimization": "optymalizacja budżetu",
    "skalowanie budżetu": "skalowanie budżetu",
    "campaign creation": "utworzenie kampanii",
    "propozycja naprawy pliku produktowego": "propozycja naprawy pliku produktowego",
    "dodanie wykluczających słów kluczowych": "dodanie wykluczających słów kluczowych",
    "zapis zmian kampanii": "zmiana kampanii",
    "causal impact": "przyczynowy wpływ zmian",
    "client-ready report": "raport gotowy dla klienta",
    "CPA": "werdykt kosztu pozyskania celu",
    "ocena kosztu pozyskania celu": "werdykt kosztu pozyskania celu",
    "werdykt kosztu pozyskania celu": "werdykt kosztu pozyskania celu",
    "ocena docelowego kosztu pozyskania celu": "werdykt docelowego kosztu pozyskania celu",
    "ocena docelowego zwrotu z reklam": "werdykt docelowego zwrotu z reklam",
    "CPC": "koszt kliknięcia",
    "CTR": "współczynnik kliknięć",
    "conversion_rate": "werdykt współczynnika konwersji",
    "spadek konwersji": "werdykt spadku konwersji",
    "werdykt spadku konwersji": "werdykt spadku konwersji",
    "współczynnik konwersji": "werdykt współczynnika konwersji",
    "wdrożona konfiguracja konwersji": "wdrożona konfiguracja konwersji",
    "Demand Gen launch ready": "gotowość uruchomienia Demand Gen",
    "zapis zmian GBP": "zapis zmian w profilu firmy",
    "zapis zmian w profilu firmy": "zapis zmian w profilu firmy",
    "lead quality": "jakość leadów",
    "jakość leadów": "jakość leadów",
    "link acquisition impact": "wpływ pozyskanych linków",
    "lead_uplift": "wzrost liczby leadów",
    "monthly performance verdict": "miesięczny werdykt skuteczności",
    "negative keyword addition": "dodanie wykluczających słów kluczowych",
    "opłacalność": "opłacalność",
    "ocena opłacalności": "opłacalność",
    "recommendation applied": "wdrożona rekomendacja",
    "recommendation write": "zapis rekomendacji",
    "przychód": "twierdzenie o przychodzie",
    "ranking guarantee": "gwarancja pozycji",
    "ranking_guarantee": "gwarancja pozycji",
    "revenue_impact": "twierdzenie o wpływie na przychód",
    "roas": "werdykt zwrotu z reklam",
    "twierdzenie o przychodzie": "twierdzenie o przychodzie",
    "marnowanie budżetu na zapytaniach": "werdykt marnowania budżetu na zapytaniach",
    "werdykt marnowania budżetu na zapytaniach": "werdykt marnowania budżetu na zapytaniach",
    "ocena atrybucji": "ocena atrybucji",
    "ocena marży": "ocena marży",
    "spend": "wydatki reklamowe",
    "wydatki reklamowe": "wydatki reklamowe",
    "zapytania z reklam": "zapytania z reklam",
    "naprawiony pomiar": "twierdzenie o naprawionym pomiarze",
    "twierdzenie o naprawionym pomiarze": "twierdzenie o naprawionym pomiarze",
    "zmarnowany budżet": "zmarnowany budżet",
    "wpływ na przychód": "twierdzenie o wpływie na przychód",
    "wpływ na revenue": "twierdzenie o wpływie na przychód",
    "twierdzenie o wpływie na przychód": "twierdzenie o wpływie na przychód",
    "wpływ zmian": "wpływ zmian",
    "wzrost konwersji": "obietnica wzrostu konwersji",
    "wzrost liczby leadów": "wzrost liczby leadów",
    "wzrost ruchu": "wzrost ruchu",
    "gwarancja pozycji": "gwarancja pozycji",
    "obietnica wzrostu konwersji": "obietnica wzrostu konwersji",
    "propozycje wykluczeń": "propozycje wykluczeń",
    "utrata konwersji": "utrata konwersji",
    "zapis w GA4": "zapis w GA4",
    "zapis wykluczeń": "zapis wykluczeń",
    "zwrot z reklam": "werdykt zwrotu z reklam",
    "werdykt zwrotu z reklam": "werdykt zwrotu z reklam",
    "wordpress_publish": "publikacja WordPress",
    "wordpress_write": "zapis WordPress",
    "ocena zmarnowanego budżetu": "zmarnowany budżet",
    "ponowne zatwierdzenie produktu": "ponowne zatwierdzenie produktu",
    "odzyskany przychód": "odzyskany przychód",
    "lokalne rankingi": "lokalne rankingi",
    "wyniki profilu firmy w Google": "wyniki profilu firmy w Google",
    "widoczność konkurencji": "widoczność konkurencji",
    "tempo nowych opinii": "tempo nowych opinii",
    "ukończone zadanie lokalne": "ukończone zadanie lokalne",
    "poprawa widoczności lokalnej": "poprawa widoczności lokalnej",
}


def blocked_claim_label(claim: str) -> str:
    if claim in BLOCKED_CLAIM_LABELS:
        return BLOCKED_CLAIM_LABELS[claim]
    if _looks_like_raw_operator_value(claim):
        return UNKNOWN_BLOCKED_CLAIM_LABEL
    return claim


def _looks_like_raw_operator_value(value: object) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    if "_" in text or ":" in text:
        return True
    if text.upper() == text and any(character.isalpha() for character in text):
        return True
    raw_terms = {
        "apply",
        "auto",
        "automatic",
        "budget",
        "campaign",
        "claim",
        "conversion",
        "forecast",
        "guarantee",
        "impact",
        "keyword",
        "payload",
        "publish",
        "ranking",
        "recommendation",
        "revenue",
        "uplift",
        "write",
    }
    normalized = text.lower().replace("-", " ")
    return any(term in normalized.split() for term in raw_terms)


def blocked_claim_labels(claims: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for claim in claims:
        label = blocked_claim_label(claim)
        if label and label not in seen:
            seen.add(label)
            values.append(label)
    return values


def metric_fact_label(name: object, source_connector: object | None = None) -> str:
    metric_name = str(name or "").strip()
    connector_id = str(source_connector or "").strip()
    if not metric_name:
        return UNKNOWN_METRIC_FACT_LABEL
    connector_labels = CONNECTOR_METRIC_FACT_LABELS.get(connector_id, {})
    if metric_name in connector_labels:
        return connector_labels[metric_name]
    if metric_name in COMMON_METRIC_FACT_LABELS:
        return COMMON_METRIC_FACT_LABELS[metric_name]
    if _looks_like_raw_operator_value(metric_name):
        return UNKNOWN_METRIC_FACT_LABEL
    return metric_name


def ads_campaign_status_label(status: object | None) -> str:
    value = str(status or "").strip().upper()
    if not value:
        return "status: brak"
    return ADS_CAMPAIGN_STATUS_LABELS.get(value, UNKNOWN_ADS_CAMPAIGN_STATUS_LABEL)


def ads_channel_type_label(channel_type: object | None) -> str:
    value = str(channel_type or "").strip().upper()
    if not value:
        return "kanał: brak"
    return ADS_CHANNEL_TYPE_LABELS.get(value, UNKNOWN_ADS_CHANNEL_TYPE_LABEL)


def blocked_claim_summary_label(claims: Iterable[str]) -> str:
    labels = blocked_claim_labels(claims)
    if not labels:
        return "brak zakazanych obietnic"
    return ", ".join(labels)


def source_connector_label(connector_id: str) -> str:
    labels = {
        "ahrefs": "Ahrefs",
        "google_ads": "Google Ads",
        "google_analytics_4": "GA4",
        "google_merchant_center": "Merchant Center",
        "google_search_console": "Google Search Console",
        "google_sheets": "Google Sheets",
        "linkedin": "LinkedIn",
        "localo": "Localo",
        "wordpress_ekologus": "WordPress ekologus.pl",
        "wordpress_sklep": "WordPress sklep.ekologus.pl",
    }
    return labels.get(connector_id, UNKNOWN_SOURCE_CONNECTOR_LABEL)


def source_connector_labels(connector_ids: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for connector_id in connector_ids:
        label = source_connector_label(connector_id)
        if label not in seen:
            seen.add(label)
            values.append(label)
    return values


def source_connector_summary_label(connector_ids: Iterable[str]) -> str:
    labels = source_connector_labels(connector_ids)
    if not labels:
        return "brak źródeł danych"
    return ", ".join(labels)


def evidence_count_label(evidence_ids: Iterable[str]) -> str:
    count = len(list(evidence_ids))
    if count == 0:
        return "brak dowodów źródłowych"
    if count == 1:
        return "1 dowód źródłowy"
    if 2 <= count <= 4:
        return f"{count} dowody źródłowe"
    return f"{count} dowodów źródłowych"


def action_count_label(action_ids: Iterable[str]) -> str:
    count = len(list(action_ids))
    if count == 0:
        return "brak akcji do sprawdzenia"
    if count == 1:
        return "1 akcja do sprawdzenia"
    if 2 <= count <= 4:
        return f"{count} akcje do sprawdzenia"
    return f"{count} akcji do sprawdzenia"


def source_contract_count_label(contract_ids: Iterable[str]) -> str:
    count = len(list(contract_ids))
    if count == 0:
        return "brak warunków źródłowych"
    if count == 1:
        return "1 warunek źródłowy"
    if 2 <= count <= 4:
        return f"{count} warunki źródłowe"
    return f"{count} warunków źródłowych"


def policy_count_label(policy_ids: Iterable[str]) -> str:
    count = len(list(policy_ids))
    if count == 0:
        return "brak polityk"
    if count == 1:
        return "1 polityka"
    if 2 <= count <= 4:
        return f"{count} polityki"
    return f"{count} polityk"


def required_validation_count_label(required_validation: Iterable[str]) -> str:
    count = len(list(required_validation))
    if count == 0:
        return "brak wymaganego sprawdzenia"
    if count == 1:
        return "1 wymagane sprawdzenie"
    if 2 <= count <= 4:
        return f"{count} wymagane sprawdzenia"
    return f"{count} wymaganych sprawdzeń"


def credential_field_count_label(fields: Iterable[str]) -> str:
    count = len(list(fields))
    if count == 0:
        return "brak brakujących pól dostępu"
    if count == 1:
        return "1 pole"
    if 2 <= count <= 4:
        return f"{count} pola"
    return f"{count} pól"


def credential_source_count_label(sources: Iterable[str]) -> str:
    count = len(list(sources))
    if count == 0:
        return "brak źródeł konfiguracji"
    if count == 1:
        return "1 źródło"
    if 2 <= count <= 4:
        return f"{count} źródła"
    return f"{count} źródeł"


def reported_issue_occurrence_count_label(count: int) -> str:
    absolute = abs(count)
    last_two = absolute % 100
    last = absolute % 10
    if absolute == 0:
        return "brak zgłoszeń problemu"
    if absolute == 1:
        return "1 zgłoszenie problemu"
    if last >= 2 and last <= 4 and not (last_two >= 12 and last_two <= 14):
        return f"{count} zgłoszenia problemu"
    return f"{count} zgłoszeń problemu"


def mapped_action_type_count_label(action_types: Iterable[str]) -> str:
    count = len(list(action_types))
    if count == 0:
        return "brak typów akcji do sprawdzenia"
    if count == 1:
        return "1 typ akcji do sprawdzenia"
    if 2 <= count <= 4:
        return f"{count} typy akcji do sprawdzenia"
    return f"{count} typów akcji do sprawdzenia"


def knowledge_reference_count_label(
    knowledge_card_ids: Iterable[str] = (),
    playbook_ids: Iterable[str] = (),
    expert_rule_ids: Iterable[str] = (),
) -> str:
    count = len(list(knowledge_card_ids)) + len(list(playbook_ids)) + len(list(expert_rule_ids))
    if count == 0:
        return "brak użytej wiedzy"
    if count == 1:
        return "1 element wiedzy użyty w decyzji"
    if 2 <= count <= 4:
        return f"{count} elementy wiedzy użyte w decyzji"
    return f"{count} elementów wiedzy użytych w decyzji"


def required_evidence_count_label(required_evidence: Iterable[str]) -> str:
    count = len(list(required_evidence))
    if count == 0:
        return "brak wymaganych dowodów"
    if count == 1:
        return "1 wymagany dowód"
    if 2 <= count <= 4:
        return f"{count} wymagane dowody"
    return f"{count} wymaganych dowodów"


def source_lineage_count_label(source_lineage: Iterable[str]) -> str:
    count = len(list(source_lineage))
    if count == 0:
        return "brak śladów źródłowych"
    if count == 1:
        return "1 ślad źródłowy"
    if 2 <= count <= 4:
        return f"{count} ślady źródłowe"
    return f"{count} śladów źródłowych"


def workflow_error_count_label(errors: Iterable[str]) -> str:
    count = len(list(errors))
    if count == 0:
        return "brak błędów procesu"
    if count == 1:
        return "1 błąd procesu"
    if 2 <= count <= 4:
        return f"{count} błędy procesu"
    return f"{count} błędów procesu"


def missing_contract_label(contract: object) -> str:
    labels = {
        "monthly_comparison_window": "okno porównania miesiąca",
        "client_report_payload": "zakres raportu dla klienta",
        "change_history_summary": "podsumowanie historii zmian",
        "pre_post_change_window": "okno przed i po zmianie",
        "human_strategy_review": "sprawdzenie strategii przez człowieka",
        "profit_margin_or_business_goal": "cel biznesowy albo marża",
        "pre_post_change_impact": "wpływ zmian przed i po",
        "operator_change_notes": "notatki operatora o zmianach",
        "ngram_cluster_contract": "grupowanie fragmentów wyszukiwanych haseł",
        "90_day_cross_check_by_ngram": "90-dniowe porównanie fragmentów wyszukiwań",
        "forecast_or_audience_size": "prognoza albo wielkość grupy odbiorców",
        "targeting_apply_preview": "podgląd zmiany targetowania",
        "creative_asset_readiness": "gotowość kreacji",
        "audience_readiness": "gotowość odbiorców",
        "competitor_gap_matrix": "macierz luk względem konkurencji",
        "backlink_gap_rows": "rekordy luk linków",
        "local_ranking_rows": "lokalne pozycje",
        "gbp_performance_rows": "wyniki profilu firmy",
        "review_rows": "opinie",
        "editorial_calendar_payload": "zakres kalendarza treści",
        "owner_due_date_review": "właściciel i termin sprawdzenia",
        "social_publish_permission": "uprawnienie do publikacji social",
        "post_payload_preview": "podgląd posta przed publikacją",
    }
    return labels.get(str(contract), UNKNOWN_MISSING_CONTRACT_LABEL)


def missing_contract_labels(contracts: Iterable[object]) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for contract in contracts:
        label = missing_contract_label(contract)
        if label and label not in seen:
            seen.add(label)
            values.append(label)
    return values


def missing_contract_count_label(contracts: Iterable[object]) -> str:
    count = len(missing_contract_labels(contracts))
    if count == 0:
        return "dane kompletne"
    if count == 1:
        return "1 brakujący zakres danych"
    if 2 <= count <= 4:
        return f"{count} brakujące zakresy danych"
    return f"{count} brakujących zakresów danych"


def blocked_claim_count_label(claims: Iterable[str]) -> str:
    count = len(blocked_claim_labels(claims))
    if count == 0:
        return "brak zablokowanych obietnic"
    if count == 1:
        return "1 zablokowana obietnica"
    if 2 <= count <= 4:
        return f"{count} zablokowane obietnice"
    return f"{count} zablokowanych obietnic"


def blocker_count_label(blockers: Iterable[object]) -> str:
    count = len([blocker for blocker in blockers if str(blocker).strip()])
    if count == 0:
        return "brak blokad"
    if count == 1:
        return "1 blokada"
    if 2 <= count <= 4:
        return f"{count} blokady"
    return f"{count} blokad"


def impact_comparison_summary_label(summary: str | None) -> str | None:
    if not summary:
        return summary
    parts: list[str] = []
    for part in summary.split(". "):
        parts.append(_impact_comparison_summary_part_label(part.strip()))
    return ". ".join(parts)


def _impact_comparison_summary_part_label(part: str) -> str:
    prefix_labels = {
        "Okno przed zmianą": "Porównanie sprzed zmiany",
        "Okno po zmianie": "Porównanie po zmianie",
    }
    for prefix, label in prefix_labels.items():
        if part.startswith(prefix):
            return f"{label}{part[len(prefix) :]}"
    return part


def freshness_state_label(state: str | None) -> str:
    labels = {
        "fresh": "świeże dane",
        "missing": "brak danych",
        "stale": "dane wymagają odświeżenia",
        "unknown": "świeżość niepotwierdzona",
    }
    return labels.get(state or "unknown", "świeżość niepotwierdzona")


def evidence_source_type_label(source_type: str) -> str:
    labels = {
        "connector_refresh": "odczyt źródła danych",
        "connector_refresh_run": "odczyt źródła danych",
        "connector_status": "status źródła danych",
        "metric_fact_store": "metryka z odczytu",
    }
    return labels.get(source_type, "dowód źródłowy")


def connector_refresh_status_label(status: object) -> str:
    value = getattr(status, "value", status)
    labels = {
        "blocked": "odczyt zablokowany",
        "completed": "odczyt zakończony",
        "failed": "odczyt nieudany",
        "missing_credentials": "brak dostępu",
        "pending": "odczyt w kolejce",
        "running": "odczyt trwa",
        "skipped": "odczyt pominięty",
    }
    return labels.get(str(value or ""), UNKNOWN_REFRESH_STATUS_LABEL)


def route_operator_label(route: str | None) -> str:
    labels = {
        "/actions": "Akcje do sprawdzenia",
        "/ads-doctor": "Google Ads",
        "/ads-doctor/custom-segments": "Segmenty Google Ads",
        "/ads-doctor/demand-gen": "Demand Gen",
        "/ahrefs": "Ahrefs",
        "/codex-runs": "Uruchomienia Codexa",
        "/command-center": "Centrum pracy",
        "/content-inventory": "Spis treści",
        "/content-planner": "Treści",
        "/ga4": "GA4",
        "/google-sheets": "Google Sheets",
        "/knowledge": "Baza wiedzy",
        "/localo": "Localo",
        "/merchant": "Merchant Center",
        "/opportunities": "Szanse",
        "/security": "Bezpieczeństwo",
        "/settings": "Ustawienia",
        "/social-publisher": "Social",
    }
    return labels.get(str(route or ""), UNKNOWN_ROUTE_LABEL)


def route_cta_label(route: str | None) -> str:
    return f"Otwórz {route_operator_label(route)}"


def opportunity_domain_label(domain: object) -> str:
    value = getattr(domain, "value", domain)
    labels = {
        "ahrefs": "SEO / Ahrefs",
        "codex": "Codex",
        "content": "Treści",
        "ga4": "GA4",
        "google_ads": "Google Ads",
        "google_sheets": "Google Sheets",
        "gsc_seo": "SEO / Google Search Console",
        "knowledge": "Wiedza",
        "localo": "Localo",
        "merchant": "Merchant Center",
        "social": "Social",
        "wordpress": "WordPress",
    }
    return labels.get(str(value), "obszar do sprawdzenia")
