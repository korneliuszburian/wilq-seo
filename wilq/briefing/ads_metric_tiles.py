"""Small decision metric-tile builders for Ads diagnostics."""

from __future__ import annotations

from wilq.briefing.ads_metric_utils import (
    clean_metric_tiles,
    format_money_micros,
    round_metric,
    sum_attr,
)
from wilq.schemas import AdsDecisionItem


def campaign_activity_metric_tiles(
    decision: AdsDecisionItem,
    currency_code: str | None,
) -> dict[str, int | float | str]:
    urgent_rows = sum(1 for row in decision.campaign_rows if row.review_priority == "pilne")
    high_rows = sum(1 for row in decision.campaign_rows if row.review_priority == "wysokie")
    target_context_rows = sum(
        1 for row in decision.campaign_rows if row.target_status != "no_target"
    )
    campaign_tiles: dict[str, int | float | str | None] = {
        "kampanie": len(decision.campaign_rows),
        "pilne": urgent_rows,
        "wysokie": high_rows,
        "kliknięcia": sum_attr(decision.campaign_rows, "clicks"),
        "wyświetlenia": sum_attr(decision.campaign_rows, "impressions"),
        "koszt": format_money_micros(
            sum_attr(decision.campaign_rows, "cost_micros"),
            currency_code,
        ),
        "konwersje": round_metric(sum_attr(decision.campaign_rows, "conversions")),
    }
    if target_context_rows:
        campaign_tiles["targety"] = target_context_rows
    return clean_metric_tiles(campaign_tiles)


def campaign_triage_metric_tiles(
    decision: AdsDecisionItem,
) -> dict[str, int | float | str]:
    urgent_rows = sum(
        1 for row in decision.campaign_triage_rows if row.review_priority == "pilne"
    )
    high_rows = sum(
        1 for row in decision.campaign_triage_rows if row.review_priority == "wysokie"
    )
    recommendation_count = sum(
        row.recommendation_count for row in decision.campaign_triage_rows
    )
    preview_count = sum(
        1 for row in decision.campaign_triage_rows if row.has_budget_apply_preview
    ) + sum(
        1 for row in decision.campaign_triage_rows if row.has_recommendation_apply_preview
    )
    return clean_metric_tiles(
        {
            "kampanie": len(decision.campaign_triage_rows),
            "pilne": urgent_rows,
            "wysokie": high_rows,
            "rekomendacje": recommendation_count,
            "podglądy": preview_count,
        }
    )
