from __future__ import annotations

from typing import Any

from apps.api.wilq_api import (
    context_action_payload,
    context_compaction,
    context_marketing,
    context_trace,
)
from apps.api.wilq_api.context_models import ContextPackRequest
from wilq.briefing.daily_runtime import build_daily_runtime
from wilq.evidence.registry import list_evidence_by_ids
from wilq.expert.rules import list_expert_capabilities, list_expert_rule_summaries
from wilq.knowledge.compilers.playbook_compiler import compile_playbook_cards
from wilq.operator_labels import (
    evidence_source_type_label,
    freshness_state_label,
    source_connector_label,
)
from wilq.schemas import (
    ActionObject,
    CommandCenterResponse,
    DailyDecision,
    Evidence,
    ExpertCapability,
    ExpertRuleSummary,
    KnowledgeCard,
    Opportunity,
)
from wilq.security.redaction import redact_mapping

DAILY_CONTEXT_EVIDENCE_SUMMARY_LIMIT = 32


def daily_command_context_pack(
    request: ContextPackRequest,
    opportunities: list[Opportunity],
    *,
    product_rules: list[str],
    strict_instruction: str,
) -> dict[str, Any]:
    daily_runtime = build_daily_runtime()
    command = daily_runtime.command_center
    brief = daily_runtime.marketing_brief
    active_actions = daily_runtime.core_actions
    connectors = daily_runtime.connectors
    decisions_by_action_id = _daily_decisions_by_action_id(command.daily_decisions)
    evidence_ids = context_trace.daily_context_evidence_ids(command, brief, active_actions)
    source_connectors = context_trace.daily_context_connectors(command, brief, active_actions)
    scoped_opportunities = _daily_context_opportunities(
        opportunities,
        source_connectors,
        request.max_opportunities,
    )
    evidence_ids.update(
        evidence_id
        for opportunity in scoped_opportunities
        for evidence_id in opportunity.evidence_ids
    )

    pack = {
        "context_scope": {
            "mode": "daily",
            "skill": "wilq-daily-command",
            "full_context_available": True,
            "full_context_request": {
                "skill": "wilq-daily-command",
                "full_context": True,
            },
            "source_connectors": sorted(source_connectors),
        },
        "current_product_rules": product_rules,
        "available_connectors": [connector.id for connector in connectors],
        "connector_status": [
            context_compaction.compact_connector_status_for_operator_context(connector)
            for connector in connectors
            if connector.id in source_connectors
        ],
        "connector_consumer_readiness": context_compaction.connector_readiness_for_context(
            connectors,
            source_connectors,
        ),
        "top_opportunities": [
            compact_opportunity_for_daily_context(opportunity)
            for opportunity in scoped_opportunities
        ],
        "active_action_objects": [
            _compact_daily_action_for_context(
                action,
                decisions_by_action_id.get(action.id),
            )
            for action in active_actions
        ],
        "connector_refresh_runs": [
            _compact_refresh_run_for_daily_context(run.model_dump(mode="json"))
            for run in daily_runtime.refresh_runs[:30]
            if run.connector_id in source_connectors
        ][:6],
        "evidence_summaries": [
            compact_evidence_for_operator_context(evidence)
            for evidence in list_evidence_by_ids(sorted(evidence_ids))
        ][:DAILY_CONTEXT_EVIDENCE_SUMMARY_LIMIT],
        "knowledge_card_summaries": [
            compact_knowledge_card_for_operator_context(card) for card in compile_playbook_cards()
        ],
        "expert_rule_summaries": [
            compact_expert_rule_for_operator_context(rule)
            for rule in list_expert_rule_summaries(limit=12)
        ],
        "expert_capabilities": [
            compact_expert_capability_for_operator_context(capability)
            for capability in list_expert_capabilities()
        ],
        "command_center": _compact_command_center_for_daily_context(command),
        "marketing_brief": context_marketing.compact_marketing_brief_for_daily_context(brief),
        "context_pack_compaction": {
            "mode": "daily_default",
            "full_context_available": True,
            "full_context_request": {
                "skill": "wilq-daily-command",
                "full_context": True,
            },
            "active_actions_compacted": True,
            "command_center_connector_health_omitted": True,
            "command_center_daily_decisions_only": True,
            "marketing_brief_metric_facts_compacted": True,
            "connector_refresh_runs_compacted": True,
            "evidence_summaries_compacted": True,
            "knowledge_card_summaries_compacted": True,
            "expert_capabilities_compacted": True,
            "action_review_gates_compacted": True,
            "raw_history_omitted": True,
            "evidence_summaries_limit": DAILY_CONTEXT_EVIDENCE_SUMMARY_LIMIT,
            "full_action_endpoint_template": "/api/actions/{action_id}",
            "full_marketing_brief_endpoint": "/api/marketing/brief",
            "full_command_center_endpoint": "/api/dashboard/command-center",
        },
        "strict_instruction": strict_instruction,
    }
    pack = context_compaction.strip_raw_operator_context(pack)
    return redact_mapping(pack)


