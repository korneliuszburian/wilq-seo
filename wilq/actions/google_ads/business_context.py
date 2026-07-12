from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from typing import Any, Protocol

from wilq.actions.validation_copy import missing, no_destructive_change, no_write, wrong
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionPreviewCardViewModel,
    ActionPreviewRowViewModel,
    ActionRisk,
    ActionStatus,
    AdsStrategyReviewRecord,
    AdsTargetGuardrailConfirmation,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
    OpportunityDomain,
)
from wilq.storage.local_state import local_state_store

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
StringList = Callable[[Any], list[str]]
ContextRows = Callable[[dict[str, Any]], list[ActionPreviewRowViewModel]]
StateLabel = Callable[[Any], str]
SummaryLabel = Callable[[Any], str]


class MetricLabel(Protocol):
    def __call__(self, value: Any, *, missing_label: str = "brak danych") -> str: ...


class MoneyLabel(Protocol):
    def __call__(
        self,
        value: Any,
        currency_code: str = "PLN",
        *,
        missing_label: str = "kwota niepotwierdzona",
    ) -> str: ...

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


def latest_google_ads_vendor_read(
    runs: Iterable[ConnectorRefreshRun],
) -> ConnectorRefreshRun | None:
    vendor_reads = [run for run in runs if run.mode == ConnectorRefreshMode.vendor_read]
    if not vendor_reads:
        return None
    return max(vendor_reads, key=connector_refresh_recency_key)


def connector_refresh_recency_key(run: ConnectorRefreshRun) -> tuple[str, str]:
    timestamp = run.completed_at or run.started_at
    return (timestamp.isoformat(), run.id)


def latest_google_ads_metric_facts(
    run: ConnectorRefreshRun | None,
    *,
    metric_facts_by_evidence_ids: Callable[[list[str]], list[MetricFact]],
) -> list[MetricFact]:
    if (
        run is None
        or run.status != ConnectorRefreshStatus.completed
        or not run.vendor_data_collected
        or not run.evidence_ids
    ):
        return []
    return [
        fact
        for fact in metric_facts_by_evidence_ids(run.evidence_ids)
        if fact.source_connector == "google_ads"
    ]


def business_context_action(
    *,
    missing_read_contracts: Iterable[str],
    evidence_ids: list[str],
) -> ActionObject:
    return ActionObject(
        id=ADS_BUSINESS_CONTEXT_ACTION_ID,
        title="Uzupełnij kontekst biznesowy Google Ads",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=evidence_ids,
        human_diagnosis=(
            "Google Ads ma live metryki, ale WILQ nie ma nie-sekretnych celów "
            "biznesowych Ekologus: marży, celu biznesowego, celu budżetu oraz "
            "docelowego zwrotu z reklam albo kosztu pozyskania celu."
        ),
        recommended_reason=(
            "Uzupełnij repo-local .env wartościami biznesowymi Ads, potem sprawdź "
            "kontekst biznesowy Ads. Do tego czasu WILQ blokuje obietnice "
            "o rentowności, zmarnowanym budżecie i skalowaniu."
        ),
        payload=ads_business_context_payload(missing_read_contracts),
        validation_status="not_validated",
        created_by="system_business_context_seed",
    )


def target_confirmation_action(
    *,
    missing_read_contracts: Iterable[str],
    evidence_ids: list[str],
) -> ActionObject:
    return ActionObject(
        id=ADS_TARGET_CONFIRMATION_ACTION_ID,
        title="Potwierdź docelowy zwrot z reklam albo koszt pozyskania celu dla Ads",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=evidence_ids,
        human_diagnosis=(
            "Google Ads ma live metryki oraz lokalny kontekst biznesowy, ale brakuje "
            "potwierdzonego zwrotu z reklam albo kosztu pozyskania celu. "
            "WILQ może robić ocenę kampanii, ale nie może wydać werdyktu KPI ani "
            "uruchamiać zapisu zmian budżetu lub rekomendacji."
        ),
        recommended_reason=(
            "Potwierdź jedną zasadę bezpieczeństwa celu w repo-local .env. To nadal jest "
            "krok bez zapisu zmian: bez mutacji Google Ads, bez automatycznego "
            "skalowania i bez werdyktu rentowności."
        ),
        payload=ads_target_confirmation_payload(missing_read_contracts),
        validation_status="not_validated",
        created_by="system_ads_target_confirmation_seed",
    )


