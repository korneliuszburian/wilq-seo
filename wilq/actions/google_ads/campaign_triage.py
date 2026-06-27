from __future__ import annotations

from typing import Literal, TypedDict

CampaignReviewPriority = Literal["pilne", "wysokie", "normalne", "niski sygnał"]
CampaignTargetStatus = Literal[
    "within_target",
    "outside_target",
    "spend_without_conversions",
    "insufficient_data",
    "no_target",
]


class CampaignTargetContext(TypedDict):
    target_status: CampaignTargetStatus
    target_status_label: str
    target_roas: float | None
    roas: float | None
    roas_vs_target: float | None
    target_cpa_micros: int | None
    cost_per_conversion_micros: float | None
    cpa_vs_target_micros: float | None

CAMPAIGN_REVIEW_HUMAN_GATES = [
    "review_campaign_goal",
    "review_conversion_quality",
    "review_budget_context",
    "review_search_terms_before_budget_decision",
    "human_strategy_review",
]


def campaign_review_score(
    *,
    campaign_name: str,
    advertising_channel_type: str | None,
    clicks: int | None,
    impressions: int | None,
    cost_micros: int | None,
    conversions: float | None,
    missing_metrics: list[str],
    target_status: CampaignTargetStatus = "no_target",
) -> int:
    if missing_metrics:
        return 10
    score = 0
    if (cost_micros or 0) > 0:
        score += 25
    if (clicks or 0) >= 20:
        score += 20
    elif (clicks or 0) > 0:
        score += 10
    if (impressions or 0) >= 500:
        score += 10
    if (cost_micros or 0) > 0 and not conversions:
        score += 25
    elif (conversions or 0) > 0:
        score += 15
    if advertising_channel_type == "PERFORMANCE_MAX":
        score += 10
    if is_draft_campaign_name(campaign_name) and (
        (cost_micros or 0) > 0 or (clicks or 0) > 0 or (impressions or 0) > 0
    ):
        score += 15
    if target_status == "outside_target":
        score += 15
    elif target_status == "spend_without_conversions":
        score += 10
    elif target_status == "insufficient_data":
        score += 5
    return min(100, score)


def campaign_review_priority(review_score: int) -> CampaignReviewPriority:
    if review_score >= 70:
        return "pilne"
    if review_score >= 45:
        return "wysokie"
    if review_score >= 15:
        return "normalne"
    return "niski sygnał"


def campaign_review_reason(
    *,
    campaign_name: str,
    advertising_channel_type: str | None,
    clicks: int | None,
    impressions: int | None,
    cost_micros: int | None,
    conversions: float | None,
    missing_metrics: list[str],
    target_status: CampaignTargetStatus = "no_target",
    target_status_label: str | None = None,
) -> str:
    if missing_metrics:
        return (
            "Kampania ma niepełne metryki kampanii: "
            f"{', '.join(missing_metrics)}. To jest blocker danych, nie "
            "rekomendacja optymalizacyjna."
        )
    signals: list[str] = []
    if (cost_micros or 0) > 0:
        signals.append(f"koszt={_format_micros(cost_micros)}")
    if (clicks or 0) > 0:
        signals.append(f"kliknięcia={clicks}")
    if (impressions or 0) > 0:
        signals.append(f"wyświetlenia={impressions}")
    if conversions is not None and conversions > 0:
        signals.append(f"konwersje={_format_float(conversions)}")
    elif (cost_micros or 0) > 0:
        signals.append("koszt bez konwersji w bieżącym evidence")
    if advertising_channel_type:
        signals.append(f"typ={advertising_channel_type}")
    if target_status != "no_target" and target_status_label:
        signals.append(f"target={target_status_label}")
    if is_draft_campaign_name(campaign_name):
        signals.append("nazwa wygląda jak draft/NIE URUCHAMIAĆ")
    signal_text = ", ".join(signals) or "brak aktywności w bieżącym evidence"
    return (
        f"Kolejność oceny kampanii wynika z faktów: {signal_text}. "
        "To nie jest werdykt przepalonego budżetu, CPA ani zwrot z reklam; przed decyzją potrzebna "
        "jest ocena celu, jakości konwersji, budżetu i wyszukiwanych haseł."
    )


def campaign_review_gates(
    *,
    campaign_name: str,
    advertising_channel_type: str | None,
    cost_micros: int | None,
    conversions: float | None,
    target_status: CampaignTargetStatus = "no_target",
) -> list[str]:
    gates = list(CAMPAIGN_REVIEW_HUMAN_GATES)
    if (cost_micros or 0) > 0 and not conversions:
        gates.append("review_conversion_tracking")
    if advertising_channel_type == "PERFORMANCE_MAX":
        gates.append("review_pmax_asset_feed_context")
    if target_status != "no_target":
        gates.append("review_target_context")
    if target_status in {"outside_target", "spend_without_conversions"}:
        gates.append("review_target_gap_before_budget_decision")
    if is_draft_campaign_name(campaign_name):
        gates.append("review_draft_campaign_status")
    return _unique(gates)


def campaign_target_context(
    *,
    cost_micros: int | None,
    conversions: float | None,
    conversion_value: float | None,
    target_roas: float | None,
    target_cpa_micros: int | None,
) -> CampaignTargetContext:
    cost_per_conversion_micros = _ratio(cost_micros, conversions)
    roas = _ratio(conversion_value, _micros_to_account_units(cost_micros))
    cpa_vs_target_micros = _difference(cost_per_conversion_micros, target_cpa_micros)
    roas_vs_target = _difference(roas, target_roas)

    if target_cpa_micros is not None:
        if cost_per_conversion_micros is not None:
            if cost_per_conversion_micros <= target_cpa_micros:
                status: CampaignTargetStatus = "within_target"
                label = "koszt pozyskania celu w granicy celu"
            else:
                status = "outside_target"
                label = "koszt pozyskania celu powyżej celu"
        elif (cost_micros or 0) > 0 and not conversions:
            status = "spend_without_conversions"
            label = "koszt bez konwersji"
        else:
            status = "insufficient_data"
            label = "brak CPA do porównania"
    elif target_roas is not None:
        if roas is not None:
            if roas >= target_roas:
                status = "within_target"
                label = "zwrot z reklam w granicy celu"
            else:
                status = "outside_target"
                label = "zwrot z reklam poniżej celu"
        elif (cost_micros or 0) > 0 and not conversion_value:
            status = "spend_without_conversions"
            label = "koszt bez wartości konwersji"
        else:
            status = "insufficient_data"
            label = "brak zwrotu z reklam do porównania"
    else:
        status = "no_target"
        label = "brak celu"

    return {
        "target_status": status,
        "target_status_label": label,
        "target_roas": target_roas,
        "roas": roas,
        "roas_vs_target": roas_vs_target,
        "target_cpa_micros": target_cpa_micros,
        "cost_per_conversion_micros": cost_per_conversion_micros,
        "cpa_vs_target_micros": cpa_vs_target_micros,
    }


def is_draft_campaign_name(campaign_name: str) -> bool:
    normalized_name = campaign_name.upper()
    return "DRAFT" in normalized_name or "NIE URUCHAMIAC" in normalized_name


def _ratio(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def _difference(left: float | int | None, right: float | int | None) -> float | None:
    if left is None or right is None:
        return None
    return round(float(left) - float(right), 6)


def _micros_to_account_units(value: int | None) -> float | None:
    if value is None:
        return None
    return value / 1_000_000


def _format_micros(value: int | None) -> str:
    if value is None:
        return "0"
    return f"{value / 1_000_000:g}"


def _format_float(value: float) -> str:
    return f"{value:g}"


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values
