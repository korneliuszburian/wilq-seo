"""Google Ads report, recommendation, shopping, and Demand Gen summaries."""
from __future__ import annotations

from collections import Counter
from typing import Any

from wilq.connectors.vendor import VendorMetricFact

from .budget import (
    _recommendation_impact_metric_facts,
)
from .campaigns import (
    _campaign_dimensions,
    _customer_resource_id,
)
from .shared import (
    SAFE_ERROR_LABEL,
    SAFE_FIELD_PATH,
    _bool_metric,
    _clip_dimension,
    _float_metric,
    _int_metric,
    _list_count,
    _search_stream_rows,
    _string_metric,
)

SHOPPING_PRODUCT_PERFORMANCE_LOOKBACK_DAYS = (30, 90)

SHOPPING_PRODUCT_PERFORMANCE_QUERY_TEMPLATE = """
SELECT
  campaign.id,
  campaign.name,
  campaign.advertising_channel_type,
  segments.product_item_id,
  segments.product_title,
  metrics.clicks,
  metrics.impressions,
  metrics.cost_micros,
  metrics.conversions,
  metrics.conversions_value
FROM shopping_performance_view
WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
  AND metrics.impressions > 0
ORDER BY
  metrics.conversions DESC,
  metrics.clicks DESC,
  metrics.cost_micros DESC,
  metrics.impressions DESC
LIMIT 200
""".strip()

SHOPPING_PRODUCT_STATE_QUERY = """
SELECT
  shopping_product.resource_name,
  shopping_product.merchant_center_id,
  shopping_product.channel,
  shopping_product.language_code,
  shopping_product.feed_label,
  shopping_product.item_id,
  shopping_product.title,
  shopping_product.status,
  shopping_product.availability,
  shopping_product.currency_code,
  shopping_product.price_micros,
  shopping_product.target_countries
FROM shopping_product
ORDER BY shopping_product.item_id ASC
LIMIT 500
""".strip()

RECOMMENDATION_SUMMARY_QUERY = """
SELECT
  recommendation.resource_name,
  recommendation.type,
  recommendation.dismissed,
  recommendation.campaign,
  recommendation.campaign_budget,
  recommendation.campaigns,
  recommendation.impact
FROM recommendation
WHERE recommendation.dismissed = false
LIMIT 50
""".strip()

CHANGE_EVENT_LOOKBACK_DAYS = 14

CHANGE_EVENT_SUMMARY_QUERY_TEMPLATE = """
SELECT
  change_event.resource_name,
  change_event.change_date_time,
  change_event.change_resource_name,
  change_event.client_type,
  change_event.change_resource_type,
  change_event.resource_change_operation,
  change_event.changed_fields,
  change_event.campaign
FROM change_event
WHERE change_event.change_date_time >= '{start_date}'
  AND change_event.change_date_time <= '{end_date}'
ORDER BY change_event.change_date_time DESC
LIMIT 50
""".strip()

DEMAND_GEN_AD_GROUP_AD_QUERY = """
SELECT
  campaign.id,
  campaign.name,
  campaign.status,
  campaign.advertising_channel_type,
  ad_group.id,
  ad_group.name,
  ad_group_ad.status,
  ad_group_ad.ad.id,
  ad_group_ad.ad.type,
  ad_group_ad.ad.final_urls,
  ad_group_ad.ad.demand_gen_multi_asset_ad.marketing_images,
  ad_group_ad.ad.demand_gen_multi_asset_ad.square_marketing_images,
  ad_group_ad.ad.demand_gen_multi_asset_ad.portrait_marketing_images,
  ad_group_ad.ad.demand_gen_multi_asset_ad.classic_display_images,
  ad_group_ad.ad.demand_gen_multi_asset_ad.logo_images,
  ad_group_ad.ad.demand_gen_carousel_ad.logo_image,
  ad_group_ad.ad.demand_gen_carousel_ad.carousel_cards,
  ad_group_ad.ad.demand_gen_video_responsive_ad.logo_images,
  ad_group_ad.ad.demand_gen_video_responsive_ad.call_to_actions,
  ad_group_ad.ad.demand_gen_video_responsive_ad.videos
FROM ad_group_ad
WHERE campaign.advertising_channel_type = DEMAND_GEN
  AND ad_group_ad.status != 'REMOVED'
LIMIT 100
""".strip()