def strategy_review_action(*, evidence_ids: list[str]) -> ActionObject:
    return ActionObject(
        id=ADS_STRATEGY_REVIEW_ACTION_ID,
        title="Zapisz ocenę strategii Ads przez człowieka",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=evidence_ids,
        human_diagnosis=(
            "Google Ads ma live metryki i lokalny kontekst biznesowy, ale brakuje "
            "zapisanego wyniku ludzkiej oceny strategii. WILQ nie powinien "
            "traktować celu ani KPI jako decyzji operacyjnej bez tego zapisu."
        ),
        recommended_reason=(
            "Zapisz wynik oceny: zatwierdzone do dalszego przygotowania, wymaga "
            "poprawek, odrzucone albo odłożone. To nadal nie wykonuje zapisu zmian ani "
            "mutacji Google Ads."
        ),
        payload=ads_strategy_review_payload(),
        validation_status="not_validated",
        created_by="system_ads_strategy_review_seed",
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
            "target_metrics_review",
            "campaign_review_context",
            "budget_review_context",
        ],
        "blocked_claims": [
            "ocena wskaźników względem celu przed potwierdzeniem",
            "ocena opłacalności",
            "skalowanie budżetu",
            "zmiana budżetu",
            "zapis rekomendacji",
        ],
        "apply_allowed": False,
        "destructive": False,
    }


def ads_target_guardrail_preview_cards(
    payload: dict[str, Any],
    *,
    business_context_rows: ContextRows,
    preview_row: PreviewRow,
    string_list: StringList,
    apply_state_label: StateLabel,
    system_readiness_label: StateLabel,
) -> list[ActionPreviewCardViewModel]:
    """Render target guardrail review without exposing technical payloads."""
    rows = business_context_rows(payload)
    target_env_options = payload.get("target_env_options")
    target_env_options = target_env_options if isinstance(target_env_options, dict) else {}
    target_options = string_list(target_env_options.get("target_roas_or_cpa_labels"))
    if target_options:
        rows.append(preview_row("Opcje celu", ", ".join(target_options[:4])))
    missing_labels = string_list(payload.get("missing_read_contract_labels"))
    if missing_labels:
        rows.append(preview_row("Braki", ", ".join(missing_labels[:4])))
    allowed_labels = string_list(payload.get("allowed_uses_after_confirmation_labels"))
    if allowed_labels:
        rows.append(preview_row("Po potwierdzeniu", ", ".join(allowed_labels[:4])))
    requirement_labels = string_list(payload.get("required_validation_labels"))
    if requirement_labels:
        rows.append(preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:5])))
    blocked_claim_labels = string_list(payload.get("blocked_claim_labels"))
    if blocked_claim_labels:
        rows.append(
            preview_row(
                "Czego nie wolno twierdzić",
                ", ".join(blocked_claim_labels[:4]),
            )
        )
    return [
        ActionPreviewCardViewModel(
            id="ads_target_guardrail_review",
            kind="google_ads_target_guardrail_review",
            title_label="Cel Ads do potwierdzenia",
            subtitle_label="ocena celu biznesowego bez zapisu zmian",
            status_label="zapis zmian zablokowany",
            rows=rows,
            apply_state_label=apply_state_label(payload.get("apply_allowed")),
            system_readiness_label=system_readiness_label(payload.get("api_mutation_ready")),
        )
    ]