def _compact_daily_action_for_context(
    action: ActionObject,
    decision: DailyDecision | None = None,
) -> dict[str, Any]:
    dumped = action.model_dump(mode="json")
    audit_events = dumped.get("audit_events")
    latest_audit_event = context_compaction.compact_audit_event_for_daily_context(
        context_compaction.latest_audit_event(audit_events)
    )
    compact = {
        "id": dumped["id"],
        "title": dumped["title"],
        "domain": dumped["domain"],
        "connector": dumped["connector"],
        "mode": dumped["mode"],
        "risk": dumped["risk"],
        "status": dumped["status"],
        "validation_status": dumped["validation_status"],
        "review_gate": dumped["review_gate"],
        "evidence_ids": dumped["evidence_ids"],
        "human_diagnosis": dumped["human_diagnosis"],
        "recommended_reason": dumped["recommended_reason"],
        "metric_count": len(dumped.get("metrics", [])),
        "latest_audit_event": latest_audit_event,
        "api_endpoint_template": "/api/actions/{action_id}",
    }
    context_action_payload.compact_action_review_gate_for_context(compact)
    if decision is not None:
        compact.update(
            {
                "decision_id": decision.id,
                "decision_status": decision.status,
                "decision_title": decision.title,
                "human_diagnosis": context_compaction.first_context_sentence(decision.co_widzimy),
                "recommended_reason": decision.bezpieczny_next_step,
                "source_connectors": decision.source_connectors,
                "evidence_ids": decision.evidence_ids,
                "metric_tiles": decision.metric_tiles,
                "blocked_claims": decision.blocked_claims,
            }
        )
    return compact


def compact_opportunity_for_daily_context(opportunity: Opportunity) -> dict[str, Any]:
    dumped = opportunity.model_dump(mode="json")
    return {
        "id": dumped.get("id"),
        "title": dumped.get("title"),
        "domain": dumped.get("domain"),
        "type": dumped.get("type"),
        "severity": dumped.get("severity"),
        "risk": dumped.get("risk"),
        "summary": context_compaction.context_pack_text(dumped.get("summary"), limit=180),
        "next_step": context_compaction.context_pack_text(dumped.get("next_step"), limit=160),
        "source_connectors": dumped.get("source_connectors"),
        "evidence_ids": dumped.get("evidence_ids"),
        "action_ids": dumped.get("action_ids"),
        "blocked_claims": dumped.get("blocked_claims"),
    }


def _compact_refresh_run_for_daily_context(run: dict[str, Any]) -> dict[str, Any]:
    return context_compaction.compact_refresh_run_for_operator_context(run)


def compact_evidence_for_operator_context(evidence: Evidence) -> dict[str, Any]:
    dumped = evidence.model_dump(mode="json")
    freshness = dumped.get("freshness")
    freshness_state = None
    if isinstance(freshness, dict):
        freshness_state = freshness.get("state")
    source_connector = dumped.get("source_connector")
    source_type = dumped.get("source_type")
    source_label = source_connector_label(
        source_connector if isinstance(source_connector, str) else "unknown"
    )
    source_type_label = evidence_source_type_label(
        source_type if isinstance(source_type, str) else "unknown"
    )
    freshness_label = freshness_state_label(freshness_state)
    compact_freshness = {
        "state": freshness_state or "unknown",
        "checked_at": freshness.get("checked_at") if isinstance(freshness, dict) else None,
        "notes": None,
    }
    summary = (
        f"Dowód {dumped.get('id')}: źródło {source_label}, "
        f"typ {source_type_label}, świeżość {freshness_label}. "
        "Decyzję bierz z aktualnych diagnostyk WILQ."
    )
    return {
        "id": dumped.get("id"),
        "source_connector": dumped.get("source_connector"),
        "source_type": dumped.get("source_type"),
        "source_id": dumped.get("source_id"),
        "collected_at": dumped.get("collected_at"),
        "freshness": compact_freshness,
        "summary": summary,
        "raw_ref": None,
    }


def compact_knowledge_card_for_operator_context(card: KnowledgeCard) -> dict[str, Any]:
    dumped = card.model_dump(mode="json")
    card_type = dumped.get("card_type") or "knowledge"
    card_type_label = dumped.get("card_type_label") or "typ wiedzy do sprawdzenia"
    return {
        "id": dumped.get("id"),
        "card_type": card_type,
        "title": f"Karta wiedzy: {card_type_label}",
        "card_type_label": card_type_label,
        "summary": (
            "Skondensowana karta wiedzy. Używaj jej jako reguły pomocniczej; "
            "decyzje muszą wynikać z aktualnych diagnostyk WILQ, dowodów i źródeł danych."
        ),
        "source_type": dumped.get("source_type"),
        "source_type_label": dumped.get("source_type_label") or "źródło wiedzy do sprawdzenia",
        "source_id": dumped.get("source_id"),
        "source_url_or_path": dumped.get("source_url_or_path"),
        "extracted_at": dumped.get("extracted_at"),
        "confidence": dumped.get("confidence"),
        "last_seen_at": dumped.get("last_seen_at"),
        "source_lineage": [],
    }


