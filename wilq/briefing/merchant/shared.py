from __future__ import annotations

from datetime import datetime

from wilq.briefing.merchant_labels import merchant_metric_fact_label
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.schemas import (
    ActionObject,
    ConnectorRefreshRun,
    MetricFact,
)

MERCHANT_CONNECTOR_ID = "google_merchant_center"


GOOGLE_ADS_CONNECTOR_ID = "google_ads"


GA4_CONNECTOR_ID = "google_analytics_4"


MERCHANT_METRIC_FACT_LIMIT = 2000


MERCHANT_PRODUCT_PERFORMANCE_REQUIRED_READ_CONTRACTS = [
    "merchant_product_id_join_key",
    "google_ads_shopping_product_performance",
    "ga4_item_product_performance",
]


MERCHANT_PRODUCT_PERFORMANCE_BLOCKED_CLAIMS = [
    "zwrot z reklam na poziomie produktu",
    "odzyskany przychód produktu",
    "efekt naprawy produktu",
    "skalowanie produktu w reklamach produktowych i Performance Max",
    "ponowne zatwierdzenie produktu",
    "zapis do pliku produktowego",
]


MERCHANT_KNOWLEDGE_CARD_IDS = [
    "card_merchant_feed_optimization_playbook",
    "card_google_ads_pmax_playbook",
]


MERCHANT_EXPERT_RULE_IDS = [
    "merchant_feed_rules_v1",
    "merchant_product_diagnostics_v1",
    "merchant_platform_traps_v1",
]


MERCHANT_PRODUCT_STATE_REVIEW_PREVIEW_CONTRACT = "merchant_product_state_review_preview_v1"


MERCHANT_SUPPLEMENTAL_FEED_REVIEW_PREVIEW_CONTRACT = "merchant_supplemental_feed_review_preview_v1"


MERCHANT_PRICE_IMPACT_PREVIEW_CONTRACT = "merchant_price_impact_readiness_preview_v1"


MERCHANT_PRICE_IMPACT_REQUIRED_READ_CONTRACTS = [
    "google_ads_shopping_product_current_price",
    "google_ads_shopping_product_price_history",
    "merchant_price_change_event_or_snapshot",
    "google_ads_or_ga4_product_performance_window",
]


MERCHANT_REQUIRED_VALIDATION_LABELS = {
    "confirm_before_after_performance_window": "potwierdź okno porównania sprzed i po zmianie",
    "confirm_price_change_date": "potwierdź datę zmiany ceny",
    "confirm_price_snapshot_history": "potwierdź historię ceny",
    "confirm_source_of_truth_values": "potwierdź wartości ze źródła prawdy",
    "exclude_stock_or_approval_confounders": "wyklucz wpływ stanu magazynu lub zatwierdzenia",
    "human_confirm_before_apply": "człowiek potwierdza przed zapisem",
    "human_review_before_action": "człowiek sprawdza przed działaniem",
    "mutation_audit_required": "wymagany audyt zapisu",
    "prepare_feed_fix_preview": "przygotuj podgląd zmian pliku produktowego",
    "prepare_supplemental_feed_draft_preview": "przygotuj podgląd uzupełnienia pliku produktowego",
    "prepare_supplemental_feed_preview_before_any_mutation": (
        "przygotuj podgląd uzupełnienia pliku produktowego przed zapisem"
    ),
    "review_ads_product_status": "sprawdź status produktu z Google Ads",
    "review_issue_type_and_attribute": "sprawdź typ problemu i atrybut",
    "review_merchant_issue_context": "sprawdź kontekst problemu Merchant",
    "review_product_identity_mapping": "sprawdź powiązanie produktu",
    "review_reporting_context": "sprawdź kontekst raportowania",
    "require_human_confirm_before_apply": "człowiek potwierdza przed zapisem",
    "validate_change_values": "sprawdź wartości przed zapisem",
}


MERCHANT_DECISION_TYPE_LABELS = {
    "review_issue_cluster": "przegląd problemu pliku produktowego",
    "review_feed_status": "przegląd statusu pliku produktowego",
    "review_product_state_mapping": "powiązanie produktu z Ads",
    "review_price_impact_readiness": "sprawdzenie wpływu ceny",
    "block_until_vendor_read": "blokada do czasu odczytu Merchant",
}


MERCHANT_SECTION_LABELS = {
    "merchant_feed_health": "Metryki produktów",
    "merchant_issue_queue": "Kolejka problemów pliku produktowego",
    "merchant_action_safety": "Bezpieczeństwo akcji",
}


