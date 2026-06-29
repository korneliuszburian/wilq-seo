from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from wilq.briefing.blocked_claim_labels import operator_blocked_claims
from wilq.expert.rules import list_expert_rule_summaries
from wilq.knowledge.compilers.playbook_compiler import compile_playbook_cards, list_playbooks
from wilq.operator_labels import (
    action_count_label,
    evidence_count_label,
    knowledge_reference_count_label,
    missing_contract_labels,
    required_evidence_count_label,
    source_connector_labels,
    source_connector_summary_label,
    source_lineage_count_label,
)
from wilq.schemas import (
    ActionRisk,
    KnowledgeCard,
    KnowledgeDecisionBinding,
    KnowledgeOperatingMapResponse,
    MarketingPlaybook,
)
from wilq.workflows.models import Workflow
from wilq.workflows.registry import list_workflows


@dataclass(frozen=True)
class KnowledgeBindingBlueprint:
    workflow_id: str
    knowledge_card_ids: tuple[str, ...]
    playbook_ids: tuple[str, ...]
    expert_rule_ids: tuple[str, ...]


KNOWLEDGE_BINDINGS: tuple[KnowledgeBindingBlueprint, ...] = (
    KnowledgeBindingBlueprint(
        workflow_id="daily_command",
        knowledge_card_ids=("card_goal_001_rules",),
        playbook_ids=(),
        expert_rule_ids=(),
    ),
    KnowledgeBindingBlueprint(
        workflow_id="ads_daily_check",
        knowledge_card_ids=(
            "card_google_ads_search_playbook",
            "card_google_ads_budget_review_playbook",
            "card_google_ads_negative_keywords_playbook",
            "card_google_ads_custom_segments_playbook",
        ),
        playbook_ids=(
            "google_ads_search_playbook",
            "google_ads_budget_review_playbook",
            "google_ads_negative_keywords_playbook",
            "google_ads_custom_segments_playbook",
        ),
        expert_rule_ids=(
            "ads_diagnostics_v1",
            "ads_search_terms_v1",
            "ads_negative_keywords_v1",
            "ads_recommendations_v1",
            "ads_scaling_candidates_v1",
        ),
    ),
    KnowledgeBindingBlueprint(
        workflow_id="ads_custom_segments",
        knowledge_card_ids=("card_google_ads_custom_segments_playbook",),
        playbook_ids=("google_ads_custom_segments_playbook",),
        expert_rule_ids=("ads_custom_segments_v1", "ads_keyword_planner_v1"),
    ),
    KnowledgeBindingBlueprint(
        workflow_id="demand_gen_readiness",
        knowledge_card_ids=("card_google_ads_demand_gen_playbook",),
        playbook_ids=("google_ads_demand_gen_playbook",),
        expert_rule_ids=("ads_demand_gen_v1",),
    ),
    KnowledgeBindingBlueprint(
        workflow_id="merchant_feed_review",
        knowledge_card_ids=(
            "card_merchant_feed_optimization_playbook",
            "card_google_ads_pmax_playbook",
        ),
        playbook_ids=("merchant_feed_optimization_playbook", "google_ads_pmax_playbook"),
        expert_rule_ids=("merchant_feed_rules_v1", "merchant_product_diagnostics_v1"),
    ),
    KnowledgeBindingBlueprint(
        workflow_id="gsc_content_doctor",
        knowledge_card_ids=(
            "card_gsc_seo_content_playbook",
            "card_wordpress_content_refresh_playbook",
            "card_ahrefs_content_gap_playbook",
        ),
        playbook_ids=(
            "gsc_seo_content_playbook",
            "wordpress_content_refresh_playbook",
            "ahrefs_content_gap_playbook",
        ),
        expert_rule_ids=(
            "seo_gsc_opportunities_v1",
            "seo_query_page_matrix_v1",
            "seo_content_decay_v1",
            "seo_cannibalization_v1",
            "content_duplication_rules_v1",
            "content_brief_rules_v1",
        ),
    ),
    KnowledgeBindingBlueprint(
        workflow_id="content_calendar_builder",
        knowledge_card_ids=(
            "card_gsc_seo_content_playbook",
            "card_wordpress_content_refresh_playbook",
        ),
        playbook_ids=("gsc_seo_content_playbook", "wordpress_content_refresh_playbook"),
        expert_rule_ids=("content_brief_rules_v1", "content_voice_rules_v1"),
    ),
    KnowledgeBindingBlueprint(
        workflow_id="ga4_data_analyst",
        knowledge_card_ids=("card_ga4_behavior_diagnostics_playbook",),
        playbook_ids=("ga4_behavior_diagnostics_playbook",),
        expert_rule_ids=("ga4_diagnostics_v1",),
    ),
    KnowledgeBindingBlueprint(
        workflow_id="ahrefs_gap_finder",
        knowledge_card_ids=("card_ahrefs_content_gap_playbook",),
        playbook_ids=("ahrefs_content_gap_playbook",),
        expert_rule_ids=("content_brief_rules_v1",),
    ),
    KnowledgeBindingBlueprint(
        workflow_id="localo_visibility_review",
        knowledge_card_ids=("card_localo_local_seo_playbook",),
        playbook_ids=("localo_local_seo_playbook",),
        expert_rule_ids=("local_visibility_v1", "local_reviews_v1"),
    ),
    KnowledgeBindingBlueprint(
        workflow_id="social_publishing_queue",
        knowledge_card_ids=(
            "card_linkedin_content_playbook",
            "card_facebook_content_playbook",
        ),
        playbook_ids=("linkedin_content_playbook", "facebook_content_playbook"),
        expert_rule_ids=("linkedin_rules_v1", "facebook_rules_v1", "content_social_limits_v1"),
    ),
)