def compact_content_knowledge_card_for_operator_context(card: Any) -> dict[str, Any]:
    """Expose real Ekologus source-fact cards without raw private material."""
    dumped = card.model_dump(mode="json")
    return {
        "id": dumped["id"],
        "card_type": dumped["card_type"],
        "title": dumped["title"],
        "summary": dumped["summary"],
        "lifecycle_status": dumped.get("lifecycle_status"),
        "confidence": dumped.get("confidence"),
        "freshness": dumped.get("freshness"),
        "source_fact_ids": dumped.get("source_fact_ids", []),
        "source_material_ids": dumped.get("source_material_ids", []),
        "evidence_ids": dumped.get("evidence_ids", []),
        "source_connectors": dumped.get("source_connectors", []),
        "source_lineage": dumped.get("source_lineage", []),
        "allowed_claims": dumped.get("allowed_claims", [])[:8],
        "claims_needing_review": [
            {
                "id": claim.get("id"),
                "status": claim.get("status"),
                "label": claim.get("label"),
                "reason": claim.get("reason"),
            }
            for claim in dumped.get("claims_needing_review", [])[:8]
        ],
        "forbidden_claims": [
            {
                "id": claim.get("id"),
                "status": claim.get("status"),
                "label": claim.get("label"),
                "reason": claim.get("reason"),
            }
            for claim in dumped.get("forbidden_claims", [])[:8]
        ],
    }


def compact_expert_rule_for_operator_context(rule: ExpertRuleSummary) -> dict[str, Any]:
    dumped = rule.model_dump(mode="json")
    return {
        "id": dumped.get("id"),
        "domain": dumped.get("domain"),
        "version": dumped.get("version"),
        "summary": (
            "Skondensowana reguła ekspercka. Używaj jej jako ograniczenia "
            "decyzji; szczegółowy kontrakt jest dostępny w API WILQ."
        ),
        "source_path": dumped.get("source_path"),
    }


def compact_expert_capability_for_operator_context(capability: ExpertCapability) -> dict[str, Any]:
    dumped = capability.model_dump(mode="json")
    required_mapping = dumped.get("required_mapping")
    required_mapping_total = len(required_mapping) if isinstance(required_mapping, list) else 0
    return {
        "id": dumped.get("id"),
        "domain": dumped.get("domain"),
        "source_rule_id": dumped.get("source_rule_id"),
        "required_inputs": [],
        "required_inputs_total": required_mapping_total,
        "output_contract": "Pełny kontrakt: /api/expert/capabilities.",
        "requires_evidence": dumped.get("requires_evidence", True),
    }


def _daily_decisions_by_action_id(decisions: list[DailyDecision]) -> dict[str, DailyDecision]:
    result: dict[str, DailyDecision] = {}
    for decision in sorted(decisions, key=lambda item: item.priority):
        for action_id in decision.action_ids:
            result.setdefault(action_id, decision)
    return result


def _compact_command_center_for_daily_context(command: CommandCenterResponse) -> dict[str, Any]:
    dumped = command.model_dump(mode="json")
    return {
        "generated_at": dumped["generated_at"],
        "strict_instruction": dumped["strict_instruction"],
        "primary_next_step": dumped["primary_next_step"],
        "blocker_count": dumped["blocker_count"],
        "tactical_item_count": dumped["tactical_item_count"],
        "source_connectors": dumped.get("source_connectors", []),
        "source_connector_labels": dumped.get("source_connector_labels", []),
        "evidence_ids": dumped.get("evidence_ids", []),
        "evidence_summary": dumped.get("evidence_summary", ""),
        "action_ids": dumped.get("action_ids", []),
        "action_summary": dumped.get("action_summary", ""),
        "daily_decisions": [
            _compact_daily_decision_for_context(decision)
            for decision in dumped["daily_decisions"]
            if isinstance(decision, dict)
        ],
        "connector_summary": dumped["connector_summary"],
    }


def _compact_daily_decision_for_context(decision: dict[str, Any]) -> dict[str, Any]:
    compact = dict(decision)
    metric_facts = compact.get("metric_facts")
    if isinstance(metric_facts, list):
        compact["metric_fact_count"] = len(metric_facts)
        compact["metric_facts"] = [
            context_compaction.compact_metric_fact_for_context(fact)
            for fact in metric_facts[:8]
            if isinstance(fact, dict)
        ]
        compact["metric_facts_included"] = len(compact["metric_facts"])
    return compact


def _daily_context_opportunities(
    opportunities: list[Opportunity],
    source_connectors: set[str],
    max_opportunities: int,
) -> list[Opportunity]:
    return [
        opportunity
        for opportunity in opportunities
        if context_trace.connectors_intersect(opportunity.source_connectors, source_connectors)
    ][:max_opportunities]
