from __future__ import annotations

from dataclasses import dataclass

from wilq.briefing.daily_runtime import build_daily_runtime
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import list_connector_statuses
from wilq.evidence.registry import connector_evidence_id
from wilq.operator_labels import (
    action_count_label,
    evidence_count_label,
    knowledge_reference_count_label,
    opportunity_domain_label,
    source_connector_label,
    source_connector_labels,
)
from wilq.schemas import (
    ActionRisk,
    CommandCenterActionPlanItem,
    ConnectorRefreshStatus,
    DailyDecision,
    MetricFact,
    Opportunity,
    OpportunityDomain,
)

EXCLUDED_DAILY_OPPORTUNITY_DECISION_IDS = {
    "decision_ads_business_context_before_budget_decisions",
}
EXCLUDED_DAILY_OPPORTUNITY_PLAN_IDS = {
    decision_id.replace("decision_", "plan_", 1)
    for decision_id in EXCLUDED_DAILY_OPPORTUNITY_DECISION_IDS
}

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
        blocked_title="Google Ads: brak dostępu blokuje odczyt danych",
        ready_title="Google Ads: wymagane świeże dowody przed rekomendacją",
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
        blocked_title="GSC: brak dostępu blokuje odczyt zapytań i stron",
        ready_title="GSC: wymagane świeże dowody przed rekomendacją",
        playbook_ids=("gsc_seo_content_playbook",),
        expert_rule_ids=("seo_gsc_opportunities_v1", "seo_query_page_matrix_v1"),
    ),
    OpportunityBlueprint(
        connector_id="google_analytics_4",
        domain=OpportunityDomain.ga4,
        opportunity_type="ga4_tracking_gap",
        blocked_title="GA4: brak dostępu blokuje diagnostykę zachowania",
        ready_title="GA4: wymagane świeże dowody przed rekomendacją",
        playbook_ids=("ga4_behavior_diagnostics_playbook",),
        expert_rule_ids=("ga4_diagnostics_v1",),
    ),
    OpportunityBlueprint(
        connector_id="google_merchant_center",
        domain=OpportunityDomain.merchant,
        opportunity_type="merchant_feed_issue",
        blocked_title="Merchant Center: brak dostępu blokuje diagnostykę feedu",
        ready_title="Merchant Center: wymagane świeże dowody przed rekomendacją",
        playbook_ids=("merchant_feed_optimization_playbook", "google_ads_pmax_playbook"),
        expert_rule_ids=("merchant_feed_rules_v1", "merchant_product_diagnostics_v1"),
        risk=ActionRisk.medium,
    ),
    OpportunityBlueprint(
        connector_id="ahrefs",
        domain=OpportunityDomain.ahrefs,
        opportunity_type="ahrefs_content_gap",
        blocked_title="Ahrefs: brak dostępu blokuje przegląd luk treści",
        ready_title="Ahrefs: wymagane świeże dowody przed rekomendacją",
        playbook_ids=("ahrefs_content_gap_playbook",),
        expert_rule_ids=("content_brief_rules_v1",),
    ),
    OpportunityBlueprint(
        connector_id="localo",
        domain=OpportunityDomain.localo,
        opportunity_type="localo_visibility_drop",
        blocked_title="Localo: brak dostępu blokuje lokalną widoczność",
        ready_title="Localo: wymagane świeże dowody przed rekomendacją",
        playbook_ids=("localo_local_seo_playbook",),
        expert_rule_ids=("local_visibility_v1", "local_reviews_v1"),
    ),
    OpportunityBlueprint(
        connector_id="wordpress_ekologus",
        domain=OpportunityDomain.wordpress,
        opportunity_type="wordpress_content_refresh",
        blocked_title="WordPress ekologus.pl: brak dostępu blokuje spis treści",
        ready_title="WordPress ekologus.pl: wymagane świeże dowody przed rekomendacją",
        playbook_ids=("wordpress_content_refresh_playbook", "gsc_seo_content_playbook"),
        expert_rule_ids=("content_duplication_rules_v1", "content_brief_rules_v1"),
        risk=ActionRisk.medium,
    ),
    OpportunityBlueprint(
        connector_id="linkedin",
        domain=OpportunityDomain.social,
        opportunity_type="social_post_candidate",
        blocked_title="LinkedIn: brak dostępu do organizacji blokuje publikację",
        ready_title="LinkedIn: wymagane świeże dowody przed rekomendacją",
        playbook_ids=("linkedin_content_playbook",),
        expert_rule_ids=("linkedin_rules_v1", "content_social_limits_v1"),
        risk=ActionRisk.medium,
    ),
    OpportunityBlueprint(
        connector_id="facebook",
        domain=OpportunityDomain.social,
        opportunity_type="social_post_candidate",
        blocked_title="Facebook: brak dostępu do strony blokuje publikację",
        ready_title="Facebook: wymagane świeże dowody przed rekomendacją",
        playbook_ids=("facebook_content_playbook",),
        expert_rule_ids=("facebook_rules_v1", "content_social_limits_v1"),
        risk=ActionRisk.medium,
    ),
)


