from __future__ import annotations

from typing import Any

from apps.api.wilq_api import context_actions, context_compaction, context_knowledge
from wilq.briefing.ads_diagnostics import build_ads_diagnostics
from wilq.briefing.content_diagnostics import build_content_diagnostics
from wilq.briefing.daily_runtime import build_daily_runtime
from wilq.briefing.ga4_diagnostics import build_ga4_diagnostics
from wilq.briefing.merchant_diagnostics import build_merchant_diagnostics
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.evidence.registry import list_evidence
from wilq.expert.rules import list_expert_capabilities, list_expert_rule_summaries
from wilq.knowledge.compilers.playbook_compiler import compile_playbook_cards
from wilq.schemas import ConnectorStatus, Opportunity
from wilq.security.redaction import redact_mapping


def full_context_pack(
    *,
    skill: str | None,
    connectors: list[ConnectorStatus],
    opportunities: list[Opportunity],
    max_opportunities: int,
    product_rules: list[str],
    strict_instruction: str,
) -> dict[str, Any]:
    active_actions = context_actions.full_context_actions_for_skill(skill)
    daily_runtime = build_daily_runtime()
    content_diagnostics = build_content_diagnostics().model_dump(mode="json")
    if skill in context_knowledge.CONTENT_KNOWLEDGE_SKILLS:
        content_cards, referenced_playbook_cards = context_knowledge.content_context_card_sets(
            skill, {"content_diagnostics": content_diagnostics}
        )
        knowledge_cards = [
            card.model_dump(mode="json") for card in content_cards
        ] + [card.model_dump(mode="json") for card in referenced_playbook_cards]
    else:
        knowledge_cards = [card.model_dump(mode="json") for card in compile_playbook_cards()]
    pack = {
        "current_product_rules": product_rules,
        "available_connectors": [connector.id for connector in connectors],
        "connector_status": [connector.model_dump(mode="json") for connector in connectors],
        "connector_consumer_readiness": context_compaction.connector_readiness_for_context(
            connectors
        ),
        "top_opportunities": [
            opportunity.model_dump(mode="json") for opportunity in opportunities[:max_opportunities]
        ],
        "active_action_objects": [action.model_dump(mode="json") for action in active_actions],
        "connector_refresh_runs": [
            run.model_dump(mode="json") for run in list_connector_refresh_runs()[:10]
        ],
        "evidence_summaries": [evidence.model_dump(mode="json") for evidence in list_evidence()],
        "knowledge_card_summaries": knowledge_cards,
        "expert_rule_summaries": [
            rule.model_dump(mode="json") for rule in list_expert_rule_summaries(limit=12)
        ],
        "expert_capabilities": [
            capability.model_dump(mode="json") for capability in list_expert_capabilities()
        ],
        "command_center": daily_runtime.command_center.model_dump(mode="json"),
        "marketing_brief": daily_runtime.marketing_brief.model_dump(mode="json"),
        "tactical_queue": build_tactical_queue().model_dump(mode="json"),
        "ads_diagnostics": build_ads_diagnostics().model_dump(mode="json"),
        "merchant_diagnostics": build_merchant_diagnostics().model_dump(mode="json"),
        "content_diagnostics": content_diagnostics,
        "ga4_diagnostics": build_ga4_diagnostics().model_dump(mode="json"),
        "strict_instruction": strict_instruction,
    }
    return redact_mapping(pack)
