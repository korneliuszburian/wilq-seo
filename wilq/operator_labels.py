from __future__ import annotations

from collections.abc import Iterable

UNKNOWN_SOURCE_CONNECTOR_LABEL = "źródło danych do sprawdzenia"
UNKNOWN_REFRESH_STATUS_LABEL = "status odczytu do sprawdzenia"
UNKNOWN_ROUTE_LABEL = "widok do sprawdzenia"

BLOCKED_CLAIM_LABELS: dict[str, str] = {
    "90-day negative keyword safety": "90-dniowe bezpieczeństwo wykluczeń",
    "90-dniowe bezpieczeństwo wykluczeń": "90-dniowe bezpieczeństwo wykluczeń",
    "automatyczne przyjęcie rekomendacji": "automatyczne przyjęcie rekomendacji",
    "automatyczna publikacja": "automatyczna publikacja",
    "automatyczna publikacja WordPress": "automatyczna publikacja WordPress",
    "automatyczna zmiana feedu": "automatyczna zmiana feedu",
    "budget change": "zmiana budżetu",
    "budget optimization": "optymalizacja budżetu",
    "skalowanie budżetu": "skalowanie budżetu",
    "campaign creation": "utworzenie kampanii",
    "feed fix candidate": "propozycja naprawy feedu",
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
    "monthly performance verdict": "miesięczny werdykt skuteczności",
    "negative keyword addition": "dodanie wykluczających słów kluczowych",
    "opłacalność": "opłacalność",
    "ocena opłacalności": "opłacalność",
    "recommendation applied": "wdrożona rekomendacja",
    "recommendation write": "zapis rekomendacji",
    "przychód": "twierdzenie o przychodzie",
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
    "obietnica wzrostu konwersji": "obietnica wzrostu konwersji",
    "propozycje wykluczeń": "propozycje wykluczeń",
    "utrata konwersji": "utrata konwersji",
    "zapis w GA4": "zapis w GA4",
    "zapis wykluczeń": "zapis wykluczeń",
    "zwrot z reklam": "werdykt zwrotu z reklam",
    "werdykt zwrotu z reklam": "werdykt zwrotu z reklam",
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
    return BLOCKED_CLAIM_LABELS.get(claim, claim)


def blocked_claim_labels(claims: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for claim in claims:
        label = blocked_claim_label(claim)
        if label and label not in seen:
            seen.add(label)
            values.append(label)
    return values


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