def list_opportunities() -> list[Opportunity]:
    daily_opportunities = _daily_decision_opportunities()
    if daily_opportunities:
        return daily_opportunities
    return _connector_registry_opportunities()


def _daily_decision_opportunities() -> list[Opportunity]:
    runtime = build_daily_runtime()
    decisions_by_id = {decision.id: decision for decision in runtime.command_center.daily_decisions}
    opportunities = [
        _opportunity_from_action_plan_item(
            plan_item,
            decisions_by_id.get(plan_item.id.replace("plan_", "decision_", 1)),
        )
        for plan_item in runtime.command_center.action_plan
        if plan_item.evidence_ids and plan_item.source_connectors
        and plan_item.id not in EXCLUDED_DAILY_OPPORTUNITY_PLAN_IDS
    ]
    return sorted(opportunities, key=lambda item: (_opportunity_sort_priority(item), item.id))


def _opportunity_from_action_plan_item(
    plan_item: CommandCenterActionPlanItem,
    matching_decision: DailyDecision | None,
) -> Opportunity:
    metric_tiles = matching_decision.metric_tiles if matching_decision is not None else {}
    metrics = _metric_tiles_to_facts(matching_decision) if matching_decision is not None else []
    return _label_opportunity(Opportunity(
        id=f"opp_{plan_item.id.replace('plan_', 'decision_', 1)}",
        type=_route_opportunity_type(plan_item.route),
        title=plan_item.title,
        domain=_route_opportunity_domain(plan_item.route),
        source_connectors=plan_item.source_connectors,
        evidence_ids=plan_item.evidence_ids,
        metric_tiles=metric_tiles,
        metrics=metrics,
        human_diagnosis=plan_item.why_it_matters,
        recommended_action=plan_item.operator_action,
        risk=plan_item.risk,
        action_ids=plan_item.action_ids,
        expert_rule_ids=[],
        playbook_ids=[plan_item.skill_id] if plan_item.skill_id else [],
        is_fixture=False,
    ))


def _opportunity_from_daily_decision(decision: DailyDecision) -> Opportunity:
    return _label_opportunity(Opportunity(
        id=f"opp_{decision.id}",
        type=_route_opportunity_type(decision.route),
        title=decision.title,
        domain=_route_opportunity_domain(decision.route),
        source_connectors=decision.source_connectors,
        evidence_ids=decision.evidence_ids,
        metric_tiles=decision.metric_tiles,
        metrics=_metric_tiles_to_facts(decision),
        human_diagnosis=(
            f"{decision.co_widzimy} {decision.dlaczego_to_ma_znaczenie}"
        ),
        recommended_action=decision.bezpieczny_next_step,
        risk=decision.risk,
        action_ids=decision.action_ids,
        expert_rule_ids=[],
        playbook_ids=[decision.skill_id] if decision.skill_id else [],
        is_fixture=False,
    ))


def _daily_decision_type(decision: DailyDecision) -> str:
    return _route_opportunity_type(decision.route)


def _route_opportunity_type(route: str) -> str:
    if route.startswith("/ads-doctor"):
        return "google_ads_review_queue"
    if route.startswith("/merchant"):
        return "merchant_feed_issue"
    if route.startswith("/content-planner"):
        return "content_brief_candidate"
    if route.startswith("/ga4"):
        return "ga4_tracking_gap"
    if route.startswith("/localo"):
        return "localo_visibility_drop"
    return "daily_marketer_decision"


def _daily_decision_domain(decision: DailyDecision) -> OpportunityDomain:
    return _route_opportunity_domain(decision.route)


def _route_opportunity_domain(route: str) -> OpportunityDomain:
    if route.startswith("/ads-doctor"):
        return OpportunityDomain.google_ads
    if route.startswith("/merchant"):
        return OpportunityDomain.merchant
    if route.startswith("/content-planner"):
        return OpportunityDomain.gsc_seo
    if route.startswith("/ga4"):
        return OpportunityDomain.ga4
    if route.startswith("/localo"):
        return OpportunityDomain.localo
    return OpportunityDomain.codex


def _metric_tiles_to_facts(decision: DailyDecision) -> list[MetricFact]:
    source_connector = decision.source_connectors[0]
    evidence_id = decision.evidence_ids[0]
    return [
        MetricFact(
            name=_metric_tile_name(label),
            value=value,
            period="daily_decision",
            source_connector=source_connector,
            evidence_id=evidence_id,
            dimensions={"decision_id": decision.id, "label": label},
        )
        for label, value in decision.metric_tiles.items()
    ]


