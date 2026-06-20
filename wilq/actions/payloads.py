from __future__ import annotations

from typing import Any

from wilq.actions.google_ads.business_context import (
    ADS_BUSINESS_CONTEXT_ACTION_TYPE,
    validate_ads_business_context_payload,
)
from wilq.actions.google_ads.campaign_review import validate_campaign_review_payload
from wilq.actions.google_ads.custom_segments import validate_custom_segment_payload
from wilq.actions.google_ads.negative_keywords import validate_negative_keyword_payload
from wilq.actions.google_ads.recommendations import validate_recommendation_review_payload
from wilq.connectors.registry import get_connector_status

INTERNAL_ACTION_TYPES = {
    "configure_connector",
    "repair_google_ads_oauth",
    ADS_BUSINESS_CONTEXT_ACTION_TYPE,
}


def validate_action_payload(connector_id: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    action_type = payload.get("action_type")
    payload_connector = payload.get("connector")
    connector = get_connector_status(connector_id)

    if not isinstance(action_type, str) or not action_type.strip():
        errors.append("Action payload requires a non-empty action_type.")
        return errors

    if payload_connector is not None and payload_connector != connector_id:
        errors.append("Action payload connector must match ActionObject connector.")

    if action_type in INTERNAL_ACTION_TYPES:
        required_env = payload.get("required_env")
        if action_type == "configure_connector" and not isinstance(required_env, list):
            errors.append("configure_connector payload requires required_env list.")
        if action_type == "repair_google_ads_oauth":
            if connector_id != "google_ads":
                errors.append("repair_google_ads_oauth is only valid for google_ads.")
            if payload.get("oauth_scope") != "https://www.googleapis.com/auth/adwords":
                errors.append("repair_google_ads_oauth requires the Google Ads adwords scope.")
            if not isinstance(payload.get("oauth_client_json_path"), str):
                errors.append("repair_google_ads_oauth requires oauth_client_json_path.")
            if not isinstance(payload.get("helper_commands"), list):
                errors.append("repair_google_ads_oauth requires helper_commands list.")
        if action_type == ADS_BUSINESS_CONTEXT_ACTION_TYPE:
            if connector_id != "google_ads":
                errors.append("configure_ads_business_context is only valid for google_ads.")
            errors.extend(validate_ads_business_context_payload(payload))
        return errors

    if connector is None:
        errors.append(f"Unknown connector for payload validation: {connector_id}")
        return errors

    if action_type not in connector.supported_actions:
        errors.append(
            f"Action type {action_type} is not supported by connector {connector_id}."
        )

    if connector_id == "google_ads" and action_type == "custom_segment_candidate":
        errors.extend(validate_custom_segment_payload(payload))
    if connector_id == "google_ads" and action_type == "negative_keyword_candidate":
        errors.extend(validate_negative_keyword_payload(payload))
    if connector_id == "google_ads" and action_type == "campaign_change_review":
        errors.extend(validate_campaign_review_payload(payload))
    if connector_id == "google_ads" and action_type == "google_ads_recommendation_review":
        errors.extend(validate_recommendation_review_payload(payload))

    return errors
