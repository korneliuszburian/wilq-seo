from __future__ import annotations

from typing import Any

from wilq.actions.ga4.tracking_quality import (
    GA4_TRACKING_QUALITY_ACTION_TYPE,
    validate_ga4_tracking_quality_payload,
)
from wilq.actions.google_ads.business_context import (
    ADS_BUSINESS_CONTEXT_ACTION_TYPE,
    ADS_STRATEGY_REVIEW_ACTION_TYPE,
    ADS_TARGET_CONFIRMATION_ACTION_TYPE,
    validate_ads_business_context_payload,
    validate_ads_strategy_review_payload,
    validate_ads_target_confirmation_payload,
)
from wilq.actions.google_ads.campaign_review import validate_campaign_review_payload
from wilq.actions.google_ads.change_history import validate_change_history_impact_payload
from wilq.actions.google_ads.custom_segments import validate_custom_segment_payload
from wilq.actions.google_ads.demand_gen import (
    DEMAND_GEN_READINESS_REVIEW_ACTION_TYPE,
    validate_demand_gen_readiness_review_payload,
)
from wilq.actions.google_ads.keyword_planner import (
    KEYWORD_PLANNER_ACCESS_ACTION_TYPE,
    validate_keyword_planner_access_payload,
)
from wilq.actions.google_ads.negative_keywords import validate_negative_keyword_payload
from wilq.actions.google_ads.recommendations import validate_recommendation_review_payload
from wilq.actions.google_ads.search_term_ngrams import validate_search_term_ngram_payload
from wilq.actions.localo.visibility import (
    LOCALO_VISIBILITY_REVIEW_ACTION_TYPE,
    validate_localo_visibility_review_payload,
)
from wilq.actions.validation_copy import missing, wrong
from wilq.connectors.registry import get_connector_status

INTERNAL_ACTION_TYPES = {
    "configure_connector",
    "repair_google_ads_oauth",
    ADS_BUSINESS_CONTEXT_ACTION_TYPE,
    ADS_TARGET_CONFIRMATION_ACTION_TYPE,
    ADS_STRATEGY_REVIEW_ACTION_TYPE,
    KEYWORD_PLANNER_ACCESS_ACTION_TYPE,
}


def validate_action_payload(connector_id: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    action_type = payload.get("action_type")
    payload_connector = payload.get("connector")
    connector = get_connector_status(connector_id)

    if not isinstance(action_type, str) or not action_type.strip():
        errors.append(missing("Akcja", "typu działania"))
        return errors

    if payload_connector is not None and payload_connector != connector_id:
        errors.append(wrong("Akcja", "źródło danych nie zgadza się z akcją"))

    if action_type in INTERNAL_ACTION_TYPES:
        required_env = payload.get("required_env")
        if action_type == "configure_connector" and not isinstance(required_env, list):
            errors.append(missing("Konfiguracja źródła danych", "listy wymaganych ustawień"))
        if action_type == "repair_google_ads_oauth":
            if connector_id != "google_ads":
                errors.append(wrong("Naprawa dostępu Google Ads", "dotyczy tylko Google Ads"))
            if payload.get("oauth_scope") != "https://www.googleapis.com/auth/adwords":
                errors.append(missing("Naprawa dostępu Google Ads", "zakresu dostępu Google Ads"))
            if not isinstance(payload.get("oauth_client_json_path"), str):
                errors.append(
                    missing("Naprawa dostępu Google Ads", "lokalnej ścieżki klienta OAuth")
                )
            if not isinstance(payload.get("helper_commands"), list):
                errors.append(missing("Naprawa dostępu Google Ads", "instrukcji pomocniczych"))
        if action_type == ADS_BUSINESS_CONTEXT_ACTION_TYPE:
            if connector_id != "google_ads":
                errors.append(wrong("Kontekst biznesowy Ads", "dotyczy tylko Google Ads"))
            errors.extend(validate_ads_business_context_payload(payload))
        if action_type == ADS_TARGET_CONFIRMATION_ACTION_TYPE:
            if connector_id != "google_ads":
                errors.append(wrong("Potwierdzenie celów Ads", "dotyczy tylko Google Ads"))
            errors.extend(validate_ads_target_confirmation_payload(payload))
        if action_type == ADS_STRATEGY_REVIEW_ACTION_TYPE:
            if connector_id != "google_ads":
                errors.append(wrong("Przegląd strategii Ads", "dotyczy tylko Google Ads"))
            errors.extend(validate_ads_strategy_review_payload(payload))
        if action_type == KEYWORD_PLANNER_ACCESS_ACTION_TYPE:
            if connector_id != "google_ads":
                errors.append(wrong("Dostęp do Keyword Plannera", "dotyczy tylko Google Ads"))
            errors.extend(validate_keyword_planner_access_payload(payload))
        return errors

    if connector is None:
        errors.append(wrong("Akcja", "źródło danych nie jest znane WILQ"))
        return errors

    if action_type not in connector.supported_actions:
        errors.append(wrong("Akcja", "ten typ działania nie jest wspierany dla źródła danych"))

    if connector_id == "google_ads" and action_type == "custom_segment_candidate":
        errors.extend(validate_custom_segment_payload(payload))
    if connector_id == "google_ads" and action_type == "negative_keyword_candidate":
        errors.extend(validate_negative_keyword_payload(payload))
    if connector_id == "google_ads" and action_type == "campaign_change_review":
        errors.extend(validate_campaign_review_payload(payload))
    if connector_id == "google_ads" and action_type == "google_ads_recommendation_review":
        errors.extend(validate_recommendation_review_payload(payload))
    if connector_id == "google_ads" and action_type == "google_ads_change_history_impact_review":
        errors.extend(validate_change_history_impact_payload(payload))
    if connector_id == "google_ads" and action_type == "google_ads_search_term_ngram_review":
        errors.extend(validate_search_term_ngram_payload(payload))
    if connector_id == "google_ads" and action_type == DEMAND_GEN_READINESS_REVIEW_ACTION_TYPE:
        errors.extend(validate_demand_gen_readiness_review_payload(payload))
    if connector_id == "google_analytics_4" and action_type == GA4_TRACKING_QUALITY_ACTION_TYPE:
        errors.extend(validate_ga4_tracking_quality_payload(payload))
    if connector_id == "localo" and action_type == LOCALO_VISIBILITY_REVIEW_ACTION_TYPE:
        errors.extend(validate_localo_visibility_review_payload(payload))

    return errors
