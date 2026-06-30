from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.wilq_api import (
    context_action_payload,
    context_actions,
    context_ads,
    context_ahrefs,
    context_compaction,
    context_content,
    context_demand_gen,
    context_ga4,
    context_knowledge,
    context_marketing,
    context_merchant,
    context_trace,
)
from apps.api.wilq_api.context_cache import (
    clear_skill_context_cache,
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
from apps.api.wilq_api.routers.actions import create_actions_router
from apps.api.wilq_api.routers.codex import create_codex_router
from apps.api.wilq_api.routers.connectors import create_connectors_router
from apps.api.wilq_api.routers.demand_gen import create_demand_gen_router
from apps.api.wilq_api.routers.diagnostics import router as diagnostics_router
from apps.api.wilq_api.routers.evidence import router as evidence_router
from apps.api.wilq_api.routers.expert import router as expert_router
from apps.api.wilq_api.routers.jobs import router as jobs_router
from apps.api.wilq_api.routers.knowledge import router as knowledge_router
from apps.api.wilq_api.routers.metrics import router as metrics_router
from apps.api.wilq_api.routers.opportunities import router as opportunities_router
from apps.api.wilq_api.routers.system import router as system_router
from apps.api.wilq_api.routers.workflows import router as workflows_router
from wilq.briefing.ads_diagnostics import build_ads_diagnostics
from wilq.briefing.ahrefs_diagnostics import build_ahrefs_diagnostics
from wilq.briefing.content_diagnostics import (
    build_content_diagnostics,
    build_content_preflight,
)
from wilq.briefing.daily_runtime import (
    build_daily_runtime,
    clear_daily_runtime_cache,
)
from wilq.briefing.ga4_diagnostics import build_ga4_diagnostics
from wilq.briefing.localo_diagnostics import build_localo_diagnostics
from wilq.briefing.merchant_diagnostics import build_merchant_diagnostics
from wilq.briefing.tactical_queue import build_tactical_queue, clear_tactical_queue_cache
from wilq.connectors.refresh import list_connector_refresh_runs
from wilq.connectors.registry import list_connector_statuses
from wilq.evidence.registry import (
    list_evidence,
    list_evidence_by_ids,
)
from wilq.expert.rules import (
    list_expert_capabilities,
    list_expert_rule_summaries,
)
from wilq.knowledge.compilers.playbook_compiler import (
    compile_playbook_cards,
)
from wilq.operator_labels import (
    evidence_source_type_label,
    freshness_state_label,
    source_connector_label,
)
from wilq.opportunities.engine import list_opportunities
from wilq.schemas import (
    ActionObject,
    CommandCenterResponse,
    ConnectorStatus,
    DailyDecision,
    Evidence,
    ExpertCapability,
    ExpertRuleSummary,
    KnowledgeCard,
    Opportunity,
)
from wilq.security.redaction import redact_mapping

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5373",
    "http://127.0.0.1:5373",
)
LOCAL_CORS_ORIGIN_REGEX = r"^http://(localhost|127\.0\.0\.1):\d+$"


