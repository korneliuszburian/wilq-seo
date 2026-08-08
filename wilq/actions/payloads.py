from __future__ import annotations

from collections.abc import Callable
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
from wilq.content.workflow.target.dev_draft_action import CONTENT_DEV_DRAFT_ACTION_TYPE
from wilq.content.workflow.target.dev_draft_discard_action import (
    CONTENT_DEV_DRAFT_DISCARD_ACTION_CONTRACT,
    CONTENT_DEV_DRAFT_DISCARD_ACTION_TYPE,
)
from wilq.content.workflow.target.new_page_draft_action import (
    CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE,
)
from wilq.content.workflow.target.new_page_draft_validation import (
    validate_new_page_draft_action_payload,
)

INTERNAL_ACTION_TYPES = {
    "configure_connector",
    "repair_google_ads_oauth",
    ADS_BUSINESS_CONTEXT_ACTION_TYPE,
    ADS_TARGET_CONFIRMATION_ACTION_TYPE,
    ADS_STRATEGY_REVIEW_ACTION_TYPE,
    KEYWORD_PLANNER_ACCESS_ACTION_TYPE,
}

SERVICE_PROFILE_KNOWLEDGE_PROMOTION_ACTION_TYPE = "service_profile_knowledge_promotion_review"
SERVICE_PROFILE_PRIVATE_PROPOSAL_PROMOTION_ACTION_TYPE = (
    "service_profile_private_proposal_promotion_review"
)


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

    validator = _connector_payload_validator(connector_id, action_type)
    if validator is not None:
        errors.extend(validator(payload))

    return errors


def _connector_payload_validator(
    connector_id: str,
    action_type: str,
) -> Callable[[dict[str, Any]], list[str]] | None:
    return {
        ("google_ads", "custom_segment_candidate"): validate_custom_segment_payload,
        ("google_ads", "negative_keyword_candidate"): validate_negative_keyword_payload,
        ("google_ads", "campaign_change_review"): validate_campaign_review_payload,
        ("google_ads", "google_ads_recommendation_review"): validate_recommendation_review_payload,
        (
            "google_ads",
            "google_ads_change_history_impact_review",
        ): validate_change_history_impact_payload,
        ("google_ads", "google_ads_search_term_ngram_review"): validate_search_term_ngram_payload,
        (
            "google_ads",
            DEMAND_GEN_READINESS_REVIEW_ACTION_TYPE,
        ): validate_demand_gen_readiness_review_payload,
        (
            "google_analytics_4",
            GA4_TRACKING_QUALITY_ACTION_TYPE,
        ): validate_ga4_tracking_quality_payload,
        ("localo", LOCALO_VISIBILITY_REVIEW_ACTION_TYPE): validate_localo_visibility_review_payload,
        (
            "wordpress_ekologus",
            SERVICE_PROFILE_KNOWLEDGE_PROMOTION_ACTION_TYPE,
        ): validate_service_profile_knowledge_promotion_payload,
        (
            "wordpress_ekologus",
            SERVICE_PROFILE_PRIVATE_PROPOSAL_PROMOTION_ACTION_TYPE,
        ): validate_service_profile_private_proposal_promotion_payload,
        (
            "wordpress_ekologus",
            CONTENT_DEV_DRAFT_ACTION_TYPE,
        ): validate_content_dev_draft_action_payload,
        (
            "wordpress_ekologus",
            CONTENT_DEV_DRAFT_DISCARD_ACTION_TYPE,
        ): validate_content_dev_draft_discard_action_payload,
        (
            "wordpress_ekologus",
            CONTENT_NEW_PAGE_DEV_DRAFT_ACTION_TYPE,
        ): validate_new_page_draft_action_payload,
    }.get((connector_id, action_type))


def validate_content_dev_draft_action_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("mode") != "dev_draft_only":
        errors.append(wrong("Szkic dev", "musi pozostać w trybie dev_draft_only"))
    if payload.get("preview_contract") != "content_dev_draft_action_v1":
        errors.append(missing("Szkic dev", "kontraktu dokładnego podglądu"))
    if payload.get("apply_allowed") is not True or payload.get("api_mutation_ready") is not True:
        errors.append(
            wrong("Szkic dev", "wymaga jawnego kontraktu apply dopiero po wszystkich bramkach")
        )
    binding = payload.get("content_target_draft_binding")
    if not isinstance(binding, dict):
        errors.append(missing("Szkic dev", "dokładnego powiązania dokumentu i targetu"))
    else:
        for key in (
            "work_item_id",
            "revision_id",
            "revision_digest",
            "target_contract_digest",
            "confirmation_id",
            "confirmation_digest",
            "payload_digest",
            "root_field",
        ):
            if not isinstance(binding.get(key), str) or not binding[key]:
                errors.append(missing("Szkic dev", f"pola {key}"))
    if not isinstance(payload.get("draft_payload"), dict):
        errors.append(missing("Szkic dev", "danych dokładnego szkicu"))
    preview = payload.get("payload_preview")
    if not isinstance(preview, list) or len(preview) != 1 or not isinstance(preview[0], dict):
        errors.append(missing("Szkic dev", "jednej pozycji podglądu"))
    return errors


