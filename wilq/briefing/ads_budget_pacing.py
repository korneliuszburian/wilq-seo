from __future__ import annotations

from collections.abc import Iterable

from wilq.actions.google_ads.budget_safety import budget_apply_safety_review
from wilq.actions.google_ads.campaign_review import (
    CAMPAIGN_BUDGET_APPLY_PREVIEW_REQUIRED_VALIDATION,
    CAMPAIGN_REVIEW_ACTION_ID,
    CAMPAIGN_REVIEW_BLOCKED_CLAIMS,
)
from wilq.schemas import (
    AdsBudgetApplyPreview,
    AdsBudgetApplySafetyReview,
    AdsBudgetPacingReadContract,
    AdsBudgetPacingRow,
    AdsCampaignReadContract,
    AdsSharedBudgetCampaignShare,
    AdsSharedBudgetDistributionRow,
    MetricFact,
)

GOOGLE_ADS_CONNECTOR_ID = "google_ads"


def build_budget_pacing_read_contract(
    metric_facts: list[MetricFact],
    campaign_read_contract: AdsCampaignReadContract,
    fallback_evidence_ids: list[str],
) -> AdsBudgetPacingReadContract:
    rows = _budget_pacing_rows(metric_facts)
    shared_budget_distribution_rows = _shared_budget_distribution_rows(rows)
    payload_preview = [
        row.payload_preview for row in rows if row.payload_preview is not None
    ]
    missing_read_contracts = [
        "shared_budget_distribution",
        "budget_target_or_seasonality",
        "change_history",
        "recommendations",
        "impression_share",
        "human_budget_goal",
    ]
    blocked_claims = [
        "budget scaling",
        "zmiana budżetu",
        "profitability",
        "wasted budget",
        "zapis rekomendacji",
    ]
    if rows:
        if all(row.budget_id for row in rows):
            missing_read_contracts = _remove_missing_contract_names(
                missing_read_contracts,
                "shared_budget_distribution",
            )
        daily_rows = [row for row in rows if row.spend_to_budget_ratio_7d is not None]
        recommended_rows = [row for row in rows if row.has_recommended_budget]
        return AdsBudgetPacingReadContract(
            status="ready",
            title="Google Ads: kontekst budżetu kampanii",
            summary=(
                f"WILQ ma budżetowy kontekst dla {len(rows)} kampanii; "
                f"{len(daily_rows)} ma policzalny stosunek kosztu z 7 dni do "
                f"budżetu dziennego, a {len(recommended_rows)} ma sygnał "
                "recommended budget z Google Ads. "
                f"Wspólne budżety: {len(shared_budget_distribution_rows)}."
            ),
            allowed_metrics=[
                "budget_amount_micros",
                "cost_micros_7d",
                "seven_day_budget_micros",
                "spend_to_budget_ratio_7d",
                "shared_budget_distribution",
                "budget_has_recommended_budget",
                "budget_recommended_amount_micros",
            ],
            missing_read_contracts=missing_read_contracts,
            blocked_claims=blocked_claims,
            source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
            evidence_ids=_unique(evidence_id for row in rows for evidence_id in row.evidence_ids),
            budget_rows=rows,
            shared_budget_distribution_rows=shared_budget_distribution_rows,
            payload_preview=payload_preview,
            action_ids=[CAMPAIGN_REVIEW_ACTION_ID] if payload_preview else [],
            next_step=(
                "Użyj tego jako kontekstu review: które kampanie mają koszt względem "
                "budżetu dziennego, czy dzielą wspólny budżet i czy Google pokazuje "
                "recommended budget. Nie skaluj budżetu bez historii zmian, impression "
                "share, celu biznesowego i akcji sprawdzonej w WILQ."
            ),
        )

    return AdsBudgetPacingReadContract(
        status="blocked",
        title="Google Ads: brak kontekstu budżetu kampanii",
        summary="WILQ nie ma jeszcze metryk budżetu kampanii z Google Ads.",
        allowed_metrics=[],
        missing_read_contracts=["campaign_budget", *missing_read_contracts],
        blocked_claims=["budget amount", "budget pacing", *blocked_claims],
        source_connectors=[GOOGLE_ADS_CONNECTOR_ID],
        evidence_ids=campaign_read_contract.evidence_ids or fallback_evidence_ids,
        budget_rows=[],
        shared_budget_distribution_rows=[],
        payload_preview=[],
        action_ids=[],
        next_step=(
            "Uruchom odczyt danych Google Ads z polami budżetu kampanii. "
            "Nie oceniaj tempa budżetu bez budget_amount_micros."
        ),
    )


