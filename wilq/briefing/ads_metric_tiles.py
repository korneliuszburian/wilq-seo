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


def budget_context_metric_tiles(
    decision: AdsDecisionItem,
    currency_code: str | None,
) -> dict[str, int | float | str]:
    budget_tiles: dict[str, int | float | str | None] = {
        "budżety": len(decision.budget_rows),
        "podgląd budżetu": len(decision.budget_apply_preview),
        "koszt 7 dni": format_money_micros(
            sum_attr(decision.budget_rows, "cost_micros_7d"),
            currency_code,
        ),
    }
    if decision.shared_budget_distribution_rows:
        budget_tiles["wspólne budżety"] = len(decision.shared_budget_distribution_rows)
    return clean_metric_tiles(budget_tiles)


def recommendations_metric_tiles(
    decision: AdsDecisionItem,
) -> dict[str, int | float | str]:
    rows_with_impact = sum(1 for row in decision.recommendation_rows if row.impact_available)
    urgent_rows = sum(1 for row in decision.recommendation_rows if row.review_priority == "pilne")
    high_rows = sum(1 for row in decision.recommendation_rows if row.review_priority == "wysokie")
    return clean_metric_tiles(
        {
            "rekomendacje": len(decision.recommendation_rows),
            "pilne": urgent_rows,
            "wysokie": high_rows,
            "podgląd wpływu": rows_with_impact,
            "podgląd akcji": len(decision.recommendation_apply_preview),
        }
    )


def search_term_ngram_metric_tiles(
    decision: AdsDecisionItem,
    currency_code: str | None,
) -> dict[str, int | float | str]:
    rows = decision.search_term_ngram_rows
    rows_with_clicks = sum(1 for row in rows if (row.clicks or 0) > 0)
    max_source_terms = max((row.source_search_term_count for row in rows), default=0)
    max_clicks = max((row.clicks or 0 for row in rows), default=0)
    max_cost_micros = max((row.cost_micros or 0 for row in rows), default=0)
    ngram_tiles: dict[str, int | float | str | None] = {
        "n-gramy": decision.metric_tiles.get("n-gramy", len(rows)),
        "pokazane": len(rows),
        "z kliknięciami": rows_with_clicks,
        "max query/temat": max_source_terms,
        "top kliknięcia": max_clicks,
    }
    if max_cost_micros:
        ngram_tiles["top koszt"] = format_money_micros(max_cost_micros, currency_code)
    return clean_metric_tiles(ngram_tiles)


def impression_share_metric_tiles(
    decision: AdsDecisionItem,
) -> dict[str, int | float | str]:
    return clean_metric_tiles(
        {
            "kampanie": len(decision.impression_share_rows),
            "utrata przez budżet": sum(
                1
                for row in decision.impression_share_rows
                if row.search_budget_lost_impression_share is not None
            ),
        }
    )


def search_terms_metric_tiles(
    decision: AdsDecisionItem,
    currency_code: str | None,
) -> dict[str, int | float | str]:
    return clean_metric_tiles(
        {
            "zapytania": len(decision.search_term_rows),
            "kliknięcia": sum_attr(decision.search_term_rows, "clicks"),
            "koszt": format_money_micros(
                sum_attr(decision.search_term_rows, "cost_micros"),
                currency_code,
            ),
        }
    )


def search_term_safety_metric_tiles(
    decision: AdsDecisionItem,
    currency_code: str | None,
) -> dict[str, int | float | str]:
    return clean_metric_tiles(
        {
            "90 dni": len(decision.search_term_safety_rows),
            "kliknięcia": sum_attr(decision.search_term_safety_rows, "clicks_90d"),
            "koszt": format_money_micros(
                sum_attr(decision.search_term_safety_rows, "cost_micros_90d"),
                currency_code,
            ),
        }
    )


def negative_keyword_safety_metric_tiles(
    decision: AdsDecisionItem,
) -> dict[str, int | float | str]:
    return clean_metric_tiles(
        {
            "propozycje": len(decision.negative_keyword_candidates),
            "pilne": sum(
                1
                for candidate in decision.negative_keyword_candidates
                if candidate.review_priority == "pilne"
            ),
            "wysokie": sum(
                1
                for candidate in decision.negative_keyword_candidates
                if candidate.review_priority == "wysokie"
            ),
            "podgląd akcji": len(decision.negative_keyword_payload_preview),
            "kontekst słów": len(decision.keyword_match_context_rows),
        }
    )


def custom_segments_metric_tiles(
    decision: AdsDecisionItem,
) -> dict[str, int | float | str]:
    return clean_metric_tiles(
        {
            "segmenty": len(decision.custom_segment_candidates),
            "pilne": sum(
                1
                for candidate in decision.custom_segment_candidates
                if candidate.review_priority == "pilne"
            ),
            "wysokie": sum(
                1
                for candidate in decision.custom_segment_candidates
                if candidate.review_priority == "wysokie"
            ),
            "podgląd akcji": len(decision.custom_segment_payload_preview),
            "źródłowe zapytania": len(decision.search_term_rows),
            "KP ideas": len(decision.keyword_planner_idea_rows),
        }
    )


def change_history_metric_tiles(
    decision: AdsDecisionItem,
) -> dict[str, int | float | str]:
    return clean_metric_tiles(
        {
            "zmiany": len(decision.change_history_rows),
            "kampanie": sum(
                1 for row in decision.change_history_rows if row.campaign_id is not None
            ),
        }
    )


def safety_blocker_metric_tiles(
    decision: AdsDecisionItem,
) -> dict[str, int | float | str]:
    return clean_metric_tiles(
        {
            "akcje do sprawdzenia": len(decision.action_ids),
            "blokady": len(decision.blocked_claims),
        }
    )
