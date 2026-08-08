"""Google Ads search-term and keyword response summaries."""
from __future__ import annotations

from typing import Any

from wilq.connectors.google_ads.ad_landing_pages import (
    ADS_DEMAND_PERIOD,
    ADS_LANDING_MAPPING_STATUS,
    ADS_LANDING_RESOLVED,
    ADS_SEARCH_TERM_PAYLOAD_STATUS,
    AdsLandingInventory,
    search_term_landing_dimensions,
    search_term_landing_dimensions_from_inventory,
    strict_search_stream_rows,
)
from wilq.connectors.vendor import VendorMetricFact
from wilq.credentials.runtime import variable_value

from .campaigns import (
    _campaign_dimensions,
)
from .shared import (
    _bool_metric,
    _clip_dimension,
    _float_metric,
    _int_metric,
    _optional_int_metric,
    _search_stream_rows,
)

KEYWORD_PLANNER_IDEA_SOURCE_TERM_LIMIT = 10

KEYWORD_PLANNER_IDEA_RESULT_LIMIT = 20

KEYWORD_PLANNER_DEFAULT_LANGUAGE_RESOURCE = "languageConstants/1045"

KEYWORD_PLANNER_DEFAULT_GEO_TARGET_RESOURCE = "geoTargetConstants/2616"

KEYWORD_PLANNER_NETWORK = "GOOGLE_SEARCH_AND_PARTNERS"

SEARCH_TERM_SUMMARY_QUERY = """
SELECT
  campaign.id,
  campaign.name,
  ad_group.id,
  ad_group.name,
  search_term_view.search_term,
  search_term_view.status,
  metrics.clicks,
  metrics.impressions,
  metrics.cost_micros,
  metrics.conversions,
  metrics.conversions_value
FROM search_term_view
WHERE segments.date DURING LAST_30_DAYS
  AND metrics.clicks > 0
LIMIT 50
""".strip()

SEARCH_TERM_SAFETY_LOOKBACK_DAYS = 90

SEARCH_TERM_SAFETY_QUERY_TEMPLATE = """
SELECT
  campaign.id,
  campaign.name,
  ad_group.id,
  ad_group.name,
  search_term_view.search_term,
  search_term_view.status,
  metrics.clicks,
  metrics.impressions,
  metrics.cost_micros,
  metrics.conversions,
  metrics.conversions_value
FROM search_term_view
WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
LIMIT 200
""".strip()

KEYWORD_MATCH_CONTEXT_QUERY = """
SELECT
  campaign.id,
  campaign.name,
  ad_group.id,
  ad_group.name,
  ad_group_criterion.criterion_id,
  ad_group_criterion.status,
  ad_group_criterion.negative,
  ad_group_criterion.keyword.text,
  ad_group_criterion.keyword.match_type
FROM ad_group_criterion
WHERE ad_group_criterion.type = 'KEYWORD'
  AND campaign.status != 'REMOVED'
  AND ad_group_criterion.status != 'REMOVED'
LIMIT 500
""".strip()

def _keyword_planner_seed_terms(search_term_facts: list[VendorMetricFact]) -> list[str]:
    grouped: dict[str, dict[str, int]] = {}
    for fact in search_term_facts:
        if fact.name not in {
            "search_term_clicks",
            "search_term_impressions",
            "search_term_cost_micros",
        }:
            continue
        search_term = fact.dimensions.get("search_term")
        if not search_term:
            continue
        normalized = " ".join(search_term.split())
        if len(normalized) < 3:
            continue
        row = grouped.setdefault(
            normalized,
            {"clicks": 0, "impressions": 0, "cost_micros": 0},
        )
        if fact.name == "search_term_clicks":
            row["clicks"] = _int_metric(fact.value)
        elif fact.name == "search_term_impressions":
            row["impressions"] = _int_metric(fact.value)
        elif fact.name == "search_term_cost_micros":
            row["cost_micros"] = _int_metric(fact.value)
    return [
        term
        for term, _metrics in sorted(
            grouped.items(),
            key=lambda item: (
                -item[1]["cost_micros"],
                -item[1]["clicks"],
                -item[1]["impressions"],
                item[0],
            ),
        )[:KEYWORD_PLANNER_IDEA_SOURCE_TERM_LIMIT]
    ]

def _keyword_planner_language_resource() -> str:
    configured = variable_value("GOOGLE_ADS_KEYWORD_PLANNER_LANGUAGE_RESOURCE")
    return configured or KEYWORD_PLANNER_DEFAULT_LANGUAGE_RESOURCE

