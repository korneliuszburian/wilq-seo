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


def business_context_metric_tiles(
    decision: AdsDecisionItem,
) -> dict[str, int | float | str]:
    return clean_metric_tiles(
        {
            "braki": len(decision.missing_read_contracts),
            "blokady": len(decision.blocked_claims),
            "ustawione pola": len(decision.allowed_metrics),
            "warunki sprawdzenia": len(decision.operator_review_gates),
            "polityki": decision.metric_tiles.get("polityki", 0),
        }
    )


def derived_kpi_metric_tiles(
    decision: AdsDecisionItem,
) -> dict[str, int | float | str]:
    rows_with_cpa = sum(
        1 for row in decision.derived_kpi_rows if row.cost_per_conversion_micros is not None
    )
    rows_with_roas = sum(1 for row in decision.derived_kpi_rows if row.roas is not None)
    rows_with_target_context = sum(
        1
        for row in decision.derived_kpi_rows
        if row.roas_vs_target is not None or row.cpa_vs_target_micros is not None
    )
    tiles: dict[str, int | float | str | None] = {
        "kampanie": len(decision.derived_kpi_rows),
        "wiersze kosztu pozyskania celu": rows_with_cpa,
        "wiersze zwrotu z reklam": rows_with_roas,
    }
    if rows_with_target_context:
        tiles["targety"] = rows_with_target_context
    rows_within_target = sum(
        1 for row in decision.derived_kpi_rows if row.target_status == "within_target"
    )
    rows_outside_target = sum(
        1 for row in decision.derived_kpi_rows if row.target_status == "outside_target"
    )
    rows_with_spend_without_conversions = sum(
        1
        for row in decision.derived_kpi_rows
        if row.target_status == "spend_without_conversions"
    )
    if rows_within_target:
        tiles["w celu"] = rows_within_target
    if rows_outside_target:
        tiles["poza celem"] = rows_outside_target
    if rows_with_spend_without_conversions:
        tiles["koszt bez konw."] = rows_with_spend_without_conversions
    return clean_metric_tiles(tiles)