def _shared_budget_distribution_rows(
    budget_rows: list[AdsBudgetPacingRow],
) -> list[AdsSharedBudgetDistributionRow]:
    grouped_rows: dict[str, list[AdsBudgetPacingRow]] = {}
    for row in budget_rows:
        if row.budget_id is None:
            continue
        grouped_rows.setdefault(row.budget_id, []).append(row)

    shared_rows: list[AdsSharedBudgetDistributionRow] = []
    for budget_id, rows in grouped_rows.items():
        if len(rows) < 2:
            continue
        total_cost_micros_7d = _sum_optional_int(
            row.cost_micros_7d for row in rows
        )
        budget_amount_micros = _first_present(row.budget_amount_micros for row in rows)
        seven_day_budget_micros = _first_present(
            row.seven_day_budget_micros for row in rows
        )
        campaign_shares = [
            AdsSharedBudgetCampaignShare(
                campaign_id=row.campaign_id,
                campaign_name=row.campaign_name,
                campaign_status=row.campaign_status,
                advertising_channel_type=row.advertising_channel_type,
                cost_micros_7d=row.cost_micros_7d,
                spend_share_7d=_ratio(row.cost_micros_7d, total_cost_micros_7d),
                evidence_ids=row.evidence_ids,
            )
            for row in sorted(rows, key=_shared_budget_campaign_sort_key)
        ]
        shared_rows.append(
            AdsSharedBudgetDistributionRow(
                budget_id=budget_id,
                budget_name=_first_present(row.budget_name for row in rows),
                campaign_count=len(rows),
                budget_amount_micros=budget_amount_micros,
                seven_day_budget_micros=seven_day_budget_micros,
                total_cost_micros_7d=total_cost_micros_7d,
                spend_to_budget_ratio_7d=_ratio(
                    total_cost_micros_7d,
                    seven_day_budget_micros,
                ),
                campaign_shares=campaign_shares,
                evidence_ids=_unique(
                    evidence_id for row in rows for evidence_id in row.evidence_ids
                ),
                blocked_claims=CAMPAIGN_REVIEW_BLOCKED_CLAIMS,
            )
        )
    return sorted(
        shared_rows,
        key=lambda row: (-(row.total_cost_micros_7d or 0), row.budget_name or row.budget_id),
    )


def _shared_budget_campaign_sort_key(row: AdsBudgetPacingRow) -> tuple[int, str]:
    return (-(row.cost_micros_7d or 0), row.campaign_name)


def _sum_optional_int(values: Iterable[int | None]) -> int | None:
    present_values = [value for value in values if value is not None]
    if not present_values:
        return None
    return sum(present_values)


def _first_present[T](values: Iterable[T | None]) -> T | None:
    return next((value for value in values if value is not None), None)