DEMAND_GEN_CREATIVE_ASSET_QUERY = """
SELECT
  asset.id,
  asset.type,
  ad_group_ad_asset_view.field_type,
  metrics.impressions
FROM ad_group_ad_asset_view
WHERE ad_group_ad_asset_view.field_type = DEMAND_GEN_CAROUSEL_CARD
LIMIT 100
""".strip()

def _summarize_recommendation_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    metric_facts: list[VendorMetricFact] = []
    recommendation_types: set[str] = set()
    campaign_count = 0
    impact_row_count = 0
    impact_metric_count = 0
    for row in rows:
        recommendation = row.get("recommendation", {})
        if not isinstance(recommendation, dict):
            continue
        dimensions = _recommendation_dimensions(recommendation)
        recommendation_type = dimensions.get("recommendation_type")
        if recommendation_type:
            recommendation_types.add(recommendation_type)
        row_campaign_count = _recommendation_campaign_count(recommendation)
        campaign_count += row_campaign_count
        if dimensions:
            metric_facts.extend(
                [
                    VendorMetricFact(
                        "recommendation_available",
                        1,
                        dimensions,
                        period="recommendation",
                    ),
                    VendorMetricFact(
                        "recommendation_campaign_count",
                        row_campaign_count,
                        dimensions,
                        period="recommendation",
                    ),
                ]
            )
            impact_facts = _recommendation_impact_metric_facts(recommendation, dimensions)
            if impact_facts:
                impact_row_count += 1
                impact_metric_count += len(impact_facts)
                metric_facts.extend(impact_facts)
    return (
        {
            "recommendation_query": "active_recommendations",
            "recommendation_row_count": len(rows),
            "recommendation_campaign_count": campaign_count,
            "recommendation_impact_row_count": impact_row_count,
            "recommendation_impact_metric_count": impact_metric_count,
            "recommendation_types": ",".join(sorted(recommendation_types)),
        },
        metric_facts,
    )

def _summarize_change_event_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    metric_facts: list[VendorMetricFact] = []
    resource_types: set[str] = set()
    operations: set[str] = set()
    client_types: set[str] = set()
    campaign_ids: set[str] = set()
    for row in rows:
        change_event = row.get("changeEvent", row.get("change_event", {}))
        if not isinstance(change_event, dict):
            continue
        dimensions = _change_event_dimensions(change_event)
        resource_type = dimensions.get("change_resource_type")
        operation = dimensions.get("resource_change_operation")
        client_type = dimensions.get("client_type")
        campaign_id = dimensions.get("campaign_id")
        if resource_type:
            resource_types.add(resource_type)
        if operation:
            operations.add(operation)
        if client_type:
            client_types.add(client_type)
        if campaign_id:
            campaign_ids.add(campaign_id)
        if dimensions:
            changed_field_count = _int_metric(dimensions.get("changed_field_count"))
            metric_facts.extend(
                [
                    VendorMetricFact(
                        "change_event_available",
                        1,
                        dimensions,
                        period="change_history",
                    ),
                    VendorMetricFact(
                        "change_event_changed_field_count",
                        changed_field_count,
                        dimensions,
                        period="change_history",
                    ),
                ]
            )
    return (
        {
            "change_event_query": f"change_event_last_{CHANGE_EVENT_LOOKBACK_DAYS}_days",
            "change_event_row_count": len(rows),
            "change_event_campaign_count": len(campaign_ids),
            "change_event_resource_types": ",".join(sorted(resource_types)),
            "change_event_operations": ",".join(sorted(operations)),
            "change_event_client_types": ",".join(sorted(client_types)),
        },
        metric_facts,
    )

