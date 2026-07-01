from __future__ import annotations

from typing import Any

from apps.api.wilq_api import (
    context_action_payload,
    context_actions,
    context_ads,
    context_ahrefs,
    context_compaction,
    context_content,
    context_daily,
    context_demand_gen,
    context_ga4,
    context_knowledge,
    context_marketing,
    context_merchant,
    context_trace,
)
from apps.api.wilq_api.context_cache import (
    read_skill_context_cache,
    request_skill,
    write_skill_context_cache,
)
from apps.api.wilq_api.context_models import ContextPackRequest
from apps.api.wilq_api.context_scopes import (
    SKILL_ACTION_ID_SCOPES,
    SKILL_CONNECTOR_SCOPES,
    SKILL_KEYWORD_SCOPES,
)
from wilq.briefing.ads_diagnostics import build_ads_diagnostics
from wilq.briefing.ahrefs_diagnostics import build_ahrefs_diagnostics
from wilq.briefing.content_diagnostics import build_content_diagnostics, build_content_preflight
from wilq.briefing.daily_runtime import build_daily_runtime
from wilq.briefing.ga4_diagnostics import build_ga4_diagnostics
from wilq.briefing.localo_diagnostics import build_localo_diagnostics
from wilq.briefing.merchant_diagnostics import build_merchant_diagnostics
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.evidence.registry import list_evidence_by_ids
from wilq.expert.rules import list_expert_capabilities
from wilq.schemas import ConnectorStatus, Opportunity
from wilq.security.redaction import redact_mapping


def skill_scoped_context_pack(
    request: ContextPackRequest,
    connectors: list[ConnectorStatus],
    opportunities: list[Opportunity],
    *,
    product_rules: list[str],
    strict_instruction: str,
) -> dict[str, Any]:
    cached_pack = read_skill_context_cache(request)
    if cached_pack is not None:
        return cached_pack
    skill = request_skill(request) or "unknown"
    scoped_connectors = SKILL_CONNECTOR_SCOPES.get(skill, set())
    if not scoped_connectors:
        scoped_connectors = {connector.id for connector in connectors if connector.configured}
    max_opportunities = request.max_opportunities

    actions = context_actions.full_context_actions_for_skill(None)
    diagnostics = _diagnostics_for_skill(skill)
    actions = context_actions.skill_context_actions_for_skill(skill, actions, diagnostics)
    evidence_ids = context_trace.evidence_ids_from_context(
        diagnostics,
        actions,
        scoped_connectors,
    )
    scoped_actions = context_actions.actions_for_scope(actions, scoped_connectors)
    evidence_ids.update(
        evidence_id for action in scoped_actions for evidence_id in action.evidence_ids
    )
    if skill == "wilq-social-publisher":
        diagnostics["social_draft_context"] = context_marketing.social_draft_context_for_context(
            scoped_actions,
            connectors,
        )
    scoped_opportunities = _opportunities_for_skill_scope(
        skill,
        opportunities,
        scoped_connectors,
        max_opportunities,
    )
    evidence_ids.update(
        evidence_id
        for opportunity in scoped_opportunities
        for evidence_id in opportunity.evidence_ids
    )
    scoped_evidence = list_evidence_by_ids(sorted(evidence_ids))
    evidence_summary_limit = 80
    if skill in {"wilq-ads-doctor", "wilq-custom-segments"}:
        evidence_summary_limit = 1 if skill == "wilq-ads-doctor" else 40
    connector_refresh_run_limit = 2 if skill == "wilq-ads-doctor" else 3

    pack = {
        "context_scope": {
            "mode": "skill",
            "skill": skill,
            "full_context_available": True,
            "full_context_request": {"skill": skill, "full_context": True},
            "source_connectors": sorted(scoped_connectors),
        },
        "current_product_rules": product_rules,
        "available_connectors": [connector.id for connector in connectors],
        "connector_status": [
            context_compaction.compact_connector_status_for_operator_context(connector)
            for connector in connectors
            if connector.id in scoped_connectors
        ],
        "top_opportunities": [
            context_daily.compact_opportunity_for_daily_context(opportunity)
            for opportunity in scoped_opportunities
        ],
        "active_action_objects": [
            context_action_payload.compact_action_dump_for_context(
                action.model_dump(mode="json"), skill=skill
            )
            for action in scoped_actions
        ],
        "connector_refresh_runs": [
            context_compaction.compact_refresh_run_for_operator_context(run.model_dump(mode="json"))
            for run in list_connector_refresh_runs()[:25]
            if run.connector_id in scoped_connectors
        ][:connector_refresh_run_limit],
        "evidence_summaries": [
            context_daily.compact_evidence_for_operator_context(evidence)
            for evidence in scoped_evidence
        ][:evidence_summary_limit],
        "knowledge_card_summaries": [
            context_daily.compact_knowledge_card_for_operator_context(card)
            for card in context_knowledge.knowledge_cards_for_skill(skill)
        ],
        "expert_rule_summaries": [
            context_daily.compact_expert_rule_for_operator_context(rule)
            for rule in context_knowledge.expert_rules_for_skill(skill)
        ],
        "expert_capabilities": [
            context_daily.compact_expert_capability_for_operator_context(capability)
            for capability in list_expert_capabilities()
            if context_knowledge.text_matches_scope(
                [
                    capability.id,
                    capability.domain,
                    capability.source_rule_id,
                    capability.output_contract,
                ],
                SKILL_KEYWORD_SCOPES.get(skill, set()),
            )
        ],
        "context_pack_compaction": {
            "mode": "skill_default",
            "full_context_available": True,
            "full_context_request": {"skill": skill, "full_context": True},
            "connector_refresh_runs_compacted": True,
            "evidence_summaries_compacted": True,
            "knowledge_card_summaries_compacted": True,
            "expert_capabilities_compacted": True,
            "action_review_gates_compacted": True,
            "raw_history_omitted": True,
            "connector_refresh_runs_limit": connector_refresh_run_limit,
            "evidence_summaries_limit": evidence_summary_limit,
        },
        "strict_instruction": strict_instruction,
        **diagnostics,
    }
    pack = context_compaction.strip_raw_operator_context(pack)
    redacted_pack = redact_mapping(pack)
    write_skill_context_cache(request, redacted_pack)
    return redacted_pack