def validate_content_dev_draft_discard_action_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("mode") != "dev_draft_trash_only":
        errors.append(wrong("Wycofanie szkicu dev", "musi pozostać w trybie dev_draft_trash_only"))
    if payload.get("preview_contract") != CONTENT_DEV_DRAFT_DISCARD_ACTION_CONTRACT:
        errors.append(missing("Wycofanie szkicu dev", "kontraktu dokładnego podglądu"))
    if payload.get("allowed_operation") != "trash_wordpress_dev_draft":
        errors.append(wrong("Wycofanie szkicu dev", "może jedynie przenieść szkic do kosza"))
    if payload.get("recoverable_operation") is not True or payload.get("destructive") is not False:
        errors.append(wrong("Wycofanie szkicu dev", "musi pozostać odzyskiwalne"))
    if payload.get("apply_allowed") is not True or payload.get("api_mutation_ready") is not True:
        errors.append(wrong("Wycofanie szkicu dev", "wymaga jawnej gotowości apply"))
    target = payload.get("draft_discard_target")
    if not isinstance(target, dict):
        errors.append(missing("Wycofanie szkicu dev", "dokładnego targetu"))
    else:
        for key in (
            "post_id",
            "endpoint",
            "title",
            "modified_gmt",
            "content_digest",
            "acf_digest",
            "origin_action_id",
        ):
            if not isinstance(target.get(key), str) or not target[key]:
                errors.append(missing("Wycofanie szkicu dev", f"pola {key}"))
        if target.get("endpoint") not in {"posts", "pages", "uslugi"}:
            errors.append(wrong("Wycofanie szkicu dev", "wskazuje nieobsługiwany typ treści"))
        if not isinstance(target.get("defect_codes"), list) or not target["defect_codes"]:
            errors.append(missing("Wycofanie szkicu dev", "potwierdzonych problemów"))
    preview = payload.get("payload_preview")
    if not isinstance(preview, list) or len(preview) != 1 or not isinstance(preview[0], dict):
        errors.append(missing("Wycofanie szkicu dev", "jednej pozycji podglądu"))
    return errors


def validate_service_profile_knowledge_promotion_payload(
    payload: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if payload.get("mode") != "prepare_only":
        errors.append(wrong("Promocja wiedzy", "musi pozostać w trybie prepare_only"))
    if payload.get("preview_contract") != "service_profile_knowledge_promotion_preview_v1":
        errors.append(missing("Promocja wiedzy", "kontraktu podglądu"))
    if payload.get("apply_allowed") is not False:
        errors.append(wrong("Promocja wiedzy", "zapis zmian musi być zablokowany"))
    if payload.get("api_mutation_ready") is not False:
        errors.append(wrong("Promocja wiedzy", "nie może deklarować gotowości mutacji"))
    if payload.get("target_lifecycle") != "approved_current":
        errors.append(missing("Promocja wiedzy", "docelowego statusu approved_current"))
    rows = payload.get("payload_preview")
    if not isinstance(rows, list) or not rows:
        errors.append(missing("Promocja wiedzy", "pozycji do sprawdzenia"))
        return errors
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append(wrong("Promocja wiedzy", f"pozycja {index} nie jest obiektem"))
            continue
        for field_name in (
            "target_card_id",
            "target_card_title",
            "source_fact_ids",
            "review_action_id",
            "required_human_role",
            "promotion_blocked_reason",
            "evidence_ids",
        ):
            value = row.get(field_name)
            if value in (None, "", []):
                errors.append(missing("Promocja wiedzy", f"pola {field_name}"))
        if row.get("apply_allowed") is not False:
            errors.append(wrong("Promocja wiedzy", "pozycja musi blokować zapis zmian"))
        if row.get("api_mutation_ready") is not False:
            errors.append(wrong("Promocja wiedzy", "pozycja nie może być gotowa do mutacji"))
    return errors


def validate_service_profile_private_proposal_promotion_payload(
    payload: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if payload.get("mode") != "prepare_only":
        errors.append(wrong("Promocja prywatnej propozycji", "musi pozostać w trybie prepare_only"))
    if payload.get("preview_contract") != "private_source_proposal_promotion_preview_v1":
        errors.append(missing("Promocja prywatnej propozycji", "kontraktu podglądu"))
    if payload.get("apply_allowed") is not False:
        errors.append(wrong("Promocja prywatnej propozycji", "zapis zmian musi być zablokowany"))
    if payload.get("api_mutation_ready") is not False:
        errors.append(
            wrong(
                "Promocja prywatnej propozycji",
                "nie może deklarować gotowości mutacji",
            )
        )
    rows = payload.get("payload_preview")
    if not isinstance(rows, list) or not rows:
        errors.append(missing("Promocja prywatnej propozycji", "pozycji do sprawdzenia"))
        return errors
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append(
                wrong(
                    "Promocja prywatnej propozycji",
                    f"pozycja {index} nie jest obiektem",
                )
            )
            continue
        for field_name in (
            "proposal_id",
            "source_id",
            "scope",
            "target_card_id",
            "target_card_title",
            "review_action_id",
            "required_human_role",
            "data_classes",
            "source_block_refs",
            "freshness_status",
            "audience",
            "retention_decision",
            "deletion_path",
            "eval_case_ids",
            "promotion_blocked_reason",
            "evidence_ids",
        ):
            value = row.get(field_name)
            if value in (None, "", []):
                errors.append(missing("Promocja prywatnej propozycji", f"pola {field_name}"))
        if row.get("redacted") is not True:
            errors.append(wrong("Promocja prywatnej propozycji", "pozycja musi być redacted"))
        if row.get("apply_allowed") is not False:
            errors.append(
                wrong(
                    "Promocja prywatnej propozycji",
                    "pozycja musi blokować zapis zmian",
                )
            )
        if row.get("api_mutation_ready") is not False:
            errors.append(
                wrong(
                    "Promocja prywatnej propozycji",
                    "pozycja nie może być gotowa do mutacji",
                )
            )
    return errors
