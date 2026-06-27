from __future__ import annotations

MERCHANT_ISSUE_LABELS = {
    "availability_updated": "zmiana dostępności do sprawdzenia",
    "image too small for high resolution": "zdjęcie za małe dla wysokiej rozdzielczości",
    "image_too_small_for_high_resolution": "zdjęcie za małe dla wysokiej rozdzielczości",
    "landing_page_error": "błąd strony produktu",
    "missing_image": "brak zdjęcia produktu",
    "missing_potentially_required_attribute": "brak potencjalnie wymaganego atrybutu",
    "problem feedu": "problem feedu",
}

MERCHANT_ATTRIBUTE_LABELS = {
    "n:availability": "dostępność",
    "availability": "dostępność",
    "n:link": "link produktu",
    "link": "link produktu",
    "image_link": "link zdjęcia",
    "n:image_link": "link zdjęcia",
    "n:unit_pricing_measure": "miara ceny jednostkowej",
    "atrybut": "atrybut",
    "atrybut nieznany": "atrybut nieznany",
}

MERCHANT_REPORTING_CONTEXT_LABELS = {
    "ALL_CONTEXTS": "wszystkie konteksty",
    "DEMAND_GEN_ADS": "reklamy Demand Gen",
    "FREE_LISTINGS": "bezpłatne wyniki produktowe",
    "SHOPPING_ADS": "reklamy produktowe",
}

MERCHANT_SEVERITY_LABELS = {
    "DISAPPROVED": "odrzucone",
    "DEMOTED": "ograniczona widoczność",
    "NOT_IMPACTED": "bez wpływu",
    "UNKNOWN": "status nieznany",
}

MERCHANT_RESOLUTION_LABELS = {
    "MERCHANT_ACTION": "wymaga działania po stronie Merchant",
    "PENDING_PROCESSING": "czeka na przetworzenie",
}

MERCHANT_METRIC_LABELS = {
    "issue_product_count": "zgłoszenia problemów",
    "max_issue_product_count": "największa liczba zgłoszeń",
    "reported_issue_occurrences": "wystąpienia problemów",
    "reporting_contexts": "konteksty raportów",
}


def merchant_display_label(value: object) -> str:
    text = str(value or "").strip()
    if text in MERCHANT_ISSUE_LABELS:
        return MERCHANT_ISSUE_LABELS[text]
    if text in MERCHANT_ATTRIBUTE_LABELS:
        return MERCHANT_ATTRIBUTE_LABELS[text]
    if not text:
        return "wartość Merchant nieznana"
    return " ".join(text.replace("_", " ").split())


def merchant_reporting_context_label(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "wszystkie konteksty"
    return MERCHANT_REPORTING_CONTEXT_LABELS.get(text, merchant_display_label(text))


def merchant_severity_label(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "status nieznany"
    return MERCHANT_SEVERITY_LABELS.get(text, merchant_display_label(text))


def merchant_resolution_label(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "brak wymaganej ścieżki rozwiązania"
    return MERCHANT_RESOLUTION_LABELS.get(text, merchant_display_label(text))


def merchant_metric_snapshot_labels(metric_snapshot: dict[str, object]) -> dict[str, str]:
    return {
        key: MERCHANT_METRIC_LABELS.get(key, "metryka Merchant")
        for key in metric_snapshot
    }