PRODUCT_JOIN_DIMENSION_KEYS = [
    "product_id",
    "item_id",
    "offer_id",
    "merchant_product_id",
    "shopping_product_id",
    "product_item_id",
    "sku",
    "item_sku",
]


GOOGLE_ADS_PRODUCT_STATE_FACT_NAMES = {
    "shopping_product_state_available",
    "shopping_product_status",
    "shopping_product_availability",
    "shopping_product_price_micros",
}


MERCHANT_HEALTH_METRIC_NAMES = {
    "total_products",
    "active_products",
    "disapproved_products",
    "expiring_products",
    "item_level_issue_count",
    "merchant_action_issue_count",
}


MERCHANT_STALE_AFTER_HOURS = 48


DEFAULT_MERCHANT_DIAGNOSTICS_CACHE_SECONDS = 15.0


def _enum_value(value: object) -> str:
    enum_value = getattr(value, "value", value)
    return str(enum_value)


def _latest_connector_refresh(connector_id: str) -> ConnectorRefreshRun | None:
    runs = list_connector_refresh_runs(connector_id=connector_id)
    return runs[0] if runs else None


def _int_metric_value(facts: list[MetricFact], names: list[str]) -> int | None:
    value = _numeric_metric_value(facts, names)
    if value is None:
        return None
    return int(value)


def _float_metric_value(facts: list[MetricFact], names: list[str]) -> float | None:
    value = _numeric_metric_value(facts, names)
    if value is None:
        return None
    return float(value)


def _numeric_metric_value(
    facts: list[MetricFact],
    names: list[str],
) -> int | float | None:
    accepted_names = set(names)
    for fact in facts:
        if fact.name in accepted_names and isinstance(fact.value, int | float):
            return fact.value
    return None


def _metric_fact_by_name(
    facts: list[MetricFact],
    names: list[str],
) -> MetricFact | None:
    accepted_names = set(names)
    for fact in facts:
        if fact.name in accepted_names:
            return fact
    return None


def _int_previous_metric_value(fact: MetricFact | None) -> int | None:
    if fact is None or not isinstance(fact.previous_value, int | float):
        return None
    return int(fact.previous_value)


def _int_delta_metric_value(fact: MetricFact | None) -> int | None:
    if fact is None or not isinstance(fact.delta, int | float):
        return None
    return int(fact.delta)


def _delta_percent_metric_value(fact: MetricFact | None) -> float | None:
    if fact is None or not isinstance(fact.delta_percent, int | float):
        return None
    return float(fact.delta_percent)


def _iso_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _text_metric_value(facts: list[MetricFact], names: list[str]) -> str | None:
    accepted_names = set(names)
    for fact in facts:
        if fact.name in accepted_names and isinstance(fact.value, str):
            value = fact.value.strip()
            if value:
                return value
    return None


def _dimension_value(facts: list[MetricFact], keys: list[str]) -> str | None:
    for fact in facts:
        for key in keys:
            value = fact.dimensions.get(key)
            if value and value.strip():
                return value.strip()
    return None


def _merchant_action_ids(actions: list[ActionObject]) -> list[str]:
    return [action.id for action in actions if action.connector == MERCHANT_CONNECTOR_ID]


def _stable_slug(value: str) -> str:
    lowered = value.lower()
    chars = [char if char.isalnum() else "_" for char in lowered]
    return "_".join("".join(chars).split("_")) or "unknown"


def _facts_by_names(facts: list[MetricFact], names: set[str]) -> list[MetricFact]:
    return [fact for fact in facts if fact.name in names]


def _numeric_metric(facts: list[MetricFact], name: str) -> int | None:
    for fact in facts:
        if fact.name == name and isinstance(fact.value, int | float):
            return int(fact.value)
    return None


def _metric_sentence(facts: list[MetricFact]) -> str:
    samples = ", ".join(
        f"{merchant_metric_fact_label(fact.name)}: {fact.value}" for fact in facts[:6]
    )
    return f"Najważniejsze metryki Merchant: {samples}."


def _pl_count(count: int, one: str, few: str, many: str) -> str:
    absolute = abs(count)
    last_digit = absolute % 10
    last_two_digits = absolute % 100
    if absolute == 1:
        form = one
    elif 2 <= last_digit <= 4 and not 12 <= last_two_digits <= 14:
        form = few
    else:
        form = many
    return f"{count} {form}"
