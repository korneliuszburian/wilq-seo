from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

from wilq.schemas import AdsStrategyReviewRecord, AdsTargetGuardrailConfirmation
from wilq.storage.local_state import local_state_store

ADS_BUSINESS_CONTEXT_ACTION_ID = "act_configure_ads_business_context"
ADS_BUSINESS_CONTEXT_ACTION_TYPE = "configure_ads_business_context"
ADS_TARGET_CONFIRMATION_ACTION_ID = "act_confirm_ads_target_guardrails"
ADS_TARGET_CONFIRMATION_ACTION_TYPE = "confirm_ads_target_guardrails"
ADS_STRATEGY_REVIEW_ACTION_ID = "act_record_ads_strategy_review"
ADS_STRATEGY_REVIEW_ACTION_TYPE = "record_ads_strategy_review"
ADS_PROFIT_MARGIN_ENV = "WILQ_ADS_PROFIT_MARGIN"
ADS_PROFIT_MARGIN_PCT_ENV = "WILQ_ADS_PROFIT_MARGIN_PCT"
ADS_BUSINESS_GOAL_ENV = "WILQ_ADS_BUSINESS_GOAL"
ADS_BUDGET_GOAL_ENV = "WILQ_ADS_BUDGET_GOAL"
ADS_TARGET_ROAS_ENV = "WILQ_ADS_TARGET_ROAS"
ADS_TARGET_CPA_MICROS_ENV = "WILQ_ADS_TARGET_CPA_MICROS"

ADS_BUSINESS_CONTEXT_REQUIRED_ENV = (
    ADS_PROFIT_MARGIN_ENV,
    ADS_BUSINESS_GOAL_ENV,
    ADS_BUDGET_GOAL_ENV,
)
ADS_BUSINESS_CONTEXT_TARGET_ENV_OPTIONS = (
    ADS_TARGET_ROAS_ENV,
    ADS_TARGET_CPA_MICROS_ENV,
)
ADS_BUSINESS_CONTEXT_BLOCKING_CONTRACTS = {
    "profit_margin",
    "business_goal",
    "human_budget_goal",
}


def ads_business_context_payload(
    missing_read_contracts: Iterable[str],
) -> dict[str, Any]:
    return {
        "action_type": ADS_BUSINESS_CONTEXT_ACTION_TYPE,
        "connector": "google_ads",
        "mode": "prepare_only",
        "credential_source": "repo_env",
        "required_env": list(ADS_BUSINESS_CONTEXT_REQUIRED_ENV),
        "alternative_env": {
            "profit_margin": [ADS_PROFIT_MARGIN_ENV, ADS_PROFIT_MARGIN_PCT_ENV],
            "target_roas_or_cpa": list(ADS_BUSINESS_CONTEXT_TARGET_ENV_OPTIONS),
        },
        "missing_read_contracts": list(missing_read_contracts),
        "helper_commands": [
            "Edytuj repo-local .env i ustaw nie-sekretne cele biznesowe Ads.",
            "scripts/local_stack.sh restart",
            (
                "curl -sS http://127.0.0.1:8000/api/ads/diagnostics "
                "| jq '.business_context_read_contract'"
            ),
        ],
        "required_validation": [
            "human_business_goal_review",
            "profit_margin_or_value_model_review",
            "target_roas_or_cpa_review",
        ],
        "blocked_claims": [
            "opłacalność",
            "ocena marży",
            "skalowanie budżetu",
            "zmiana budżetu",
            "zmarnowany budżet",
        ],
        "apply_allowed": False,
        "destructive": False,
    }


