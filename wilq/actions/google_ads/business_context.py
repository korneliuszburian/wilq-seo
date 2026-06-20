from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

ADS_BUSINESS_CONTEXT_ACTION_ID = "act_configure_ads_business_context"
ADS_BUSINESS_CONTEXT_ACTION_TYPE = "configure_ads_business_context"
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
            "profitability",
            "margin verdict",
            "budget scaling",
            "budget apply",
            "wasted budget",
        ],
        "apply_allowed": False,
        "destructive": False,
    }


def ads_business_context_missing_read_contracts() -> list[str]:
    profit_margin, _profit_margin_source = ads_profit_margin_env()
    business_goal, _business_goal_source = ads_text_env(ADS_BUSINESS_GOAL_ENV)
    budget_goal, _budget_goal_source = ads_text_env(ADS_BUDGET_GOAL_ENV)
    target_roas, _target_roas_source = ads_float_env(ADS_TARGET_ROAS_ENV)
    target_cpa_micros, _target_cpa_source = ads_int_env(ADS_TARGET_CPA_MICROS_ENV)
    missing_read_contracts: list[str] = []
    if profit_margin is None:
        missing_read_contracts.append("profit_margin")
    if not business_goal:
        missing_read_contracts.append("business_goal")
    if not budget_goal:
        missing_read_contracts.append("human_budget_goal")
    if target_roas is None and target_cpa_micros is None:
        missing_read_contracts.append("target_roas_or_cpa")
    return missing_read_contracts


def ads_business_context_configured() -> bool:
    return not ads_business_context_missing_read_contracts()


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