def _budget_pacing_rows(metric_facts: list[MetricFact]) -> list[AdsBudgetPacingRow]:
    grouped_facts: dict[tuple[str | None, str], list[MetricFact]] = {}
    seen_metric_keys: set[tuple[str | None, str, str]] = set()
    for fact in metric_facts:
        if fact.name not in {
            "cost_micros",
            "budget_amount_micros",
            "budget_has_recommended_budget",
            "budget_recommended_amount_micros",
        }:
            continue
        campaign_id = fact.dimensions.get("campaign_id")
        campaign_name = fact.dimensions.get("campaign_name")
        if not campaign_id and not campaign_name:
            continue
        row_key = (campaign_id, campaign_name or f"campaign {campaign_id}")
        metric_key = (campaign_id, row_key[1], fact.name)
        if metric_key in seen_metric_keys:
            continue
        seen_metric_keys.add(metric_key)
        grouped_facts.setdefault(row_key, []).append(fact)

    rows = [
        _budget_pacing_row(campaign_id, campaign_name, facts)
        for (campaign_id, campaign_name), facts in grouped_facts.items()
    ]
    return sorted(
        [row for row in rows if row.budget_amount_micros is not None],
        key=_budget_pacing_row_sort_key,
    )


def _budget_pacing_row(
    campaign_id: str | None,
    campaign_name: str,
    facts: list[MetricFact],
) -> AdsBudgetPacingRow:
    facts_by_name = {fact.name: fact for fact in facts}
    first_dimensions = next(
        (fact.dimensions for fact in facts if fact.dimensions.get("budget_id")),
        facts[0].dimensions if facts else {},
    )
    budget_amount_micros = _int_metric_value(facts_by_name.get("budget_amount_micros"))
    cost_micros_7d = _int_metric_value(facts_by_name.get("cost_micros"))
    budget_period = first_dimensions.get("budget_period")
    seven_day_budget_micros = (
        budget_amount_micros * 7
        if budget_amount_micros is not None and budget_period == "DAILY"
        else None
    )
    has_recommended_budget = _bool_metric_value(
        facts_by_name.get("budget_has_recommended_budget")
    )
    recommended_budget_amount_micros = _int_metric_value(
        facts_by_name.get("budget_recommended_amount_micros")
    )
    recommended_budget_delta_micros = (
        recommended_budget_amount_micros - budget_amount_micros
        if recommended_budget_amount_micros is not None and budget_amount_micros is not None
        else None
    )
    expected_metrics = ["budget_amount_micros", "cost_micros"]
    missing_metrics = [name for name in expected_metrics if name not in facts_by_name]
    if budget_period != "DAILY":
        missing_metrics.append("daily_budget_period_for_7d_ratio")
    payload_preview = _budget_apply_preview(
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        budget_id=first_dimensions.get("budget_id"),
        budget_name=first_dimensions.get("budget_name"),
        budget_amount_micros=budget_amount_micros,
        has_recommended_budget=has_recommended_budget,
        recommended_budget_amount_micros=recommended_budget_amount_micros,
        source_metric_names=_unique(fact.name for fact in facts),
        evidence_ids=_unique(fact.evidence_id for fact in facts),
    )
    return AdsBudgetPacingRow(
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        campaign_status=first_dimensions.get("campaign_status"),
        advertising_channel_type=first_dimensions.get("advertising_channel_type"),
        budget_id=first_dimensions.get("budget_id"),
        budget_name=first_dimensions.get("budget_name"),
        budget_period=budget_period,
        budget_status=first_dimensions.get("budget_status"),
        budget_amount_micros=budget_amount_micros,
        cost_micros_7d=cost_micros_7d,
        seven_day_budget_micros=seven_day_budget_micros,
        spend_to_budget_ratio_7d=_ratio(cost_micros_7d, seven_day_budget_micros),
        has_recommended_budget=has_recommended_budget,
        recommended_budget_amount_micros=recommended_budget_amount_micros,
        recommended_budget_delta_micros=recommended_budget_delta_micros,
        evidence_ids=_unique(fact.evidence_id for fact in facts),
        metric_facts=sorted(facts, key=lambda fact: fact.name),
        payload_preview=payload_preview,
        missing_metrics=_unique(missing_metrics),
        blocked_claims=CAMPAIGN_REVIEW_BLOCKED_CLAIMS,
    )