def _summarize_shopping_product_performance_response(
    payload: Any,
    lookback_days: int,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    clicks = 0
    impressions = 0
    cost_micros = 0
    conversions = 0.0
    conversion_value = 0.0
    product_ids: set[str] = set()
    metric_facts: list[VendorMetricFact] = []
    fact_period = f"shopping_product_performance_{lookback_days}d"
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
        dimensions = _shopping_product_dimensions(row)
        product_id = dimensions.get("product_id")
        if product_id:
            product_ids.add(product_id)
        if dimensions:
            metric_facts.extend(
                [
                    VendorMetricFact(
                        "shopping_product_clicks",
                        row_clicks,
                        dimensions,
                        period=fact_period,
                    ),
                    VendorMetricFact(
                        "shopping_product_impressions",
                        row_impressions,
                        dimensions,
                        period=fact_period,
                    ),
                    VendorMetricFact(
                        "shopping_product_cost_micros",
                        row_cost_micros,
                        dimensions,
                        period=fact_period,
                    ),
                    VendorMetricFact(
                        "shopping_product_conversions",
                        row_conversions,
                        dimensions,
                        period=fact_period,
                    ),
                    VendorMetricFact(
                        "shopping_product_conversion_value",
                        row_conversion_value,
                        dimensions,
                        period=fact_period,
                    ),
                ]
            )
    return (
        {
            "shopping_product_performance_status": "ready",
            "shopping_product_performance_query": (
                f"shopping_performance_view_last_{lookback_days}_days"
            ),
            "shopping_product_performance_lookback_days": lookback_days,
            "shopping_product_performance_row_count": len(rows),
            "shopping_product_performance_product_count": len(product_ids),
            "shopping_product_clicks": clicks,
            "shopping_product_impressions": impressions,
            "shopping_product_cost_micros": cost_micros,
            "shopping_product_conversions": conversions,
            "shopping_product_conversion_value": conversion_value,
        },
        metric_facts,
    )

def _summarize_shopping_product_state_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    product_ids: set[str] = set()
    statuses: Counter[str] = Counter()
    availability: Counter[str] = Counter()
    metric_facts: list[VendorMetricFact] = []
    for row in rows:
        shopping_product = row.get("shoppingProduct", row.get("shopping_product", {}))
        if not isinstance(shopping_product, dict):
            continue
        dimensions = _shopping_product_state_dimensions(shopping_product)
        product_id = dimensions.get("product_id")
        if product_id:
            product_ids.add(product_id)
        status = _string_metric(shopping_product.get("status"))
        if status:
            statuses[status] += 1
        product_availability = _string_metric(shopping_product.get("availability"))
        if product_availability:
            availability[product_availability] += 1
        if not dimensions:
            continue
        metric_facts.append(
            VendorMetricFact(
                "shopping_product_state_available",
                1,
                dimensions,
                period="shopping_product_state",
            )
        )
        if status:
            metric_facts.append(
                VendorMetricFact(
                    "shopping_product_status",
                    status,
                    dimensions,
                    period="shopping_product_state",
                )
            )
        if product_availability:
            metric_facts.append(
                VendorMetricFact(
                    "shopping_product_availability",
                    product_availability,
                    dimensions,
                    period="shopping_product_state",
                )
            )
        price_micros = _int_metric(shopping_product.get("priceMicros"))
        if price_micros:
            metric_facts.append(
                VendorMetricFact(
                    "shopping_product_price_micros",
                    price_micros,
                    dimensions,
                    period="shopping_product_state",
                )
            )
    return (
        {
            "shopping_product_state_status": "ready",
            "shopping_product_state_query": "shopping_product_current_state",
            "shopping_product_state_row_count": len(rows),
            "shopping_product_state_product_count": len(product_ids),
            "shopping_product_state_eligible_count": statuses.get("ELIGIBLE", 0),
            "shopping_product_state_limited_count": statuses.get("ELIGIBLE_LIMITED", 0),
            "shopping_product_state_not_eligible_count": statuses.get("NOT_ELIGIBLE", 0),
            "shopping_product_state_status_values": ",".join(sorted(statuses)),
            "shopping_product_state_availability_values": ",".join(sorted(availability)),
        },
        metric_facts,
    )

def _summarize_demand_gen_ad_group_ad_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    metric_facts: list[VendorMetricFact] = []
    ad_type_counts: Counter[str] = Counter()
    final_url_count = 0
    asset_reference_count = 0
    for row in rows:
        dimensions = _demand_gen_ad_dimensions(row)
        if not dimensions:
            continue
        ad_type = dimensions.get("ad_type", "UNKNOWN")
        ad_type_counts[ad_type] += 1
        ad_group_ad = row.get("adGroupAd", row.get("ad_group_ad", {}))
        ad = ad_group_ad.get("ad", {}) if isinstance(ad_group_ad, dict) else {}
        row_final_url_count = _list_count(ad, "finalUrls", "final_urls")
        row_asset_reference_count = _demand_gen_ad_asset_reference_count(ad)
        final_url_count += row_final_url_count
        asset_reference_count += row_asset_reference_count
        metric_facts.extend(
            [
                VendorMetricFact(
                    "demand_gen_ad_available",
                    1,
                    dimensions,
                    period="demand_gen_ad_inventory",
                ),
                VendorMetricFact(
                    "demand_gen_ad_final_url_count",
                    row_final_url_count,
                    dimensions,
                    period="demand_gen_ad_inventory",
                ),
                VendorMetricFact(
                    "demand_gen_ad_asset_reference_count",
                    row_asset_reference_count,
                    dimensions,
                    period="demand_gen_ad_inventory",
                ),
            ]
        )
    return (
        {
            "demand_gen_ad_group_ad_status": "ready",
            "demand_gen_ad_group_ad_query": "demand_gen_ad_group_ad_inventory",
            "demand_gen_ad_group_ad_row_count": len(rows),
            "demand_gen_multi_asset_ad_count": ad_type_counts["DEMAND_GEN_MULTI_ASSET_AD"],
            "demand_gen_carousel_ad_count": ad_type_counts["DEMAND_GEN_CAROUSEL_AD"],
            "demand_gen_video_responsive_ad_count": ad_type_counts[
                "DEMAND_GEN_VIDEO_RESPONSIVE_AD"
            ],
            "demand_gen_final_url_count": final_url_count,
            "demand_gen_asset_reference_count": asset_reference_count,
        },
        metric_facts,
    )

def _summarize_demand_gen_creative_asset_response(
    payload: Any,
) -> tuple[dict[str, float | int | str], list[VendorMetricFact]]:
    rows = _search_stream_rows(payload)
    impressions = 0
    metric_facts: list[VendorMetricFact] = []
    for row in rows:
        dimensions = _demand_gen_creative_asset_dimensions(row)
        if not dimensions:
            continue
        metrics = row.get("metrics", {})
        row_impressions = _int_metric(metrics.get("impressions"))
        impressions += row_impressions
        metric_facts.append(
            VendorMetricFact(
                "demand_gen_creative_asset_impressions",
                row_impressions,
                dimensions,
                period="demand_gen_creative_asset",
            )
        )
    return (
        {
            "demand_gen_creative_asset_status": "ready",
            "demand_gen_creative_asset_query": "demand_gen_carousel_asset_performance",
            "demand_gen_creative_asset_row_count": len(rows),
            "demand_gen_creative_asset_impressions": impressions,
        },
        metric_facts,
    )

def _demand_gen_ad_asset_reference_count(ad: Any) -> int:
    if not isinstance(ad, dict):
        return 0
    return (
        _demand_gen_multi_asset_reference_count(ad)
        + _demand_gen_carousel_asset_reference_count(ad)
        + _demand_gen_video_responsive_asset_reference_count(ad)
    )

def _demand_gen_multi_asset_reference_count(ad: dict[str, Any]) -> int:
    info = ad.get("demandGenMultiAssetAd", ad.get("demand_gen_multi_asset_ad", {}))
    if not isinstance(info, dict):
        return 0
    return sum(
        _list_count(info, camel_key, snake_key)
        for camel_key, snake_key in (
            ("marketingImages", "marketing_images"),
            ("squareMarketingImages", "square_marketing_images"),
            ("portraitMarketingImages", "portrait_marketing_images"),
            ("classicDisplayImages", "classic_display_images"),
            ("logoImages", "logo_images"),
        )
    )

def _demand_gen_carousel_asset_reference_count(ad: dict[str, Any]) -> int:
    info = ad.get("demandGenCarouselAd", ad.get("demand_gen_carousel_ad", {}))
    if not isinstance(info, dict):
        return 0
    return _list_count(info, "logoImage", "logo_image") + _list_count(
        info,
        "carouselCards",
        "carousel_cards",
    )

def _demand_gen_video_responsive_asset_reference_count(ad: dict[str, Any]) -> int:
    info = ad.get(
        "demandGenVideoResponsiveAd",
        ad.get("demand_gen_video_responsive_ad", {}),
    )
    if not isinstance(info, dict):
        return 0
    return sum(
        _list_count(info, camel_key, snake_key)
        for camel_key, snake_key in (
            ("logoImages", "logo_images"),
            ("callToActions", "call_to_actions"),
            ("videos", "videos"),
        )
    )

def _shopping_product_dimensions(row: dict[str, Any]) -> dict[str, str]:
    dimensions = _campaign_dimensions(row.get("campaign", {}))
    segments = row.get("segments", {})
    if not isinstance(segments, dict):
        return dimensions
    product_item_id = segments.get("productItemId", segments.get("product_item_id"))
    if isinstance(product_item_id, str) and product_item_id.strip():
        normalized_product_id = product_item_id.strip()
        dimensions["product_id"] = normalized_product_id
        dimensions["item_id"] = normalized_product_id
        dimensions["product_item_id"] = normalized_product_id
    product_title = segments.get("productTitle", segments.get("product_title"))
    if isinstance(product_title, str) and product_title.strip():
        dimensions["product_title"] = _clip_dimension(product_title)
    return dimensions

def _shopping_product_state_dimensions(shopping_product: dict[str, Any]) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    resource_name = _string_metric(
        shopping_product.get("resourceName", shopping_product.get("resource_name"))
    )
    if resource_name:
        dimensions["shopping_product_resource_name"] = _clip_dimension(resource_name)
    item_id = _string_metric(shopping_product.get("itemId", shopping_product.get("item_id")))
    if item_id:
        dimensions["product_id"] = item_id
        dimensions["item_id"] = item_id
        dimensions["product_item_id"] = item_id
    merchant_center_id = shopping_product.get(
        "merchantCenterId",
        shopping_product.get("merchant_center_id"),
    )
    if merchant_center_id is not None:
        dimensions["merchant_center_id"] = str(merchant_center_id)
    for api_key, fallback_key, dimension_key in (
        ("channel", "channel", "product_channel"),
        ("languageCode", "language_code", "language_code"),
        ("feedLabel", "feed_label", "feed_label"),
        ("currencyCode", "currency_code", "currency_code"),
        ("status", "status", "product_status"),
        ("availability", "availability", "product_availability"),
    ):
        value = _string_metric(shopping_product.get(api_key, shopping_product.get(fallback_key)))
        if value:
            dimensions[dimension_key] = value
    title = _string_metric(shopping_product.get("title"))
    if title:
        dimensions["product_title"] = _clip_dimension(title)
    target_countries = shopping_product.get(
        "targetCountries",
        shopping_product.get("target_countries"),
    )
    if isinstance(target_countries, list):
        countries = sorted(str(country) for country in target_countries if country)
        if countries:
            dimensions["target_countries"] = ",".join(countries)
    return dimensions

def _demand_gen_ad_dimensions(row: dict[str, Any]) -> dict[str, str]:
    dimensions = _campaign_dimensions(row.get("campaign", {}))
    ad_group = row.get("adGroup", row.get("ad_group", {}))
    if isinstance(ad_group, dict):
        ad_group_id = ad_group.get("id")
        if ad_group_id is not None:
            dimensions["ad_group_id"] = str(ad_group_id)
        ad_group_name = ad_group.get("name")
        if isinstance(ad_group_name, str) and ad_group_name:
            dimensions["ad_group_name"] = ad_group_name
    ad_group_ad = row.get("adGroupAd", row.get("ad_group_ad", {}))
    if not isinstance(ad_group_ad, dict):
        return dimensions
    ad_status = ad_group_ad.get("status")
    if isinstance(ad_status, str) and ad_status:
        dimensions["ad_status"] = ad_status
    ad = ad_group_ad.get("ad", {})
    if not isinstance(ad, dict):
        return dimensions
    ad_id = ad.get("id")
    if ad_id is not None:
        dimensions["ad_id"] = str(ad_id)
    ad_type = ad.get("type")
    if isinstance(ad_type, str) and ad_type:
        dimensions["ad_type"] = ad_type
    return dimensions

def _demand_gen_creative_asset_dimensions(row: dict[str, Any]) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    asset = row.get("asset", {})
    if isinstance(asset, dict):
        asset_id = asset.get("id")
        if asset_id is not None:
            dimensions["asset_id"] = str(asset_id)
        asset_type = asset.get("type")
        if isinstance(asset_type, str) and asset_type:
            dimensions["asset_type"] = asset_type
    asset_view = row.get("adGroupAdAssetView", row.get("ad_group_ad_asset_view", {}))
    if isinstance(asset_view, dict):
        field_type = asset_view.get("fieldType", asset_view.get("field_type"))
        if isinstance(field_type, str) and field_type:
            dimensions["field_type"] = field_type
    return dimensions

def _recommendation_dimensions(recommendation: dict[str, Any]) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    resource_name = recommendation.get("resourceName", recommendation.get("resource_name"))
    if isinstance(resource_name, str) and resource_name:
        dimensions["recommendation_resource_name"] = resource_name
    recommendation_id = _customer_resource_id(resource_name)
    if recommendation_id:
        dimensions["recommendation_id"] = recommendation_id
    recommendation_type = recommendation.get("type")
    if isinstance(recommendation_type, str) and recommendation_type:
        dimensions["recommendation_type"] = recommendation_type
    dismissed = _bool_metric(recommendation.get("dismissed"))
    dimensions["dismissed"] = "true" if dismissed else "false"
    campaign_id = _customer_resource_id(recommendation.get("campaign"))
    if campaign_id:
        dimensions["campaign_id"] = campaign_id
    campaign_budget_id = _customer_resource_id(
        recommendation.get("campaignBudget", recommendation.get("campaign_budget"))
    )
    if campaign_budget_id:
        dimensions["campaign_budget_id"] = campaign_budget_id
    campaign_count = _recommendation_campaign_count(recommendation)
    dimensions["recommendation_campaign_count"] = str(campaign_count)
    return dimensions

def _recommendation_campaign_count(recommendation: dict[str, Any]) -> int:
    campaigns = recommendation.get("campaigns")
    if isinstance(campaigns, list):
        return len(campaigns)
    return 1 if _customer_resource_id(recommendation.get("campaign")) else 0

def _change_event_dimensions(change_event: dict[str, Any]) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    resource_name = change_event.get("resourceName", change_event.get("resource_name"))
    change_event_id = _customer_resource_id(resource_name)
    if change_event_id:
        dimensions["change_event_id"] = change_event_id
    change_date_time = change_event.get(
        "changeDateTime",
        change_event.get("change_date_time"),
    )
    if isinstance(change_date_time, str) and change_date_time:
        dimensions["change_date_time"] = change_date_time[:32]
    change_resource_name = change_event.get(
        "changeResourceName",
        change_event.get("change_resource_name"),
    )
    change_resource_id = _customer_resource_id(change_resource_name)
    if change_resource_id:
        dimensions["change_resource_id"] = change_resource_id
    for source_key, target_key in (
        ("clientType", "client_type"),
        ("changeResourceType", "change_resource_type"),
        ("resourceChangeOperation", "resource_change_operation"),
    ):
        value = change_event.get(source_key, change_event.get(target_key))
        if isinstance(value, str) and SAFE_ERROR_LABEL.fullmatch(value):
            dimensions[target_key] = value
    campaign_id = _customer_resource_id(change_event.get("campaign"))
    if campaign_id:
        dimensions["campaign_id"] = campaign_id
    changed_fields = _field_mask_paths(
        change_event.get("changedFields", change_event.get("changed_fields"))
    )
    dimensions["changed_field_count"] = str(len(changed_fields))
    if changed_fields:
        dimensions["changed_fields"] = ",".join(changed_fields[:8])
    return dimensions

def _field_mask_paths(value: Any) -> list[str]:
    raw_paths: list[Any]
    if isinstance(value, dict):
        paths = value.get("paths")
        raw_paths = paths if isinstance(paths, list) else []
    elif isinstance(value, list):
        raw_paths = value
    elif isinstance(value, str):
        raw_paths = [path.strip() for path in value.split(",")]
    else:
        raw_paths = []
    return [
        path
        for path in (str(raw_path).strip() for raw_path in raw_paths)
        if path and SAFE_FIELD_PATH.fullmatch(path)
    ]