def ads_business_context_preview_rows(
    payload: dict[str, Any],
    *,
    preview_row: PreviewRow,
    plain_metric_value_label: MetricLabel,
    micros_money_label: MoneyLabel,
) -> list[ActionPreviewRowViewModel]:
    """Build shared Ads business-context rows for operator cards."""
    context = payload.get("current_context")
    context = context if isinstance(context, dict) else {}
    configured_sources = context.get("configured_sources")
    configured_sources = configured_sources if isinstance(configured_sources, list) else []
    configured_sources = [item for item in configured_sources if isinstance(item, str)]
    return [
        preview_row("Marża", _percentage_label(context.get("profit_margin"))),
        preview_row("Cel biznesowy", plain_metric_value_label(context.get("business_goal"))),
        preview_row("Cel budżetu", plain_metric_value_label(context.get("budget_goal"))),
        preview_row(
            "Docelowy zwrot z reklam",
            plain_metric_value_label(
                context.get("target_roas"),
                missing_label="nie ustawiono; WILQ nie ocenia opłacalności Ads",
            ),
        ),
        preview_row(
            "Docelowy koszt pozyskania celu",
            micros_money_label(
                context.get("target_cpa_micros"),
                missing_label="nie ustawiono; WILQ nie ocenia kosztu celu",
            ),
        ),
        preview_row("Ustawione pola", _configured_source_count_label(configured_sources)),
    ]


def ads_strategy_review_summary(value: Any) -> str:
    if not isinstance(value, dict):
        return "przegląd strategii nie jest zapisany"
    outcome = value.get("outcome")
    labels = {
        "approved_for_prepare": "zatwierdzone do przygotowania",
        "needs_changes": "wymaga poprawek",
        "rejected": "odrzucone",
        "deferred": "odłożone",
    }
    if isinstance(outcome, str):
        return labels.get(outcome, "przegląd zapisany")
    return "przegląd zapisany"


def _configured_source_count_label(values: list[str]) -> str:
    count = len(values)
    if count == 0:
        return "żadne pole nie jest ustawione lokalnie"
    if count == 1:
        return "1 pole ustawione lokalnie"
    if 2 <= count <= 4:
        return f"{count} pola ustawione lokalnie"
    return f"{count} pól ustawionych lokalnie"


def _percentage_label(value: Any) -> str:
    if not isinstance(value, int | float):
        return "wartość procentowa niepotwierdzona"
    numeric_label = f"{value * 100:.2f}".rstrip("0").rstrip(".")
    return f"{numeric_label}%"


def micros_money_label(
    value: Any,
    currency_code: str = "PLN",
    *,
    missing_label: str = "kwota niepotwierdzona",
) -> str:
    if not isinstance(value, int | float):
        return missing_label
    return f"{value / 1_000_000:.2f} {currency_code}"


def ads_strategy_review_preview_cards(
    payload: dict[str, Any],
    *,
    business_context_rows: ContextRows,
    preview_row: PreviewRow,
    string_list: StringList,
    strategy_summary: SummaryLabel,
    apply_state_label: StateLabel,
    system_readiness_label: StateLabel,
) -> list[ActionPreviewCardViewModel]:
    """Render Ads strategy review without exposing technical payloads."""
    rows = business_context_rows(payload)
    rows.append(
        preview_row(
            "Ostatni przegląd strategii",
            strategy_summary(payload.get("latest_strategy_review")),
        )
    )
    gate_labels = string_list(payload.get("operator_review_gate_labels"))
    if gate_labels:
        rows.append(preview_row("Warunki przeglądu", ", ".join(gate_labels[:5])))
    requirement_labels = string_list(payload.get("required_validation_labels"))
    if requirement_labels:
        rows.append(preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:5])))
    blocked_claim_labels = string_list(payload.get("blocked_claim_labels"))
    if blocked_claim_labels:
        rows.append(
            preview_row(
                "Czego nie wolno twierdzić",
                ", ".join(blocked_claim_labels[:4]),
            )
        )
    return [
        ActionPreviewCardViewModel(
            id="ads_strategy_review",
            kind="google_ads_strategy_review",
            title_label="Ocena strategii Ads do zapisania",
            subtitle_label="decyzja człowieka bez zapisu zmian w Google Ads",
            status_label="zapis zmian zablokowany",
            rows=rows,
            apply_state_label=apply_state_label(payload.get("apply_allowed")),
            system_readiness_label=system_readiness_label(payload.get("api_mutation_ready")),
        )
    ]


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
        contract in ADS_BUSINESS_CONTEXT_BLOCKING_CONTRACTS for contract in missing_read_contracts
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
    subject = "Kontekst biznesowy Google Ads"
    if payload.get("connector") != "google_ads":
        errors.append(wrong(subject, "dotyczy tylko Google Ads"))
    if payload.get("mode") != "prepare_only":
        errors.append(wrong(subject, "musi pozostać etapem przygotowania"))
    required_env = payload.get("required_env")
    if not isinstance(required_env, list) or not set(ADS_BUSINESS_CONTEXT_REQUIRED_ENV).issubset(
        set(required_env)
    ):
        errors.append(missing(subject, "podstawowych ustawień biznesowych"))
    alternative_env = payload.get("alternative_env")
    if not isinstance(alternative_env, dict) or "target_roas_or_cpa" not in alternative_env:
        errors.append(missing(subject, "wariantów celu kosztu lub zwrotu z reklam"))
    missing_read_contracts = payload.get("missing_read_contracts")
    if not isinstance(missing_read_contracts, list):
        errors.append(missing(subject, "listy brakujących odczytów"))
    if payload.get("apply_allowed") is not False:
        errors.append(no_write(subject))
    if payload.get("destructive") is not False:
        errors.append(no_destructive_change(subject))
    if not isinstance(payload.get("helper_commands"), list):
        errors.append(missing(subject, "instrukcji pomocniczych"))
    return errors