def _budget_apply_preview(
    *,
    campaign_id: str | None,
    campaign_name: str,
    budget_id: str | None,
    budget_name: str | None,
    budget_amount_micros: int | None,
    has_recommended_budget: bool | None,
    recommended_budget_amount_micros: int | None,
    source_metric_names: list[str],
    evidence_ids: list[str],
) -> AdsBudgetApplyPreview:
    proposed_budget_amount_micros = (
        recommended_budget_amount_micros
        if has_recommended_budget and recommended_budget_amount_micros is not None
        else None
    )
    proposed_budget_delta_micros = (
        proposed_budget_amount_micros - budget_amount_micros
        if proposed_budget_amount_micros is not None and budget_amount_micros is not None
        else None
    )
    reason = (
        "Podgląd budżetu z rekomendacji Google do sprawdzenia. "
        "WILQ nie może zmienić budżetu bez celu budżetowego, przeglądu strategii, "
        "potwierdzenia człowieka i audytu."
        if proposed_budget_amount_micros is not None
        else (
            "Podgląd budżetu do sprawdzenia. Google Ads nie zwrócił "
            "recommended budget, więc WILQ pokazuje bieżący budżet i blokuje "
            "propozycję kwoty do czasu human_budget_goal."
        )
    )
    preview_id = (
        f"budget_apply_preview_{_slug(campaign_id or campaign_name)}_"
        f"{_slug(budget_id or budget_name or 'budget')}"
    )
    return AdsBudgetApplyPreview(
        id=preview_id,
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        campaign_budget_id=budget_id,
        campaign_budget_name=budget_name,
        current_budget_amount_micros=budget_amount_micros,
        proposed_budget_amount_micros=proposed_budget_amount_micros,
        proposed_budget_delta_micros=proposed_budget_delta_micros,
        reason=reason,
        evidence_ids=evidence_ids,
        source_metric_names=source_metric_names,
        required_validation=CAMPAIGN_BUDGET_APPLY_PREVIEW_REQUIRED_VALIDATION,
        blocked_claims=CAMPAIGN_REVIEW_BLOCKED_CLAIMS,
        safety_review=AdsBudgetApplySafetyReview.model_validate(
            budget_apply_safety_review(
                preview_id=preview_id,
                current_budget_amount_micros=budget_amount_micros,
                proposed_budget_amount_micros=proposed_budget_amount_micros,
                proposed_budget_delta_micros=proposed_budget_delta_micros,
                evidence_ids=evidence_ids,
            )
        ),
    )


def _budget_pacing_row_sort_key(row: AdsBudgetPacingRow) -> tuple[float, int, str]:
    ratio = row.spend_to_budget_ratio_7d if row.spend_to_budget_ratio_7d is not None else -1
    return (-ratio, -(row.cost_micros_7d or 0), row.campaign_name)


def _remove_missing_contract_names(
    missing_read_contracts: list[str],
    *contract_names: str,
) -> list[str]:
    removals = set(contract_names)
    return [contract for contract in missing_read_contracts if contract not in removals]


def _ratio(
    numerator: float | int | None,
    denominator: float | int | None,
) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def _int_metric_value(fact: MetricFact | None) -> int | None:
    if fact is None:
        return None
    if isinstance(fact.value, str):
        try:
            return int(float(fact.value))
        except ValueError:
            return None
    return int(fact.value)


def _bool_metric_value(fact: MetricFact | None) -> bool | None:
    if fact is None:
        return None
    if isinstance(fact.value, str):
        return fact.value.lower() in {"1", "true", "yes"}
    return bool(fact.value)


def _slug(value: str) -> str:
    normalized = "".join(character.lower() if character.isalnum() else "_" for character in value)
    return "_".join(part for part in normalized.split("_") if part)[:80] or "unknown"


def _unique(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in unique_values:
            unique_values.append(text)
    return unique_values
