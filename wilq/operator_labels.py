from __future__ import annotations

from collections.abc import Iterable


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
    }
    return labels.get(connector_id, connector_id)


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
    return labels.get(str(value), str(value))