def cors_origins() -> list[str]:
    configured = os.getenv("WILQ_CORS_ORIGINS")
    if not configured:
        return list(DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app = FastAPI(title="WILQ Marketing API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_origin_regex=LOCAL_CORS_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(diagnostics_router)
app.include_router(evidence_router)
app.include_router(expert_router)
app.include_router(jobs_router)
app.include_router(knowledge_router)
app.include_router(metrics_router)
app.include_router(opportunities_router)
app.include_router(system_router)
app.include_router(workflows_router)

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "testclient", "testserver"}

CONTEXT_PRODUCT_RULES = [
    "Brak dowodu w WILQ -> brak rekomendacji.",
    "Brak źródła danych -> brak rekomendacji.",
    "Brak sprawdzonej akcji -> brak zapisu zmian.",
    "Brak audytu -> brak zapisu zmian.",
    "Brak odczytu z WILQ API -> Codex nie może podawać metryk.",
]
CONTEXT_STRICT_INSTRUCTION = (
    "Codex nie może podawać metryk bez odczytu z WILQ API i dowodów źródłowych."
)
DAILY_CONTEXT_EVIDENCE_SUMMARY_LIMIT = 32


@app.middleware("http")
async def require_local_api_access(request: Request, call_next: Any) -> Any:
    if os.getenv("WILQ_ALLOW_REMOTE_API") == "true":
        return await call_next(request)
    host = request.url.hostname
    if host not in LOCAL_HOSTS:
        return JSONResponse(
            status_code=403,
            content={"detail": "WILQ API is local-only by default."},
        )
    return await call_next(request)


def context_pack(request: ContextPackRequest | None = None) -> dict[str, Any]:
    skill = request_skill(request)
    if request and skill == "wilq-daily-command" and not request.full_context:
        return _daily_command_context_pack(request, list_opportunities())
    connectors = list_connector_statuses()
    opportunities = list_opportunities()
    max_opportunities = request.max_opportunities if request else 5
    if request and skill and skill != "wilq-daily-command" and not request.full_context:
        return _skill_scoped_context_pack(request, connectors, opportunities)
    active_actions = context_actions.full_context_actions_for_skill(skill)
    daily_runtime = build_daily_runtime()
    pack = {
        "current_product_rules": CONTEXT_PRODUCT_RULES,
        "available_connectors": [connector.id for connector in connectors],
        "connector_status": [connector.model_dump(mode="json") for connector in connectors],
        "top_opportunities": [
            opportunity.model_dump(mode="json") for opportunity in opportunities[:max_opportunities]
        ],
        "active_action_objects": [action.model_dump(mode="json") for action in active_actions],
        "connector_refresh_runs": [
            run.model_dump(mode="json") for run in list_connector_refresh_runs()[:10]
        ],
        "evidence_summaries": [evidence.model_dump(mode="json") for evidence in list_evidence()],
        "knowledge_card_summaries": [
            card.model_dump(mode="json") for card in compile_playbook_cards()
        ],
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
        "content_diagnostics": build_content_diagnostics().model_dump(mode="json"),
        "ga4_diagnostics": build_ga4_diagnostics().model_dump(mode="json"),
        "strict_instruction": CONTEXT_STRICT_INSTRUCTION,
    }
    return redact_mapping(pack)


def _daily_command_context_pack(
    request: ContextPackRequest,
    opportunities: list[Opportunity],
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
        "current_product_rules": CONTEXT_PRODUCT_RULES,
        "available_connectors": [connector.id for connector in connectors],
        "connector_status": [
            context_compaction.compact_connector_status_for_operator_context(connector)
            for connector in connectors
            if connector.id in source_connectors
        ],
        "top_opportunities": [
            _compact_opportunity_for_daily_context(opportunity)
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
            _compact_evidence_for_operator_context(evidence)
            for evidence in list_evidence_by_ids(sorted(evidence_ids))
        ][:DAILY_CONTEXT_EVIDENCE_SUMMARY_LIMIT],
        "knowledge_card_summaries": [
            _compact_knowledge_card_for_operator_context(card) for card in compile_playbook_cards()
        ],
        "expert_rule_summaries": [
            _compact_expert_rule_for_operator_context(rule)
            for rule in list_expert_rule_summaries(limit=12)
        ],
        "expert_capabilities": [
            _compact_expert_capability_for_operator_context(capability)
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
        "strict_instruction": CONTEXT_STRICT_INSTRUCTION,
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


def _compact_opportunity_for_daily_context(opportunity: Opportunity) -> dict[str, Any]:
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


def _compact_evidence_for_operator_context(evidence: Evidence) -> dict[str, Any]:
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


def _compact_knowledge_card_for_operator_context(card: KnowledgeCard) -> dict[str, Any]:
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


def _compact_expert_rule_for_operator_context(rule: ExpertRuleSummary) -> dict[str, Any]:
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


def _compact_expert_capability_for_operator_context(capability: ExpertCapability) -> dict[str, Any]:
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


def _skill_scoped_context_pack(
    request: ContextPackRequest,
    connectors: list[ConnectorStatus],
    opportunities: list[Opportunity],
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
        evidence_summary_limit = 50 if skill == "wilq-ads-doctor" else 40
    connector_refresh_run_limit = 2 if skill == "wilq-ads-doctor" else 3

    pack = {
        "context_scope": {
            "mode": "skill",
            "skill": skill,
            "full_context_available": True,
            "full_context_request": {"skill": skill, "full_context": True},
            "source_connectors": sorted(scoped_connectors),
        },
        "current_product_rules": CONTEXT_PRODUCT_RULES,
        "available_connectors": [connector.id for connector in connectors],
        "connector_status": [
            context_compaction.compact_connector_status_for_operator_context(connector)
            for connector in connectors
            if connector.id in scoped_connectors
        ],
        "top_opportunities": [
            _compact_opportunity_for_daily_context(opportunity)
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
            _compact_evidence_for_operator_context(evidence) for evidence in scoped_evidence
        ][:evidence_summary_limit],
        "knowledge_card_summaries": [
            _compact_knowledge_card_for_operator_context(card)
            for card in context_knowledge.knowledge_cards_for_skill(skill)
        ],
        "expert_rule_summaries": [
            _compact_expert_rule_for_operator_context(rule)
            for rule in context_knowledge.expert_rules_for_skill(skill)
        ],
        "expert_capabilities": [
            _compact_expert_capability_for_operator_context(capability)
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
        "strict_instruction": CONTEXT_STRICT_INSTRUCTION,
        **diagnostics,
    }
    pack = context_compaction.strip_raw_operator_context(pack)
    redacted_pack = redact_mapping(pack)
    write_skill_context_cache(request, redacted_pack)
    return redacted_pack


def clear_api_view_model_caches() -> None:
    clear_tactical_queue_cache()
    clear_daily_runtime_cache()
    clear_skill_context_cache()


app.include_router(create_actions_router(clear_api_view_model_caches))
app.include_router(create_connectors_router(clear_api_view_model_caches))
app.include_router(create_codex_router(context_pack))
app.include_router(create_demand_gen_router(context_demand_gen.build_readiness_contract))


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