def ads_target_confirmation_payload(
    missing_read_contracts: Iterable[str],
) -> dict[str, Any]:
    profit_margin, profit_margin_source = ads_profit_margin_env()
    business_goal, business_goal_source = ads_text_env(ADS_BUSINESS_GOAL_ENV)
    budget_goal, budget_goal_source = ads_text_env(ADS_BUDGET_GOAL_ENV)
    (
        target_roas,
        target_roas_source,
        target_cpa_micros,
        target_cpa_source,
        target_confirmation,
    ) = ads_target_guardrail_values()
    configured_sources = [
        source
        for source in [
            profit_margin_source,
            business_goal_source,
            budget_goal_source,
            target_roas_source,
            target_cpa_source,
        ]
        if source
    ]
    return {
        "action_type": ADS_TARGET_CONFIRMATION_ACTION_TYPE,
        "connector": "google_ads",
        "mode": "prepare_only",
        "credential_source": "repo_env",
        "current_context": {
            "profit_margin": profit_margin,
            "business_goal": business_goal,
            "budget_goal": budget_goal,
            "target_roas": target_roas,
            "target_cpa_micros": target_cpa_micros,
            "configured_sources": configured_sources,
            "target_confirmation_id": target_confirmation.id
            if target_confirmation is not None
            else None,
        },
        "target_env_options": {
            "target_roas_or_cpa": list(ADS_BUSINESS_CONTEXT_TARGET_ENV_OPTIONS),
        },
        "missing_read_contracts": list(missing_read_contracts),
        "helper_commands": [
            (
                "Ustal z operatorem czy zasada bezpieczeństwa Ads ma być "
                "docelowym zwrotem z reklam czy docelowym kosztem pozyskania celu."
            ),
            (
                "Potwierdź target przez potwierdzenie akcji albo ustaw repo-local "
                ".env: WILQ_ADS_TARGET_ROAS albo WILQ_ADS_TARGET_CPA_MICROS."
            ),
            "scripts/local_stack.sh restart",
            (
                "curl -sS http://127.0.0.1:8000/api/ads/diagnostics "
                "| jq '.business_context_read_contract.target_interpretation'"
            ),
        ],
        "required_validation": [
            "review_profit_margin_model",
            "review_business_goal",
            "review_human_budget_goal",
            "confirm_target_roas_or_cpa",
            "human_strategy_review",
        ],
        "allowed_uses_after_confirmation": [
            "target_kpi_review",
            "campaign_review_context",
            "budget_review_context",
        ],
        "blocked_claims": [
            "ocena KPI względem celu przed potwierdzeniem",
            "ocena opłacalności",
            "skalowanie budżetu",
            "zmiana budżetu",
            "zapis rekomendacji",
        ],
        "apply_allowed": False,
        "destructive": False,
    }


def ads_strategy_review_payload() -> dict[str, Any]:
    profit_margin, profit_margin_source = ads_profit_margin_env()
    business_goal, business_goal_source = ads_text_env(ADS_BUSINESS_GOAL_ENV)
    budget_goal, budget_goal_source = ads_text_env(ADS_BUDGET_GOAL_ENV)
    (
        target_roas,
        target_roas_source,
        target_cpa_micros,
        target_cpa_source,
        target_confirmation,
    ) = ads_target_guardrail_values()
    latest_review = ads_strategy_review_state()
    configured_sources = [
        source
        for source in [
            profit_margin_source,
            business_goal_source,
            budget_goal_source,
            target_roas_source,
            target_cpa_source,
        ]
        if source
    ]
    return {
        "action_type": ADS_STRATEGY_REVIEW_ACTION_TYPE,
        "connector": "google_ads",
        "mode": "prepare_only",
        "credential_source": "repo_env",
        "current_context": {
            "profit_margin": profit_margin,
            "business_goal": business_goal,
            "budget_goal": budget_goal,
            "target_roas": target_roas,
            "target_cpa_micros": target_cpa_micros,
            "configured_sources": configured_sources,
            "target_confirmation_id": target_confirmation.id
            if target_confirmation is not None
            else None,
        },
        "latest_strategy_review": latest_review.model_dump(mode="json")
        if latest_review is not None
        else None,
        "required_validation": [
            "review_profit_margin_model",
            "review_business_goal",
            "review_human_budget_goal",
            "review_target_fit",
            "record_human_strategy_review_outcome",
        ],
        "operator_review_gates": [
            "human_strategy_review",
            "review_profit_margin_model",
            "review_business_goal",
            "review_human_budget_goal",
            "review_target_fit",
        ],
        "blocked_claims": [
            "ocena opłacalności",
            "skalowanie budżetu",
            "zmiana budżetu",
            "zapis rekomendacji",
            "automatyczna optymalizacja",
        ],
        "apply_allowed": False,
        "destructive": False,
    }


