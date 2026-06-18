from __future__ import annotations

from dataclasses import dataclass

from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import list_connector_statuses
from wilq.evidence.registry import connector_evidence_id
from wilq.schemas import (
    ActionRisk,
    ConnectorRefreshStatus,
    MetricFact,
    Opportunity,
    OpportunityDomain,
)

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


@dataclass(frozen=True)
class OpportunityBlueprint:
    connector_id: str
    domain: OpportunityDomain
    opportunity_type: str
    blocked_title: str
    ready_title: str
    playbook_ids: tuple[str, ...]
    expert_rule_ids: tuple[str, ...]
    risk: ActionRisk = ActionRisk.low
    action_ids: tuple[str, ...] = ()


BLUEPRINTS: tuple[OpportunityBlueprint, ...] = (
    OpportunityBlueprint(
        connector_id="google_ads",
        domain=OpportunityDomain.google_ads,
        opportunity_type="google_ads_waste",
        blocked_title="Google Ads evidence pipeline blocked by missing credentials",
        ready_title="Google Ads connector ready for first search-term refresh",
        playbook_ids=(
            "google_ads_search_playbook",
            "google_ads_negative_keywords_playbook",
            "google_ads_custom_segments_playbook",
        ),
        expert_rule_ids=(
            "ads_search_terms_v1",
            "ads_negative_keywords_v1",
            "ads_diagnostics_v1",
        ),
        action_ids=("act_configure_google_ads_env",),
    ),
    OpportunityBlueprint(
        connector_id="google_search_console",
        domain=OpportunityDomain.gsc_seo,
        opportunity_type="gsc_ctr_opportunity",
        blocked_title="GSC query/page evidence pipeline blocked by missing credentials",
        ready_title="GSC connector ready for query/page opportunity refresh",
        playbook_ids=("gsc_seo_content_playbook",),
        expert_rule_ids=("seo_gsc_opportunities_v1", "seo_query_page_matrix_v1"),
    ),
    OpportunityBlueprint(
        connector_id="google_analytics_4",
        domain=OpportunityDomain.ga4,
        opportunity_type="ga4_tracking_gap",
        blocked_title="GA4 behavior diagnostics blocked by missing property access",
        ready_title="GA4 connector ready for behavior diagnostics refresh",
        playbook_ids=("ga4_behavior_diagnostics_playbook",),
        expert_rule_ids=("ga4_diagnostics_v1",),
    ),
    OpportunityBlueprint(
        connector_id="google_merchant_center",
        domain=OpportunityDomain.merchant,
        opportunity_type="merchant_feed_issue",
        blocked_title="Merchant feed diagnostics blocked by missing account access",
        ready_title="Merchant connector ready for feed diagnostics refresh",
        playbook_ids=("merchant_feed_optimization_playbook", "google_ads_pmax_playbook"),
        expert_rule_ids=("merchant_feed_rules_v1", "merchant_product_diagnostics_v1"),
        risk=ActionRisk.medium,
    ),
    OpportunityBlueprint(
        connector_id="ahrefs",
        domain=OpportunityDomain.ahrefs,
        opportunity_type="ahrefs_content_gap",
        blocked_title="Ahrefs content-gap evidence blocked by missing API token",
        ready_title="Ahrefs connector ready for competitor gap refresh",
        playbook_ids=("ahrefs_content_gap_playbook",),
        expert_rule_ids=("content_brief_rules_v1",),
    ),
    OpportunityBlueprint(
        connector_id="localo",
        domain=OpportunityDomain.localo,
        opportunity_type="localo_visibility_drop",
        blocked_title="Local visibility evidence blocked by missing Localo access",
        ready_title="Localo connector ready for local visibility refresh",
        playbook_ids=("localo_local_seo_playbook",),
        expert_rule_ids=("local_visibility_v1", "local_reviews_v1"),
    ),
    OpportunityBlueprint(
        connector_id="wordpress_ekologus",
        domain=OpportunityDomain.wordpress,
        opportunity_type="wordpress_content_refresh",
        blocked_title="WordPress content inventory blocked by missing ekologus.pl access",
        ready_title="WordPress ekologus.pl ready for content inventory refresh",
        playbook_ids=("wordpress_content_refresh_playbook", "gsc_seo_content_playbook"),
        expert_rule_ids=("content_duplication_rules_v1", "content_brief_rules_v1"),
        risk=ActionRisk.medium,
    ),
    OpportunityBlueprint(
        connector_id="linkedin",
        domain=OpportunityDomain.social,
        opportunity_type="social_post_candidate",
        blocked_title="LinkedIn publishing evidence blocked by missing organization access",
        ready_title="LinkedIn connector ready for social publishing review",
        playbook_ids=("linkedin_content_playbook",),
        expert_rule_ids=("linkedin_rules_v1", "content_social_limits_v1"),
        risk=ActionRisk.medium,
    ),
    OpportunityBlueprint(
        connector_id="facebook",
        domain=OpportunityDomain.social,
        opportunity_type="social_post_candidate",
        blocked_title="Facebook Page publishing evidence blocked by missing Page access",
        ready_title="Facebook connector ready for Page publishing review",
        playbook_ids=("facebook_content_playbook",),
        expert_rule_ids=("facebook_rules_v1", "content_social_limits_v1"),
        risk=ActionRisk.medium,
    ),
)