def build_knowledge_operating_map() -> KnowledgeOperatingMapResponse:
    cards = {card.id: card for card in compile_playbook_cards()}
    playbooks = {playbook.id: playbook for playbook in list_playbooks()}
    expert_rule_ids = {rule.id for rule in list_expert_rule_summaries()}
    workflows = {workflow.id: workflow for workflow in list_workflows()}

    bindings = [
        _binding_from_blueprint(blueprint, workflows, cards, playbooks, expert_rule_ids)
        for blueprint in KNOWLEDGE_BINDINGS
        if blueprint.workflow_id in workflows
    ]
    return KnowledgeOperatingMapResponse(
        source_card_count=len(cards),
        playbook_count=len(playbooks),
        expert_rule_count=len(expert_rule_ids),
        binding_count=len(bindings),
        bindings=sorted(bindings, key=_binding_sort_key),
    )


def _binding_from_blueprint(
    blueprint: KnowledgeBindingBlueprint,
    workflows: dict[str, Workflow],
    cards: dict[str, KnowledgeCard],
    playbooks: dict[str, MarketingPlaybook],
    expert_rule_ids: set[str],
) -> KnowledgeDecisionBinding:
    workflow = workflows[blueprint.workflow_id]
    valid_card_ids = [card_id for card_id in blueprint.knowledge_card_ids if card_id in cards]
    valid_playbook_ids = [
        playbook_id for playbook_id in blueprint.playbook_ids if playbook_id in playbooks
    ]
    valid_rule_ids = [
        rule_id for rule_id in blueprint.expert_rule_ids if rule_id in expert_rule_ids
    ]
    playbook_values = [playbooks[playbook_id] for playbook_id in valid_playbook_ids]
    card_values = [cards[card_id] for card_id in valid_card_ids]
    blocked_claims = _unique(workflow.blocked_claims)
    required_evidence = _unique(
        item for playbook in playbook_values for item in playbook.required_evidence
    )
    source_lineage = _unique(
        [
            *(line for card in card_values for line in card.source_lineage),
            *(playbook.source_path for playbook in playbook_values),
            *valid_rule_ids,
        ]
    )
    return KnowledgeDecisionBinding(
        id=f"knowledge_{workflow.id}",
        title=workflow.label,
        status=workflow.status,
        status_label=workflow.status_label or "",
        route=workflow.route or "/knowledge",
        route_label=workflow.route_label or "",
        skill_id=workflow.skill_id,
        summary=workflow.description,
        next_step=workflow.safe_next_step
        or "Użyj tej wiedzy tylko z dowodami WILQ i sprawdzeniem akcji.",
        source_connectors=workflow.source_connectors,
        source_connector_labels=source_connector_labels(workflow.source_connectors),
        source_connector_summary_label=source_connector_summary_label(workflow.source_connectors),
        evidence_ids=workflow.evidence_ids,
        evidence_summary_label=evidence_count_label(workflow.evidence_ids),
        action_ids=workflow.action_ids,
        action_summary_label=action_count_label(workflow.action_ids),
        metric_tiles=workflow.metric_tiles,
        knowledge_card_ids=valid_card_ids,
        playbook_ids=valid_playbook_ids,
        expert_rule_ids=valid_rule_ids,
        knowledge_summary_label=knowledge_reference_count_label(
            knowledge_card_ids=valid_card_ids,
            playbook_ids=valid_playbook_ids,
            expert_rule_ids=valid_rule_ids,
        ),
        required_evidence=required_evidence,
        required_evidence_summary_label=required_evidence_count_label(required_evidence),
        missing_contracts=workflow.missing_contracts,
        missing_contract_labels=missing_contract_labels(workflow.missing_contracts),
        blocked_claims=blocked_claims,
        blocked_claim_labels=operator_blocked_claims(blocked_claims),
        source_lineage=source_lineage,
        source_lineage_summary_label=source_lineage_count_label(source_lineage),
        risk=workflow.risk,
        risk_label=workflow.risk_label or "",
    )


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _binding_sort_key(binding: KnowledgeDecisionBinding) -> tuple[int, str]:
    priority = {
        "knowledge_daily_command": 0,
        "knowledge_merchant_feed_review": 10,
        "knowledge_gsc_content_doctor": 20,
        "knowledge_ga4_data_analyst": 30,
        "knowledge_ads_daily_check": 40,
    }.get(binding.id, 90)
    status_penalty = {"ready": 0, "blocked": 10, "planned": 20}.get(binding.status, 30)
    risk_penalty = {ActionRisk.low: 0, ActionRisk.medium: 1, ActionRisk.high: 2}.get(
        binding.risk,
        3,
    )
    return (priority + status_penalty + risk_penalty, binding.id)