def _metric_tile_name(label: str) -> str:
    return (
        label.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("ą", "a")
        .replace("ć", "c")
        .replace("ę", "e")
        .replace("ł", "l")
        .replace("ń", "n")
        .replace("ó", "o")
        .replace("ś", "s")
        .replace("ź", "z")
        .replace("ż", "z")
    )


def _opportunity_sort_priority(opportunity: Opportunity) -> int:
    if opportunity.id.startswith("opp_decision_review_merchant"):
        return 10
    if opportunity.id.startswith("opp_decision_prepare_content"):
        return 12
    if opportunity.id.startswith("opp_decision_review_ga4"):
        return 14
    if opportunity.id.startswith("opp_decision_review_ads"):
        return 16
    return 90


def _connector_registry_opportunities() -> list[Opportunity]:
    statuses = {connector.id: connector for connector in list_connector_statuses()}
    opportunities: list[Opportunity] = []
    for blueprint in BLUEPRINTS:
        connector = statuses[blueprint.connector_id]
        evidence_id = connector_evidence_id(connector.id)
        missing = connector.missing_credentials
        latest_live_run = _latest_live_refresh(connector.id)
        title = _title(blueprint, connector.configured, latest_live_run is not None)
        opportunities.append(
            _label_opportunity(Opportunity(
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
            ))
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
    connector_label = source_connector_label(connector_id)
    missing_count = len(missing_credentials)
    if live_refresh_available:
        return (
            f"{connector_label} ma zakończony odczyt danych w WILQ. Ta karta jest "
            "pomocniczym przeglądem obszaru, nie samodzielną rekomendacją "
            "marketingową."
        )
    if configured:
        return (
            f"{connector_label} ma skonfigurowany dostęp, ale ta karta nie zawiera "
            "jeszcze świeżych metryk do decyzji. Najpierw użyj dedykowanego widoku "
            "diagnostycznego albo odśwież odczyt danych."
        )
    missing_label = (
        "brakuje dostępu do źródła danych"
        if missing_count == 0
        else f"brakuje dostępu do {missing_count} wymaganych ustawień źródła danych"
    )
    return (
        f"{connector_label} nie dostarcza dowodów do decyzji, bo {missing_label}. "
        "Najpierw trzeba skonfigurować dostęp i odświeżyć odczyt danych."
    )


def _recommended_action(
    connector_id: str,
    configured: bool,
    missing_credentials: list[str],
    live_refresh_available: bool,
) -> str:
    connector_label = source_connector_label(connector_id)
    if live_refresh_available:
        return (
            f"Otwórz dedykowany widok diagnostyczny dla: {connector_label}. "
            "Nie traktuj tej karty jako gotowego wniosku bez przejścia do widoku domeny."
        )
    if configured:
        return (
            f"Odśwież odczyt danych dla: {connector_label}, jeśli dedykowany widok "
            "nie ma świeżych dowodów."
        )
    missing_count = len(missing_credentials)
    missing_suffix = (
        ""
        if missing_count == 0
        else f" Brakuje {missing_count} wymaganych ustawień dostępu."
    )
    return f"Skonfiguruj dostęp dla: {connector_label}, potem odśwież dane.{missing_suffix}"


def _title(
    blueprint: OpportunityBlueprint,
    configured: bool,
    live_refresh_available: bool,
) -> str:
    if not configured:
        return blueprint.blocked_title
    if live_refresh_available:
        connector_label = source_connector_label(blueprint.connector_id)
        return f"{connector_label}: przegląd obszaru z dowodami"
    return blueprint.ready_title


def _label_opportunity(opportunity: Opportunity) -> Opportunity:
    return opportunity.model_copy(
        update={
            "domain_label": opportunity_domain_label(opportunity.domain),
            "source_connector_labels": source_connector_labels(
                opportunity.source_connectors
            ),
            "evidence_summary_label": evidence_count_label(opportunity.evidence_ids),
            "risk_label": _risk_label(opportunity.risk),
            "action_summary_label": action_count_label(opportunity.action_ids),
            "knowledge_summary_label": knowledge_reference_count_label(
                playbook_ids=opportunity.playbook_ids,
                expert_rule_ids=opportunity.expert_rule_ids,
            ),
        }
    )


def _risk_label(risk: ActionRisk | str) -> str:
    value = risk.value if isinstance(risk, ActionRisk) else risk
    labels = {
        "low": "niskie ryzyko",
        "medium": "średnie ryzyko",
        "high": "wysokie ryzyko",
        "critical": "krytyczne ryzyko",
    }
    return labels.get(value, "ryzyko szansy do sprawdzenia")


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
