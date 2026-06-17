from __future__ import annotations

from wilq.schemas import ActionRisk, MetricFact, Opportunity, OpportunityDomain

OPPORTUNITY_TYPES = (
    "google_ads_waste",
    "google_ads_negative_keywords",
    "google_ads_landing_mismatch",
    "google_ads_recommendation_review",
    "google_ads_quality_score_issue",
    "gsc_ctr_opportunity",
    "gsc_content_decay",
    "gsc_cannibalization",
    "gsc_near_top_opportunity",
    "ahrefs_content_gap",
    "ahrefs_competitor_gap",
    "ahrefs_backlink_gap",
    "localo_visibility_drop",
    "wordpress_content_refresh",
    "wordpress_duplicate_content_risk",
    "social_post_candidate",
    "content_brief_candidate",
    "ga4_landing_page_issue",
    "ga4_campaign_quality_issue",
    "ga4_funnel_dropoff_issue",
    "ga4_tracking_gap",
    "ga4_conversion_mapping_gap",
    "merchant_feed_issue",
    "merchant_product_title_rewrite",
    "merchant_product_description_rewrite",
    "merchant_product_attribute_gap",
    "pmax_retail_readiness_gap",
    "shopping_campaign_candidate",
)


def seed_opportunities() -> list[Opportunity]:
    return [
        Opportunity(
            id="opp_dev_connector_ads_001",
            type="google_ads_waste",
            title="Google Ads diagnostics blocked until credentials are configured",
            domain=OpportunityDomain.google_ads,
            source_connectors=["google_ads"],
            evidence_ids=["ev_connector_google_ads_missing_credentials"],
            metrics=[
                MetricFact(
                    name="real_metric_status",
                    value="unavailable_until_connector_configured",
                    period="current",
                    source_connector="google_ads",
                    evidence_id="ev_connector_google_ads_missing_credentials",
                )
            ],
            human_diagnosis=(
                "WILQ cannot diagnose paid-media waste until Google Ads credentials are present. "
                "This is connector state, not Ekologus performance data."
            ),
            recommended_action=(
                "Configure Google Ads access pack variables, then refresh connector data."
            ),
            risk=ActionRisk.low,
            action_ids=["act_configure_google_ads_access_pack"],
            is_fixture=True,
        ),
        Opportunity(
            id="opp_dev_ga4_tracking_001",
            type="ga4_tracking_gap",
            title="GA4 behavior diagnostics need property configuration",
            domain=OpportunityDomain.ga4,
            source_connectors=["google_analytics_4"],
            evidence_ids=["ev_connector_ga4_missing_credentials"],
            human_diagnosis=(
                "Ads and SEO clicks are incomplete without GA4 engagement and conversion context."
            ),
            recommended_action="Provide GA4 property access before classifying traffic quality.",
            risk=ActionRisk.low,
            action_ids=[],
            is_fixture=True,
        ),
        Opportunity(
            id="opp_dev_merchant_feed_001",
            type="merchant_feed_issue",
            title="Merchant/feed health is represented but not yet refreshed",
            domain=OpportunityDomain.merchant,
            source_connectors=["google_merchant_center"],
            evidence_ids=["ev_connector_merchant_missing_credentials"],
            human_diagnosis=(
                "sklep.ekologus.pl requires product/feed diagnostics, but the current state only "
                "proves connector availability requirements."
            ),
            recommended_action="Configure Merchant Center access and run feed health refresh.",
            risk=ActionRisk.medium,
            action_ids=[],
            is_fixture=True,
        ),
    ]


def list_opportunities() -> list[Opportunity]:
    return seed_opportunities()


def get_opportunity(opportunity_id: str) -> Opportunity | None:
    return next((item for item in list_opportunities() if item.id == opportunity_id), None)