def validate_ads_target_confirmation_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    subject = "Potwierdzenie celów Google Ads"
    if payload.get("connector") != "google_ads":
        errors.append(wrong(subject, "dotyczy tylko Google Ads"))
    if payload.get("mode") != "prepare_only":
        errors.append(wrong(subject, "musi pozostać etapem przygotowania"))
    current_context = payload.get("current_context")
    if not isinstance(current_context, dict):
        errors.append(missing(subject, "obecnego kontekstu biznesowego"))
    else:
        for key in ("profit_margin", "business_goal", "budget_goal"):
            if key not in current_context:
                errors.append(missing(subject, "pełnego kontekstu biznesowego"))
    target_env_options = payload.get("target_env_options")
    if not isinstance(target_env_options, dict):
        errors.append(missing(subject, "wariantów ustawień celu"))
    elif set(target_env_options.get("target_roas_or_cpa", [])) != set(
        ADS_BUSINESS_CONTEXT_TARGET_ENV_OPTIONS
    ):
        errors.append(missing(subject, "celu zwrotu z reklam albo kosztu pozyskania celu"))
    missing_read_contracts = payload.get("missing_read_contracts")
    if (
        not isinstance(missing_read_contracts, list)
        or "target_roas_or_cpa" not in missing_read_contracts
    ):
        errors.append(missing(subject, "informacji o brakującym celu biznesowym"))
    required_validation = payload.get("required_validation")
    if (
        not isinstance(required_validation, list)
        or "confirm_target_roas_or_cpa" not in required_validation
    ):
        errors.append(missing(subject, "sprawdzenia celu przez człowieka"))
    if payload.get("apply_allowed") is not False:
        errors.append(no_write(subject))
    if payload.get("destructive") is not False:
        errors.append(no_destructive_change(subject))
    if not isinstance(payload.get("helper_commands"), list):
        errors.append(missing(subject, "instrukcji pomocniczych"))
    return errors


def validate_ads_strategy_review_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    subject = "Przegląd strategii Google Ads"
    if payload.get("connector") != "google_ads":
        errors.append(wrong(subject, "dotyczy tylko Google Ads"))
    if payload.get("mode") != "prepare_only":
        errors.append(wrong(subject, "musi pozostać etapem przygotowania"))
    if not isinstance(payload.get("current_context"), dict):
        errors.append(missing(subject, "obecnego kontekstu biznesowego"))
    required_validation = payload.get("required_validation")
    if (
        not isinstance(required_validation, list)
        or "record_human_strategy_review_outcome" not in required_validation
    ):
        errors.append(missing(subject, "sprawdzenia strategii przez człowieka"))
    if payload.get("apply_allowed") is not False:
        errors.append(no_write(subject))
    if payload.get("destructive") is not False:
        errors.append(no_destructive_change(subject))
    return errors