def ads_business_context_missing_read_contracts() -> list[str]:
    profit_margin, _profit_margin_source = ads_profit_margin_env()
    business_goal, _business_goal_source = ads_text_env(ADS_BUSINESS_GOAL_ENV)
    budget_goal, _budget_goal_source = ads_text_env(ADS_BUDGET_GOAL_ENV)
    target_roas, _target_roas_source, target_cpa_micros, _target_cpa_source, _ = (
        ads_target_guardrail_values()
    )
    strategy_review = ads_strategy_review_state()
    missing_read_contracts: list[str] = []
    if profit_margin is None:
        missing_read_contracts.append("profit_margin")
    if not business_goal:
        missing_read_contracts.append("business_goal")
    if not budget_goal:
        missing_read_contracts.append("human_budget_goal")
    if target_roas is None and target_cpa_micros is None:
        missing_read_contracts.append("target_roas_or_cpa")
    if strategy_review is None:
        missing_read_contracts.append("human_strategy_review")
    return missing_read_contracts


def ads_business_context_configured() -> bool:
    missing_read_contracts = ads_business_context_missing_read_contracts()
    return not any(
        contract in ADS_BUSINESS_CONTEXT_BLOCKING_CONTRACTS
        for contract in missing_read_contracts
    )


def ads_profit_margin_env() -> tuple[float | None, str | None]:
    value, source = ads_float_env(ADS_PROFIT_MARGIN_ENV)
    if value is None:
        value, source = ads_float_env(ADS_PROFIT_MARGIN_PCT_ENV)
    if value is None or source is None:
        return None, None
    if value > 1:
        value = value / 100
    if value <= 0 or value >= 1:
        return None, None
    return round(value, 6), source


def ads_text_env(name: str) -> tuple[str | None, str | None]:
    value = os.getenv(name, "").strip()
    if not value:
        return None, None
    return value, name


def ads_float_env(name: str) -> tuple[float | None, str | None]:
    value = os.getenv(name, "").strip()
    if not value:
        return None, None
    try:
        return float(value.replace(",", ".")), name
    except ValueError:
        return None, None


def ads_int_env(name: str) -> tuple[int | None, str | None]:
    value = os.getenv(name, "").strip()
    if not value:
        return None, None
    try:
        return int(value), name
    except ValueError:
        return None, None


def ads_target_guardrail_values() -> tuple[
    float | None,
    str | None,
    int | None,
    str | None,
    AdsTargetGuardrailConfirmation | None,
]:
    target_roas, target_roas_source = ads_float_env(ADS_TARGET_ROAS_ENV)
    target_cpa_micros, target_cpa_source = ads_int_env(ADS_TARGET_CPA_MICROS_ENV)
    if target_roas is not None or target_cpa_micros is not None:
        return target_roas, target_roas_source, target_cpa_micros, target_cpa_source, None

    target_confirmation = local_state_store().latest_ads_target_guardrail_confirmation()
    if target_confirmation is None:
        return None, None, None, None, None

    target_source = f"local_state:{target_confirmation.action_id}"
    if target_confirmation.target_roas is not None:
        return target_confirmation.target_roas, target_source, None, None, target_confirmation
    return None, None, target_confirmation.target_cpa_micros, target_source, target_confirmation


def ads_strategy_review_state() -> AdsStrategyReviewRecord | None:
    return local_state_store().latest_ads_strategy_review()


