from __future__ import annotations

from typing import Literal

CampaignReviewPriority = Literal["pilne", "wysokie", "normalne", "niski sygnał"]

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
    if is_draft_campaign_name(campaign_name):
        signals.append("nazwa wygląda jak draft/NIE URUCHAMIAĆ")
    signal_text = ", ".join(signals) or "brak aktywności w bieżącym evidence"
    return (
        f"Kolejność review kampanii wynika z faktów: {signal_text}. "
        "To nie jest werdykt wasted budget, CPA ani ROAS; przed decyzją potrzebny "
        "jest review celu, jakości konwersji, budżetu i search terms."
    )


def campaign_review_gates(
    *,
    campaign_name: str,
    advertising_channel_type: str | None,
    cost_micros: int | None,
    conversions: float | None,
) -> list[str]:
    gates = list(CAMPAIGN_REVIEW_HUMAN_GATES)
    if (cost_micros or 0) > 0 and not conversions:
        gates.append("review_conversion_tracking")
    if advertising_channel_type == "PERFORMANCE_MAX":
        gates.append("review_pmax_asset_feed_context")
    if is_draft_campaign_name(campaign_name):
        gates.append("review_draft_campaign_status")
    return _unique(gates)


def is_draft_campaign_name(campaign_name: str) -> bool:
    normalized_name = campaign_name.upper()
    return "DRAFT" in normalized_name or "NIE URUCHAMIAC" in normalized_name


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