def _diagnostics_for_skill(skill: str) -> dict[str, Any]:
    if skill == "wilq-content-strategist":
        content = build_content_diagnostics()
        return {
            "content_diagnostics": context_content.compact_content_diagnostics_for_context(
                content.model_dump(mode="json")
            ),
            "content_preflight": build_content_preflight(content).model_dump(mode="json"),
        }
    if skill == "wilq-gsc-content-doctor":
        content = build_content_diagnostics()
        return {
            "content_diagnostics": context_content.compact_gsc_content_diagnostics_for_context(
                content.model_dump(mode="json")
            ),
            "content_preflight": build_content_preflight(content).model_dump(mode="json"),
        }
    if skill == "wilq-ahrefs-gap-finder":
        return {
            "ahrefs_diagnostics": context_ahrefs.compact_ahrefs_diagnostics_for_context(
                build_ahrefs_diagnostics().model_dump(mode="json")
            )
        }
    if skill == "wilq-ads-doctor":
        return {
            "ads_diagnostics": context_ads.compact_ads_diagnostics_for_context(
                build_ads_diagnostics(view="summary").model_dump(mode="json")
            )
        }
    if skill == "wilq-merchant-feed-operator":
        return {
            "merchant_diagnostics": context_merchant.compact_merchant_diagnostics_for_context(
                build_merchant_diagnostics().model_dump(mode="json")
            )
        }
    if skill == "wilq-ga4-analyst":
        return {
            "ga4_diagnostics": context_ga4.compact_ga4_diagnostics_for_context(
                build_ga4_diagnostics().model_dump(mode="json")
            )
        }
    if skill == "wilq-localo-operator":
        return {"localo_diagnostics": build_localo_diagnostics().model_dump(mode="json")}
    if skill == "wilq-demand-gen-operator":
        return context_demand_gen.demand_gen_diagnostics_for_context()
    if skill == "wilq-custom-segments":
        return {
            "ads_diagnostics": context_ads.custom_segments_diagnostics_for_context(
                build_ads_diagnostics().model_dump(mode="json")
            )
        }
    if skill == "wilq-campaign-builder":
        return {
            "ads_diagnostics": context_ads.compact_ads_diagnostics_for_lite_context(
                build_ads_diagnostics().model_dump(mode="json"),
                allowed_decision_ids={
                    "ads_review_campaign_activity",
                    "ads_review_budget_context",
                    "ads_block_write_actions_without_actionobject",
                },
                allowed_action_ids=SKILL_ACTION_ID_SCOPES["wilq-campaign-builder"],
            ),
            "content_landing_context": (
                context_content.content_landing_context_for_campaign_builder()
            ),
        }
    if skill == "wilq-social-publisher":
        runtime = build_daily_runtime()
        return {
            "marketing_brief": context_marketing.compact_marketing_brief_for_skill_context(
                runtime.marketing_brief,
                include_top_metric_facts=False,
            ),
            "tactical_queue": context_marketing.compact_tactical_queue_for_skill_context(
                build_tactical_queue()
            ),
        }
    return {"marketing_brief": build_daily_runtime().marketing_brief.model_dump(mode="json")}


def _opportunities_for_skill_scope(
    skill: str,
    opportunities: list[Opportunity],
    scoped_connectors: set[str],
    max_opportunities: int,
) -> list[Opportunity]:
    scoped = [
        opportunity
        for opportunity in opportunities
        if context_trace.connectors_intersect(opportunity.source_connectors, scoped_connectors)
    ]
    allowed_action_ids = SKILL_ACTION_ID_SCOPES.get(skill)
    if allowed_action_ids is None:
        return scoped[:max_opportunities]
    return [
        opportunity
        for opportunity in scoped
        if opportunity.action_ids and set(opportunity.action_ids).issubset(allowed_action_ids)
    ][:max_opportunities]