def list_opportunities() -> list[Opportunity]:
    statuses = {connector.id: connector for connector in list_connector_statuses()}
    opportunities: list[Opportunity] = []
    for blueprint in BLUEPRINTS:
        connector = statuses[blueprint.connector_id]
        evidence_id = connector_evidence_id(connector.id)
        missing = connector.missing_credentials
        latest_live_run = _latest_live_refresh(connector.id)
        title = _title(blueprint, connector.configured, latest_live_run is not None)
        opportunities.append(
            Opportunity(
                id=f"opp_connector_{connector.id}",
                type=blueprint.opportunity_type,
                title=title,
                domain=blueprint.domain,
                source_connectors=[connector.id],
                evidence_ids=[evidence_id],
                metrics=_opportunity_metrics(connector.id, connector.configured, evidence_id),
                human_diagnosis=_diagnosis(
                    connector.id,
                    connector.configured,
                    missing,
                    blueprint.playbook_ids,
                    blueprint.expert_rule_ids,
                    latest_live_run is not None,
                ),
                recommended_action=_recommended_action(
                    connector.id,
                    connector.configured,
                    missing,
                    latest_live_run is not None,
                ),
                risk=blueprint.risk,
                action_ids=list(blueprint.action_ids) if not connector.configured else [],
                expert_rule_ids=list(blueprint.expert_rule_ids),
                playbook_ids=list(blueprint.playbook_ids),
                is_fixture=False,
            )
        )
    return opportunities


def get_opportunity(opportunity_id: str) -> Opportunity | None:
    return next((item for item in list_opportunities() if item.id == opportunity_id), None)


def _diagnosis(
    connector_id: str,
    configured: bool,
    missing_credentials: list[str],
    playbook_ids: tuple[str, ...],
    expert_rule_ids: tuple[str, ...],
    live_refresh_available: bool,
) -> str:
    playbooks = ", ".join(playbook_ids)
    rules = ", ".join(expert_rule_ids)
    if live_refresh_available:
        return (
            f"{connector_id} ma zakończony odczyt vendor_read w WILQ. Ta karta jest "
            f"technicznym inventory reguł/playbooków ({playbooks}), nie gotową "
            "rekomendacją marketingową."
        )
    if configured:
        return (
            f"{connector_id} ma nazwy credentiali w runtime, ale ta karta nie zawiera "
            f"jeszcze świeżych metryk performance. Najpierw użyj dedykowanego widoku "
            "diagnostycznego albo refreshu connectora, potem dopiero playbooków: "
            f"{playbooks}."
        )
    return (
        f"{connector_id} nie dostarcza evidence dla playbooków {playbooks} ani reguł "
        f"{rules}, dopóki brakuje credentiali: "
        f"{', '.join(missing_credentials)}."
    )


def _recommended_action(
    connector_id: str,
    configured: bool,
    missing_credentials: list[str],
    live_refresh_available: bool,
) -> str:
    if live_refresh_available:
        return (
            f"Otwórz dedykowany widok diagnostyczny dla {connector_id}; "
            "nie traktuj tej karty jako insightu."
        )
    if configured:
        return (
            f"Uruchom read-only refresh dla {connector_id}, jeśli dedykowany widok "
            "nie ma świeżego evidence."
        )
    return (
        f"Skonfiguruj wymagane credentiale dla {connector_id}, potem odśwież dane: "
        f"{', '.join(missing_credentials)}."
    )


def _title(
    blueprint: OpportunityBlueprint,
    configured: bool,
    live_refresh_available: bool,
) -> str:
    if not configured:
        return blueprint.blocked_title
    if live_refresh_available:
        return f"{blueprint.connector_id}: technical playbook inventory"
    return blueprint.ready_title.replace("connector ready for", "requires evidence before")


def _opportunity_metrics(
    connector_id: str,
    configured: bool,
    evidence_id: str,
) -> list[MetricFact]:
    return [
        MetricFact(
            name="connector_runtime_configured",
            value="yes" if configured else "no",
            period="current",
            source_connector=connector_id,
            evidence_id=evidence_id,
        )
    ]


def _latest_live_refresh(connector_id: str) -> object | None:
    for run in list_connector_refresh_runs(connector_id=connector_id):
        if run.status == ConnectorRefreshStatus.completed and run.vendor_data_collected:
            return run
    return None