def validate_ads_business_context_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("connector") != "google_ads":
        errors.append("configure_ads_business_context requires connector=google_ads.")
    if payload.get("mode") != "prepare_only":
        errors.append("configure_ads_business_context requires mode=prepare_only.")
    required_env = payload.get("required_env")
    if not isinstance(required_env, list) or not set(ADS_BUSINESS_CONTEXT_REQUIRED_ENV).issubset(
        set(required_env)
    ):
        errors.append("configure_ads_business_context requires core business env names.")
    alternative_env = payload.get("alternative_env")
    if not isinstance(alternative_env, dict) or "target_roas_or_cpa" not in alternative_env:
        errors.append("configure_ads_business_context requires target_roas_or_cpa options.")
    missing_read_contracts = payload.get("missing_read_contracts")
    if not isinstance(missing_read_contracts, list):
        errors.append("configure_ads_business_context requires missing_read_contracts list.")
    if payload.get("apply_allowed") is not False:
        errors.append("configure_ads_business_context must keep apply_allowed=false.")
    if payload.get("destructive") is not False:
        errors.append("configure_ads_business_context must be non-destructive.")
    if not isinstance(payload.get("helper_commands"), list):
        errors.append("configure_ads_business_context requires helper_commands list.")
    return errors


def validate_ads_target_confirmation_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("connector") != "google_ads":
        errors.append("confirm_ads_target_guardrails requires connector=google_ads.")
    if payload.get("mode") != "prepare_only":
        errors.append("confirm_ads_target_guardrails requires mode=prepare_only.")
    current_context = payload.get("current_context")
    if not isinstance(current_context, dict):
        errors.append("confirm_ads_target_guardrails requires current_context.")
    else:
        for key in ("profit_margin", "business_goal", "budget_goal"):
            if key not in current_context:
                errors.append(f"confirm_ads_target_guardrails missing current_context.{key}.")
    target_env_options = payload.get("target_env_options")
    if not isinstance(target_env_options, dict):
        errors.append("confirm_ads_target_guardrails requires target_env_options.")
    elif set(target_env_options.get("target_roas_or_cpa", [])) != set(
        ADS_BUSINESS_CONTEXT_TARGET_ENV_OPTIONS
    ):
        errors.append(
            "confirm_ads_target_guardrails requires WILQ_ADS_TARGET_ROAS or "
            "WILQ_ADS_TARGET_CPA_MICROS env options."
        )
    missing_read_contracts = payload.get("missing_read_contracts")
    if (
        not isinstance(missing_read_contracts, list)
        or "target_roas_or_cpa" not in missing_read_contracts
    ):
        errors.append("confirm_ads_target_guardrails requires target_roas_or_cpa missing.")
    required_validation = payload.get("required_validation")
    if (
        not isinstance(required_validation, list)
        or "confirm_target_roas_or_cpa" not in required_validation
    ):
        errors.append("confirm_ads_target_guardrails requires target confirmation validation.")
    if payload.get("apply_allowed") is not False:
        errors.append("confirm_ads_target_guardrails must keep apply_allowed=false.")
    if payload.get("destructive") is not False:
        errors.append("confirm_ads_target_guardrails must be non-destructive.")
    if not isinstance(payload.get("helper_commands"), list):
        errors.append("confirm_ads_target_guardrails requires helper_commands list.")
    return errors


def validate_ads_strategy_review_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("connector") != "google_ads":
        errors.append("record_ads_strategy_review requires connector=google_ads.")
    if payload.get("mode") != "prepare_only":
        errors.append("record_ads_strategy_review requires mode=prepare_only.")
    if not isinstance(payload.get("current_context"), dict):
        errors.append("record_ads_strategy_review requires current_context.")
    required_validation = payload.get("required_validation")
    if (
        not isinstance(required_validation, list)
        or "record_human_strategy_review_outcome" not in required_validation
    ):
        errors.append("record_ads_strategy_review requires strategy review validation.")
    if payload.get("apply_allowed") is not False:
        errors.append("record_ads_strategy_review must keep apply_allowed=false.")
    if payload.get("destructive") is not False:
        errors.append("record_ads_strategy_review must be non-destructive.")
    return errors