def _keyword_planner_geo_target_resource() -> str:
    configured = variable_value("GOOGLE_ADS_KEYWORD_PLANNER_GEO_TARGET_RESOURCE")
    return configured or KEYWORD_PLANNER_DEFAULT_GEO_TARGET_RESOURCE

def _summarize_keyword_planner_response(
    payload: Any,
    *,
    seed_terms: list[str],
    language_resource: str,
    geo_target_resource: str,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        results = []
    metric_facts: list[VendorMetricFact] = []
    max_avg_monthly_searches = 0
    competition_values: set[str] = set()
    seed_terms_label = _keyword_planner_seed_terms_label(seed_terms)
    for result in results:
        if not isinstance(result, dict):
            continue
        idea_text = result.get("text")
        if not isinstance(idea_text, str) or not idea_text.strip():
            continue
        metrics = result.get("keywordIdeaMetrics", result.get("keyword_idea_metrics", {}))
        if not isinstance(metrics, dict):
            metrics = {}
        avg_monthly_searches = _int_metric(
            metrics.get(
                "avgMonthlySearches",
                metrics.get("avg_monthly_searches"),
            )
        )
        competition = metrics.get("competition")
        if not isinstance(competition, str):
            competition = None
        competition_index = _optional_int_metric(
            metrics.get("competitionIndex", metrics.get("competition_index"))
        )
        low_bid_micros = _optional_int_metric(
            metrics.get(
                "lowTopOfPageBidMicros",
                metrics.get("low_top_of_page_bid_micros"),
            )
        )
        high_bid_micros = _optional_int_metric(
            metrics.get(
                "highTopOfPageBidMicros",
                metrics.get("high_top_of_page_bid_micros"),
            )
        )
        dimensions = {
            "keyword_idea_text": _clip_dimension(idea_text),
            "seed_terms": seed_terms_label,
            "seed_terms_count": str(len(seed_terms)),
            "language_resource": language_resource,
            "geo_target_resource": geo_target_resource,
        }
        if competition:
            dimensions["competition"] = competition
            competition_values.add(competition)
        max_avg_monthly_searches = max(max_avg_monthly_searches, avg_monthly_searches)
        metric_facts.extend(
            [
                VendorMetricFact(
                    "keyword_planner_idea_available",
                    1,
                    dimensions,
                    period="keyword_planner",
                ),
                VendorMetricFact(
                    "keyword_planner_avg_monthly_searches",
                    avg_monthly_searches,
                    dimensions,
                    period="keyword_planner",
                ),
            ]
        )
        if competition_index is not None:
            metric_facts.append(
                VendorMetricFact(
                    "keyword_planner_competition_index",
                    competition_index,
                    dimensions,
                    period="keyword_planner",
                )
            )
        if low_bid_micros is not None:
            metric_facts.append(
                VendorMetricFact(
                    "keyword_planner_low_top_of_page_bid_micros",
                    low_bid_micros,
                    dimensions,
                    period="keyword_planner",
                )
            )
        if high_bid_micros is not None:
            metric_facts.append(
                VendorMetricFact(
                    "keyword_planner_high_top_of_page_bid_micros",
                    high_bid_micros,
                    dimensions,
                    period="keyword_planner",
                )
            )
    return (
        {
            "keyword_planner_status": "ready",
            "keyword_planner_seed_term_count": len(seed_terms),
            "keyword_planner_idea_count": sum(
                1 for fact in metric_facts if fact.name == "keyword_planner_idea_available"
            ),
            "keyword_planner_avg_monthly_searches_max": max_avg_monthly_searches,
            "keyword_planner_competition_values": ",".join(sorted(competition_values)),
            "keyword_planner_language_resource": language_resource,
            "keyword_planner_geo_target_resource": geo_target_resource,
            "keyword_planner_network": KEYWORD_PLANNER_NETWORK,
        },
        metric_facts,
    )

def _keyword_planner_seed_terms_label(seed_terms: list[str]) -> str:
    return _clip_dimension(", ".join(seed_terms[:5]))

def _summarize_search_term_response(
    payload: Any,
    *,
    landing_inventory: AdsLandingInventory | None = None,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows, payload_valid = strict_search_stream_rows(payload)
    clicks = 0
    impressions = 0
    cost_micros = 0
    conversions = 0.0
    conversion_value = 0.0
    metric_facts: list[VendorMetricFact] = []
    mapped_landing_rows = 0
    blocked_landing_rows = 0
    for row in rows:
        metrics = row.get("metrics", {})
        row_clicks = _int_metric(metrics.get("clicks"))
        row_impressions = _int_metric(metrics.get("impressions"))
        row_cost_micros = _int_metric(metrics.get("costMicros", metrics.get("cost_micros")))
        row_conversions = _float_metric(metrics.get("conversions"))
        row_conversion_value = _float_metric(
            metrics.get("conversionsValue", metrics.get("conversions_value"))
        )
        clicks += row_clicks
        impressions += row_impressions
        cost_micros += row_cost_micros
        conversions += row_conversions
        conversion_value += row_conversion_value
        dimensions = _search_term_dimensions(row)
        dimensions.update(search_term_landing_dimensions(row))
        if (
            landing_inventory
            and dimensions.get(ADS_LANDING_MAPPING_STATUS) != ADS_LANDING_RESOLVED
        ):
            dimensions.update(
                search_term_landing_dimensions_from_inventory(row, landing_inventory)
            )
        if dimensions.get(ADS_LANDING_MAPPING_STATUS) == ADS_LANDING_RESOLVED:
            mapped_landing_rows += 1
        else:
            blocked_landing_rows += 1
        if dimensions:
            metric_facts.extend(
                [
                    VendorMetricFact(
                        "search_term_clicks", row_clicks, dimensions, ADS_DEMAND_PERIOD
                    ),
                    VendorMetricFact(
                        "search_term_impressions",
                        row_impressions,
                        dimensions,
                        ADS_DEMAND_PERIOD,
                    ),
                    VendorMetricFact(
                        "search_term_cost_micros",
                        row_cost_micros,
                        dimensions,
                        ADS_DEMAND_PERIOD,
                    ),
                    VendorMetricFact(
                        "search_term_conversions",
                        row_conversions,
                        dimensions,
                        ADS_DEMAND_PERIOD,
                    ),
                    VendorMetricFact(
                        "search_term_conversion_value",
                        row_conversion_value,
                        dimensions,
                        ADS_DEMAND_PERIOD,
                    ),
                ]
            )
    metric_facts.append(
        VendorMetricFact(
            ADS_SEARCH_TERM_PAYLOAD_STATUS,
            "ready" if payload_valid else "blocked",
            period=ADS_DEMAND_PERIOD,
        )
    )
    return (
        {
            "search_term_query": "search_term_last_30_days",
            "search_term_row_count": len(rows),
            "search_term_clicks": clicks,
            "search_term_impressions": impressions,
            "search_term_cost_micros": cost_micros,
            "search_term_conversions": conversions,
            "search_term_conversion_value": conversion_value,
            ADS_SEARCH_TERM_PAYLOAD_STATUS: "ready" if payload_valid else "blocked",
            "search_term_landing_mapped_row_count": mapped_landing_rows,
            "search_term_landing_blocked_row_count": blocked_landing_rows,
        },
        metric_facts,
    )

def _summarize_search_term_safety_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    clicks = 0
    impressions = 0
    cost_micros = 0
    conversions = 0.0
    conversion_value = 0.0
    metric_facts: list[VendorMetricFact] = []
    for row in rows:
        metrics = row.get("metrics", {})
        row_clicks = _int_metric(metrics.get("clicks"))
        row_impressions = _int_metric(metrics.get("impressions"))
        row_cost_micros = _int_metric(metrics.get("costMicros", metrics.get("cost_micros")))
        row_conversions = _float_metric(metrics.get("conversions"))
        row_conversion_value = _float_metric(
            metrics.get("conversionsValue", metrics.get("conversions_value"))
        )
        clicks += row_clicks
        impressions += row_impressions
        cost_micros += row_cost_micros
        conversions += row_conversions
        conversion_value += row_conversion_value
        dimensions = _search_term_dimensions(row)
        if dimensions:
            metric_facts.extend(
                [
                    VendorMetricFact(
                        "search_term_90d_clicks",
                        row_clicks,
                        dimensions,
                        period="search_term_safety_90d",
                    ),
                    VendorMetricFact(
                        "search_term_90d_impressions",
                        row_impressions,
                        dimensions,
                        period="search_term_safety_90d",
                    ),
                    VendorMetricFact(
                        "search_term_90d_cost_micros",
                        row_cost_micros,
                        dimensions,
                        period="search_term_safety_90d",
                    ),
                    VendorMetricFact(
                        "search_term_90d_conversions",
                        row_conversions,
                        dimensions,
                        period="search_term_safety_90d",
                    ),
                    VendorMetricFact(
                        "search_term_90d_conversion_value",
                        row_conversion_value,
                        dimensions,
                        period="search_term_safety_90d",
                    ),
                ]
            )
    return (
        {
            "search_term_safety_query": (
                f"search_term_last_{SEARCH_TERM_SAFETY_LOOKBACK_DAYS}_days"
            ),
            "search_term_safety_row_count": len(rows),
            "search_term_safety_clicks": clicks,
            "search_term_safety_impressions": impressions,
            "search_term_safety_cost_micros": cost_micros,
            "search_term_safety_conversions": conversions,
            "search_term_safety_conversion_value": conversion_value,
        },
        metric_facts,
    )

def _summarize_keyword_match_context_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    metric_facts: list[VendorMetricFact] = []
    keyword_texts: set[str] = set()
    match_types: set[str] = set()
    negative_count = 0
    for row in rows:
        dimensions = _keyword_match_context_dimensions(row)
        keyword_text = dimensions.get("keyword_text")
        match_type = dimensions.get("keyword_match_type")
        if keyword_text:
            keyword_texts.add(keyword_text)
        if match_type:
            match_types.add(match_type)
        negative = dimensions.get("keyword_negative") == "true"
        if negative:
            negative_count += 1
        if dimensions:
            metric_facts.extend(
                [
                    VendorMetricFact(
                        "keyword_match_context_available",
                        1,
                        dimensions,
                        period="keyword_match_context",
                    ),
                    VendorMetricFact(
                        "keyword_match_type",
                        match_type or "UNKNOWN",
                        dimensions,
                        period="keyword_match_context",
                    ),
                    VendorMetricFact(
                        "keyword_match_context_negative",
                        1 if negative else 0,
                        dimensions,
                        period="keyword_match_context",
                    ),
                ]
            )
    return (
        {
            "keyword_match_context_query": "ad_group_criterion_keyword_context",
            "keyword_match_context_row_count": len(rows),
            "keyword_match_context_keyword_count": len(keyword_texts),
            "keyword_match_context_negative_count": negative_count,
            "keyword_match_context_match_types": ",".join(sorted(match_types)),
        },
        metric_facts,
    )

def _search_term_dimensions(row: dict[str, Any]) -> dict[str, str]:
    dimensions = _campaign_dimensions(row.get("campaign", {}))
    ad_group = row.get("adGroup", row.get("ad_group", {}))
    if isinstance(ad_group, dict):
        ad_group_id = ad_group.get("id")
        if ad_group_id is not None:
            dimensions["ad_group_id"] = str(ad_group_id)
        ad_group_name = ad_group.get("name")
        if isinstance(ad_group_name, str) and ad_group_name:
            dimensions["ad_group_name"] = ad_group_name
    search_term_view = row.get("searchTermView", row.get("search_term_view", {}))
    if isinstance(search_term_view, dict):
        search_term = search_term_view.get("searchTerm", search_term_view.get("search_term"))
        if isinstance(search_term, str) and search_term:
            dimensions["search_term"] = search_term
        status = search_term_view.get("status")
        if isinstance(status, str) and status:
            dimensions["search_term_status"] = status
    return dimensions

def _keyword_match_context_dimensions(row: dict[str, Any]) -> dict[str, str]:
    dimensions = _campaign_dimensions(row.get("campaign", {}))
    ad_group = row.get("adGroup", row.get("ad_group", {}))
    if isinstance(ad_group, dict):
        ad_group_id = ad_group.get("id")
        if ad_group_id is not None:
            dimensions["ad_group_id"] = str(ad_group_id)
        ad_group_name = ad_group.get("name")
        if isinstance(ad_group_name, str) and ad_group_name:
            dimensions["ad_group_name"] = ad_group_name
    criterion = row.get("adGroupCriterion", row.get("ad_group_criterion", {}))
    if not isinstance(criterion, dict):
        return dimensions
    criterion_id = criterion.get("criterionId", criterion.get("criterion_id"))
    if criterion_id is not None:
        dimensions["criterion_id"] = str(criterion_id)
    status = criterion.get("status")
    if isinstance(status, str) and status:
        dimensions["criterion_status"] = status
    negative = _bool_metric(criterion.get("negative"))
    dimensions["keyword_negative"] = "true" if negative else "false"
    keyword = criterion.get("keyword", {})
    if isinstance(keyword, dict):
        keyword_text = keyword.get("text")
        if isinstance(keyword_text, str) and keyword_text:
            dimensions["keyword_text"] = keyword_text
        match_type = keyword.get("matchType", keyword.get("match_type"))
        if isinstance(match_type, str) and match_type:
            dimensions["keyword_match_type"] = match_type
    return dimensions

