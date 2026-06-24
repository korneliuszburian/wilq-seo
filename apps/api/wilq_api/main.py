from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass
from time import monotonic
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from wilq.actions.google_ads.business_context import (
    ADS_STRATEGY_REVIEW_ACTION_ID,
    ADS_TARGET_CONFIRMATION_ACTION_ID,
)
from wilq.actions.google_ads.demand_gen import (
    DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT,
    DEMAND_GEN_AD_READ_ROW_COUNT_FACT,
    DEMAND_GEN_AD_READ_STATUS_FACT,
    DEMAND_GEN_CAMPAIGN_ROWS_CONTRACT,
    DEMAND_GEN_CREATIVE_ASSET_ROW_COUNT_FACT,
    DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT,
    DEMAND_GEN_CREATIVE_ASSET_STATUS_FACT,
    DEMAND_GEN_LANDING_QUALITY_CONTRACT,
    DEMAND_GEN_MIGRATION_CONSTRAINTS_CONTRACT,
    DEMAND_GEN_READINESS_AVAILABLE_CONTRACT,
    DEMAND_GEN_READINESS_BLOCKED_CLAIMS,
    DEMAND_GEN_READINESS_REVIEW_ACTION_ID,
    demand_gen_ad_group_ad_rows_from_facts,
    demand_gen_contract_has_ready_fact,
    demand_gen_creative_asset_rows_from_facts,
    demand_gen_landing_quality_rows_from_facts,
    demand_gen_migration_constraint_rows_from_campaigns,
    demand_gen_readiness_review_payload,
)
from wilq.actions.google_ads.keyword_planner import KEYWORD_PLANNER_ACCESS_ACTION_ID
from wilq.actions.google_ads.search_term_ngrams import SEARCH_TERM_NGRAM_ACTION_ID
from wilq.actions.service import (
    apply_action,
    confirm_action,
    get_action,
    impact_check_action,
    list_actions,
    preview_action,
    record_action_review,
    validate_action,
)
from wilq.briefing.ads_diagnostics import build_ads_diagnostics
from wilq.briefing.ahrefs_diagnostics import build_ahrefs_diagnostics
from wilq.briefing.content_diagnostics import build_content_diagnostics
from wilq.briefing.daily_runtime import (
    build_daily_command_center,
    build_daily_marketing_brief,
    build_daily_runtime,
    clear_daily_runtime_cache,
)
from wilq.briefing.ga4_diagnostics import build_ga4_diagnostics
from wilq.briefing.localo_diagnostics import build_localo_diagnostics
from wilq.briefing.marketing_brief import core_brief_actions
from wilq.briefing.merchant_diagnostics import build_merchant_diagnostics
from wilq.briefing.tactical_queue import build_tactical_queue, clear_tactical_queue_cache
from wilq.codex.runtime_status import codex_runtime_status
from wilq.connectors.refresh import (
    get_connector_refresh_run,
    list_connector_refresh_runs,
    run_connector_refresh,
)
from wilq.connectors.registry import get_connector_status, list_connector_statuses
from wilq.credentials.runtime import credential_runtime_status
from wilq.evidence.registry import (
    connector_evidence_id,
    get_evidence,
    list_evidence,
    list_evidence_by_ids,
)
from wilq.expert.rules import (
    get_expert_rule,
    list_expert_capabilities,
    list_expert_rule_summaries,
    list_expert_rules,
)
from wilq.jobs.models import JobRun, JobRunRequest, ScheduledJob
from wilq.jobs.registry import get_job, list_jobs
from wilq.jobs.scheduler import (
    get_job_run,
    list_job_runs,
    run_job,
    scheduler_status,
)
from wilq.knowledge.compilers.playbook_compiler import (
    compile_playbook_cards,
    condense_playbooks,
    get_playbook,
    list_playbooks,
)
from wilq.knowledge.operating_map import build_knowledge_operating_map
from wilq.opportunities.engine import OPPORTUNITY_TYPES, get_opportunity, list_opportunities
from wilq.schemas import (
    ActionApplyRequest,
    ActionConfirmRequest,
    ActionImpactCheckRequest,
    ActionMutationAuditRecord,
    ActionObject,
    ActionPreviewRequest,
    ActionReviewRequest,
    AdsCampaignMetricRow,
    AdsDiagnosticsResponse,
    AdsStrategyReviewRecord,
    AdsTargetGuardrailConfirmation,
    AhrefsDiagnosticsResponse,
    AuditEvent,
    CodexRun,
    CommandCenterResponse,
    ConnectorRefreshRequest,
    ConnectorRefreshRun,
    ConnectorStatus,
    ConnectorSummary,
    ContentDiagnosticsResponse,
    DailyDecision,
    DemandGenReadinessContract,
    Evidence,
    ExpertCapability,
    ExpertRule,
    ExpertRuleSummary,
    Ga4DiagnosticsResponse,
    KnowledgeCard,
    KnowledgeCompilerResult,
    KnowledgeOperatingMapResponse,
    LocaloDiagnosticsResponse,
    MarketingBrief,
    MarketingPlaybook,
    MerchantDiagnosticsResponse,
    MetricFact,
    Opportunity,
    TacticalQueueResponse,
    utc_now,
)
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store
from wilq.workflows.models import WorkflowRun, WorkflowRunCreateRequest
from wilq.workflows.registry import list_workflows

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

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "testclient", "testserver"}
ADS_CONTEXT_ROW_LIMIT = 3
ADS_CONTEXT_NGRAM_ROW_LIMIT = 3
DEMAND_GEN_CHANNEL_TYPES = {"DEMAND_GEN", "DISCOVERY"}
DEMAND_GEN_CAMPAIGN_ROW_LIMIT = 8
ADS_CONTEXT_DECISION_ROW_LIMIT = 2
ADS_LITE_DECISION_LIMIT = 5
ACTION_CONTEXT_CAMPAIGN_CANDIDATE_LIMIT = 3
DEFAULT_SKILL_CONTEXT_CACHE_SECONDS = 5.0
_cached_skill_context_packs: dict[str, SkillContextCacheEntry] = {}


@dataclass(frozen=True)
class SkillContextCacheEntry:
    created_at: float
    payload: dict[str, Any]


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


class ContextPackRequest(BaseModel):
    skill: str | None = None
    focus: str | None = None
    max_opportunities: int = Field(default=5, ge=1, le=25)
    full_context: bool = False


def connector_summary(connectors: list[ConnectorStatus]) -> ConnectorSummary:
    missing = sum(1 for connector in connectors if connector.missing_credentials)
    configured = sum(1 for connector in connectors if connector.configured)
    return ConnectorSummary(
        total=len(connectors),
        configured=configured,
        missing_credentials=missing,
    )


def context_pack(request: ContextPackRequest | None = None) -> dict[str, Any]:
    skill = request.skill if request else None
    if request and skill == "wilq-daily-command" and not request.full_context:
        return _daily_command_context_pack(request, list_opportunities())
    connectors = list_connector_statuses()
    opportunities = list_opportunities()
    max_opportunities = request.max_opportunities if request else 5
    if request and skill and skill != "wilq-daily-command" and not request.full_context:
        return _skill_scoped_context_pack(request, connectors, opportunities)
    active_actions = _full_context_actions_for_skill(skill)
    daily_runtime = build_daily_runtime()
    pack = {
        "current_product_rules": [
            "No evidence ID -> no recommendation.",
            "No source connector -> no recommendation.",
            "No validated payload -> no apply.",
            "No audit event -> no write.",
            "No WILQ API call -> Codex must not invent metrics.",
        ],
        "available_connectors": [connector.id for connector in connectors],
        "connector_status": [connector.model_dump(mode="json") for connector in connectors],
        "top_opportunities": [
            opportunity.model_dump(mode="json") for opportunity in opportunities[:max_opportunities]
        ],
        "active_action_objects": [
            action.model_dump(mode="json") for action in active_actions
        ],
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
        "strict_instruction": "Codex must not invent metrics; fetch WILQ API evidence first.",
    }
    return redact_mapping(pack)


def _full_context_actions_for_skill(skill: str | None) -> list[ActionObject]:
    actions = list_actions()
    if skill == "wilq-daily-command":
        return core_brief_actions(actions)
    return actions


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
    evidence_ids = _daily_context_evidence_ids(command, brief, active_actions)
    source_connectors = _daily_context_connectors(command, brief, active_actions)
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
        "current_product_rules": [
            "No evidence ID -> no recommendation.",
            "No source connector -> no recommendation.",
            "No validated payload -> no apply.",
            "No audit event -> no write.",
            "No WILQ API call -> Codex must not invent metrics.",
        ],
        "available_connectors": [connector.id for connector in connectors],
        "connector_status": [
            connector.model_dump(mode="json")
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
            evidence.model_dump(mode="json")
            for evidence in list_evidence_by_ids(sorted(evidence_ids))
        ][:50],
        "knowledge_card_summaries": [
            card.model_dump(mode="json") for card in compile_playbook_cards()
        ],
        "expert_rule_summaries": [
            rule.model_dump(mode="json") for rule in list_expert_rule_summaries(limit=12)
        ],
        "expert_capabilities": [
            capability.model_dump(mode="json") for capability in list_expert_capabilities()
        ],
        "command_center": _compact_command_center_for_daily_context(command),
        "marketing_brief": _compact_marketing_brief_for_daily_context(brief),
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
            "full_action_endpoint_template": "/api/actions/{action_id}",
            "full_marketing_brief_endpoint": "/api/marketing/brief",
            "full_command_center_endpoint": "/api/dashboard/command-center",
        },
        "strict_instruction": "Codex must not invent metrics; fetch WILQ API evidence first.",
    }
    return redact_mapping(pack)


def _compact_daily_action_for_context(
    action: ActionObject,
    decision: DailyDecision | None = None,
) -> dict[str, Any]:
    dumped = action.model_dump(mode="json")
    payload = dumped.get("payload")
    payload_keys = sorted(payload) if isinstance(payload, dict) else []
    audit_events = dumped.get("audit_events")
    latest_audit_event = _latest_audit_event_for_context(audit_events)
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
        "payload_keys": payload_keys,
        "api_endpoint_template": "/api/actions/{action_id}",
    }
    _compact_action_review_gate_for_context(compact)
    if decision is not None:
        compact.update(
            {
                "decision_id": decision.id,
                "decision_status": decision.status,
                "decision_title": decision.title,
                "human_diagnosis": (
                    f"{decision.co_widzimy} {decision.dlaczego_to_ma_znaczenie}"
                ),
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
        "summary": _context_pack_text(dumped.get("summary"), limit=180),
        "next_step": _context_pack_text(dumped.get("next_step"), limit=160),
        "source_connectors": dumped.get("source_connectors"),
        "evidence_ids": dumped.get("evidence_ids"),
        "action_ids": dumped.get("action_ids"),
        "blocked_claims": dumped.get("blocked_claims"),
    }


def _compact_refresh_run_for_daily_context(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": run.get("id"),
        "connector_id": run.get("connector_id"),
        "mode": run.get("mode"),
        "status": run.get("status"),
        "started_at": run.get("started_at"),
        "completed_at": run.get("completed_at"),
        "summary": _context_pack_text(run.get("summary"), limit=180),
        "evidence_ids": run.get("evidence_ids"),
        "blocked_claims": run.get("blocked_claims"),
        "missing_credentials": run.get("missing_credentials"),
    }


def _latest_audit_event_for_context(audit_events: Any) -> dict[str, Any] | None:
    if not isinstance(audit_events, list):
        return None
    dict_events = [event for event in audit_events if isinstance(event, dict)]
    if not dict_events:
        return None
    return max(
        dict_events,
        key=lambda event: (str(event.get("created_at") or ""), str(event.get("id") or "")),
    )


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
        "daily_decisions": dumped["daily_decisions"],
        "connector_summary": dumped["connector_summary"],
    }


def _compact_marketing_brief_for_daily_context(brief: MarketingBrief) -> dict[str, Any]:
    dumped = brief.model_dump(mode="json")
    compact_sections = []
    for section in dumped["sections"]:
        compact_items = []
        for item in section["items"]:
            item_copy = dict(item)
            metric_facts = item_copy.get("metric_facts", [])
            item_copy["metric_fact_count"] = len(metric_facts)
            item_copy["metric_facts"] = [
                _compact_metric_fact_for_context(fact) for fact in metric_facts[:3]
            ]
            compact_items.append(item_copy)
        section_copy = dict(section)
        section_copy["items"] = compact_items
        compact_sections.append(section_copy)
    return {
        "generated_at": dumped["generated_at"],
        "language": dumped["language"],
        "strict_instruction": dumped["strict_instruction"],
        "connector_summary": dumped["connector_summary"],
        "sections": compact_sections,
        "top_metric_facts": [
            _compact_metric_fact_for_context(fact)
            for fact in dumped.get("top_metric_facts", [])[:8]
        ],
        "evidence_ids": dumped["evidence_ids"],
        "action_ids": dumped["action_ids"],
        "blocker_count": dumped["blocker_count"],
        "recommendation_count": dumped["recommendation_count"],
    }


def _compact_metric_fact_for_context(fact: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": fact.get("name"),
        "value": fact.get("value"),
        "unit": fact.get("unit"),
        "period": fact.get("period"),
        "source_connector": fact.get("source_connector"),
        "evidence_id": fact.get("evidence_id"),
        "dimensions": _compact_dimensions_for_context(fact.get("dimensions")),
        "freshness_label": fact.get("freshness_label"),
        "trend": fact.get("trend"),
    }


def _compact_dimensions_for_context(dimensions: Any) -> dict[str, str]:
    if not isinstance(dimensions, dict):
        return {}
    compact: dict[str, str] = {}
    for key, value in list(dimensions.items())[:8]:
        text = str(value)
        compact[str(key)] = text if len(text) <= 160 else f"{text[:157]}..."
    return compact


def _daily_context_evidence_ids(
    command: CommandCenterResponse,
    brief: MarketingBrief,
    actions: list[ActionObject],
) -> set[str]:
    evidence_ids = set(brief.evidence_ids)
    evidence_ids.update(_collect_values_by_key(command.model_dump(mode="json"), "evidence_ids"))
    for action in actions:
        evidence_ids.update(action.evidence_ids)
    return evidence_ids


def _daily_context_connectors(
    command: CommandCenterResponse,
    brief: MarketingBrief,
    actions: list[ActionObject],
) -> set[str]:
    source_connectors = set(
        _collect_values_by_key(command.model_dump(mode="json"), "source_connectors")
    )
    source_connectors.update(
        _collect_values_by_key(brief.model_dump(mode="json"), "source_connectors")
    )
    source_connectors.update(action.connector for action in actions)
    return source_connectors


def _daily_context_opportunities(
    opportunities: list[Opportunity],
    source_connectors: set[str],
    max_opportunities: int,
) -> list[Opportunity]:
    return [
        opportunity
        for opportunity in opportunities
        if _connectors_intersect(opportunity.source_connectors, source_connectors)
    ][:max_opportunities]


SKILL_CONNECTOR_SCOPES: dict[str, set[str]] = {
    "wilq-ads-doctor": {"google_ads"},
    "wilq-ahrefs-gap-finder": {"ahrefs", "google_search_console", "wordpress_ekologus"},
    "wilq-campaign-builder": {
        "google_ads",
        "google_analytics_4",
        "google_search_console",
    },
    "wilq-content-strategist": {
        "google_search_console",
        "google_analytics_4",
        "ahrefs",
        "wordpress_ekologus",
        "wordpress_sklep",
    },
    "wilq-custom-segments": {"google_ads", "google_search_console"},
    "wilq-demand-gen-operator": {
        "google_ads",
        "google_analytics_4",
    },
    "wilq-ga4-analyst": {"google_analytics_4", "wordpress_ekologus"},
    "wilq-gsc-content-doctor": {
        "google_search_console",
        "wordpress_ekologus",
        "wordpress_sklep",
    },
    "wilq-localo-operator": {"localo"},
    "wilq-merchant-feed-operator": {"google_merchant_center"},
    "wilq-social-publisher": {
        "facebook",
        "google_analytics_4",
        "google_merchant_center",
        "google_search_console",
        "linkedin",
        "wordpress_ekologus",
    },
}

SKILL_KEYWORD_SCOPES: dict[str, set[str]] = {
    "wilq-ads-doctor": {
        "ads",
        "budget",
        "google_ads",
        "negative",
        "recommendations",
        "scaling",
        "search",
        "pmax",
    },
    "wilq-ahrefs-gap-finder": {"ahrefs", "gap", "content", "seo"},
    "wilq-campaign-builder": {"ads", "campaign", "pmax", "search", "shopping"},
    "wilq-content-strategist": {"content", "seo", "gsc", "wordpress", "ahrefs"},
    "wilq-custom-segments": {"custom", "segment", "audience", "ads"},
    "wilq-demand-gen-operator": {"demand", "creative", "ga4", "ads"},
    "wilq-ga4-analyst": {"ga4", "analytics", "behavior", "landing"},
    "wilq-gsc-content-doctor": {"gsc", "seo", "content", "wordpress"},
    "wilq-localo-operator": {"localo", "local", "gbp"},
    "wilq-merchant-feed-operator": {"merchant", "feed", "shopping", "product"},
    "wilq-social-publisher": {"social", "linkedin", "facebook", "content"},
}

SKILL_KNOWLEDGE_CARD_IDS: dict[str, list[str]] = {
    "wilq-ads-doctor": [
        "card_google_ads_search_playbook",
        "card_google_ads_budget_review_playbook",
        "card_google_ads_negative_keywords_playbook",
        "card_google_ads_custom_segments_playbook",
        "card_goal_001_rules",
    ],
}

SKILL_ACTION_ID_SCOPES: dict[str, set[str]] = {
    "wilq-ads-doctor": {
        "act_prepare_ads_campaign_review_queue",
        "act_prepare_google_ads_recommendation_review_queue",
        "act_review_ads_change_history_impact",
        SEARCH_TERM_NGRAM_ACTION_ID,
        "act_prepare_custom_segments_from_search_terms",
        "act_prepare_negative_keyword_review_queue",
        ADS_TARGET_CONFIRMATION_ACTION_ID,
        ADS_STRATEGY_REVIEW_ACTION_ID,
        KEYWORD_PLANNER_ACCESS_ACTION_ID,
    },
    "wilq-ahrefs-gap-finder": set(),
    "wilq-campaign-builder": {
        "act_prepare_ads_campaign_review_queue",
        "act_prepare_google_ads_recommendation_review_queue",
    },
    "wilq-custom-segments": {
        "act_prepare_custom_segments_from_search_terms",
    },
    "wilq-demand-gen-operator": {DEMAND_GEN_READINESS_REVIEW_ACTION_ID},
}

SKILL_EXPERT_RULE_IDS: dict[str, list[str]] = {
    "wilq-ads-doctor": [
        "ads_diagnostics_v1",
        "ads_principles_v1",
        "ads_scaling_candidates_v1",
        "ads_recommendations_v1",
        "ads_search_terms_v1",
        "ads_negative_keywords_v1",
        "ads_custom_segments_v1",
        "ads_keyword_planner_v1",
    ],
}


def _skill_scoped_context_pack(
    request: ContextPackRequest,
    connectors: list[ConnectorStatus],
    opportunities: list[Opportunity],
) -> dict[str, Any]:
    cached_pack = _read_skill_context_cache(request)
    if cached_pack is not None:
        return cached_pack
    skill = request.skill or "unknown"
    scoped_connectors = SKILL_CONNECTOR_SCOPES.get(skill, set())
    if not scoped_connectors:
        scoped_connectors = {connector.id for connector in connectors if connector.configured}
    max_opportunities = request.max_opportunities

    actions = list_actions()
    diagnostics = _diagnostics_for_skill(skill)
    actions = _stateful_context_actions(skill, actions, diagnostics)
    actions = _actions_for_skill_scope(skill, actions)
    evidence_ids = _evidence_ids_from_context(diagnostics, actions, scoped_connectors)
    scoped_actions = _actions_for_scope(actions, scoped_connectors, evidence_ids)
    evidence_ids.update(
        evidence_id
        for action in scoped_actions
        for evidence_id in action.evidence_ids
    )
    if skill == "wilq-social-publisher":
        diagnostics["social_draft_context"] = _social_draft_context_for_context(
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
        "current_product_rules": [
            "No evidence ID -> no recommendation.",
            "No source connector -> no recommendation.",
            "No validated payload -> no apply.",
            "No audit event -> no write.",
            "No WILQ API call -> Codex must not invent metrics.",
        ],
        "available_connectors": [connector.id for connector in connectors],
        "connector_status": [
            connector.model_dump(mode="json")
            for connector in connectors
            if connector.id in scoped_connectors
        ],
        "top_opportunities": [
            opportunity.model_dump(mode="json") for opportunity in scoped_opportunities
        ],
        "active_action_objects": [
            _compact_action_dump_for_context(action.model_dump(mode="json"))
            for action in scoped_actions
        ],
        "connector_refresh_runs": [
            run.model_dump(mode="json")
            for run in list_connector_refresh_runs()[:25]
            if run.connector_id in scoped_connectors
        ][:connector_refresh_run_limit],
        "evidence_summaries": [
            evidence.model_dump(mode="json")
            for evidence in scoped_evidence
        ][:evidence_summary_limit],
        "knowledge_card_summaries": [
            card.model_dump(mode="json")
            for card in _knowledge_cards_for_skill(skill)
        ],
        "expert_rule_summaries": [
            rule.model_dump(mode="json")
            for rule in _expert_rules_for_skill(skill)
        ],
        "expert_capabilities": [
            capability.model_dump(mode="json")
            for capability in list_expert_capabilities()
            if _text_matches_scope(
                [
                    capability.id,
                    capability.domain,
                    capability.source_rule_id,
                    capability.output_contract,
                ],
                SKILL_KEYWORD_SCOPES.get(skill, set()),
            )
        ],
        "strict_instruction": "Codex must not invent metrics; fetch WILQ API evidence first.",
        **diagnostics,
    }
    redacted_pack = redact_mapping(pack)
    _write_skill_context_cache(request, redacted_pack)
    return redacted_pack


def clear_skill_context_cache() -> None:
    _cached_skill_context_packs.clear()


def clear_api_view_model_caches() -> None:
    clear_tactical_queue_cache()
    clear_daily_runtime_cache()
    clear_skill_context_cache()


def _read_skill_context_cache(request: ContextPackRequest) -> dict[str, Any] | None:
    cache_seconds = _skill_context_cache_seconds()
    if cache_seconds <= 0:
        return None
    cached = _cached_skill_context_packs.get(_skill_context_cache_key(request))
    if cached is None:
        return None
    if monotonic() - cached.created_at > cache_seconds:
        return None
    return cached.payload


def _write_skill_context_cache(request: ContextPackRequest, payload: dict[str, Any]) -> None:
    if _skill_context_cache_seconds() <= 0:
        return
    _cached_skill_context_packs[_skill_context_cache_key(request)] = SkillContextCacheEntry(
        created_at=monotonic(),
        payload=payload,
    )


def _skill_context_cache_key(request: ContextPackRequest) -> str:
    return "|".join(
        [
            request.skill or "",
            request.focus or "",
            str(request.max_opportunities),
        ]
    )


def _skill_context_cache_seconds() -> float:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return 0.0
    configured = os.getenv("WILQ_SKILL_CONTEXT_CACHE_SECONDS")
    if configured is None:
        return DEFAULT_SKILL_CONTEXT_CACHE_SECONDS
    try:
        return max(0.0, float(configured))
    except ValueError:
        return DEFAULT_SKILL_CONTEXT_CACHE_SECONDS


def _stateful_context_actions(
    skill: str,
    actions: list[ActionObject],
    diagnostics: dict[str, Any],
) -> list[ActionObject]:
    ads_diagnostics = diagnostics.get("ads_diagnostics")
    if (
        skill in {"wilq-ads-doctor", "wilq-custom-segments", "wilq-campaign-builder"}
        and isinstance(ads_diagnostics, dict)
        and ads_diagnostics.get("live_data_available") is True
    ):
        return [action for action in actions if action.id != "act_configure_google_ads_env"]
    return actions


def _actions_for_skill_scope(skill: str, actions: list[ActionObject]) -> list[ActionObject]:
    if skill not in SKILL_ACTION_ID_SCOPES:
        return actions
    allowed_action_ids = SKILL_ACTION_ID_SCOPES[skill]
    return [action for action in actions if action.id in allowed_action_ids]


def _diagnostics_for_skill(skill: str) -> dict[str, Any]:
    if skill == "wilq-content-strategist":
        return {
            "content_diagnostics": _compact_content_diagnostics_for_context(
                build_content_diagnostics().model_dump(mode="json")
            )
        }
    if skill == "wilq-gsc-content-doctor":
        return {
            "content_diagnostics": _compact_gsc_content_diagnostics_for_context(
                build_content_diagnostics().model_dump(mode="json")
            )
        }
    if skill == "wilq-ahrefs-gap-finder":
        return {"ahrefs_diagnostics": build_ahrefs_diagnostics().model_dump(mode="json")}
    if skill == "wilq-ads-doctor":
        return {
            "ads_diagnostics": _compact_ads_diagnostics_for_context(
                build_ads_diagnostics(view="summary").model_dump(mode="json")
            )
        }
    if skill == "wilq-merchant-feed-operator":
        return {
            "merchant_diagnostics": _compact_merchant_diagnostics_for_context(
                build_merchant_diagnostics().model_dump(mode="json")
            )
        }
    if skill == "wilq-ga4-analyst":
        return {
            "ga4_diagnostics": _compact_ga4_diagnostics_for_context(
                build_ga4_diagnostics().model_dump(mode="json")
            )
        }
    if skill == "wilq-localo-operator":
        return {"localo_diagnostics": build_localo_diagnostics().model_dump(mode="json")}
    if skill == "wilq-demand-gen-operator":
        return _demand_gen_diagnostics_for_context()
    if skill == "wilq-custom-segments":
        return {
            "ads_diagnostics": _custom_segments_diagnostics_for_context(
                build_ads_diagnostics().model_dump(mode="json")
            )
        }
    if skill == "wilq-campaign-builder":
        return {
            "ads_diagnostics": _compact_ads_diagnostics_for_lite_context(
                build_ads_diagnostics().model_dump(mode="json"),
                allowed_decision_ids={
                    "ads_review_campaign_activity",
                    "ads_review_budget_context",
                    "ads_block_write_actions_without_actionobject",
                },
                allowed_action_ids=SKILL_ACTION_ID_SCOPES["wilq-campaign-builder"],
            ),
            "content_landing_context": _content_landing_context_for_campaign_builder(),
        }
    if skill == "wilq-social-publisher":
        return {
            "marketing_brief": build_daily_runtime().marketing_brief.model_dump(mode="json"),
            "tactical_queue": build_tactical_queue().model_dump(mode="json"),
        }
    return {"marketing_brief": build_daily_runtime().marketing_brief.model_dump(mode="json")}


def _social_draft_context_for_context(
    actions: list[ActionObject],
    connectors: list[ConnectorStatus],
) -> dict[str, Any]:
    social_actions = sorted(
        [
            action
            for action in actions
            if action.id
            in {
                "act_prepare_facebook_social_drafts",
                "act_prepare_linkedin_social_drafts",
            }
        ],
        key=lambda action: action.id,
    )
    connector_status_by_id = {connector.id: connector for connector in connectors}
    missing_publish_permissions = {
        connector_id: connector_status_by_id[connector_id].missing_credentials
        for connector_id in ("linkedin", "facebook")
        if connector_id in connector_status_by_id
        and connector_status_by_id[connector_id].missing_credentials
    }
    candidate_inputs: list[dict[str, Any]] = []
    draft_constraints: list[str] = []
    blocked_claims = ["post published", "social performance uplift"]
    source_metric_names: list[str] = []
    source_connectors: list[str] = []
    evidence_ids: list[str] = []
    for action in social_actions:
        payload = action.payload
        if isinstance(payload, dict):
            candidate_inputs.extend(
                item
                for item in payload.get("candidate_inputs", [])
                if isinstance(item, dict)
            )
            draft_constraints.extend(
                str(item)
                for item in payload.get("draft_constraints", [])
                if item
            )
            blocked_claims.extend(
                str(item)
                for item in payload.get("blocked_claims", [])
                if item
            )
            source_metric_names.extend(
                str(item)
                for item in payload.get("source_metric_names", [])
                if item
            )
            source_connectors.extend(
                str(item)
                for item in payload.get("source_connectors", [])
                if item
            )
        evidence_ids.extend(action.evidence_ids)
    return {
        "mode": "review_only",
        "publish_allowed": False,
        "missing_publish_permissions": missing_publish_permissions,
        "draft_action_ids": [action.id for action in social_actions],
        "candidate_inputs": candidate_inputs[:8],
        "draft_constraints": sorted(set(draft_constraints)),
        "blocked_claims": sorted(set(blocked_claims)),
        "source_metric_names": sorted(set(source_metric_names)),
        "source_connectors": sorted(set(source_connectors)),
        "evidence_ids": list(dict.fromkeys(evidence_ids))[:12],
        "operator_next_step": (
            "Przygotuj szkice do review z evidence; publikacja pozostaje "
            "zablokowana do czasu konfiguracji LinkedIn/Facebook permissions."
        ),
    }


def _demand_gen_diagnostics_for_context() -> dict[str, Any]:
    demand_gen_metric_facts = _demand_gen_google_ads_metric_facts()
    ga4_metric_facts = _demand_gen_ga4_metric_facts()
    ads_diagnostics = build_ads_diagnostics().model_dump(mode="json")
    ga4_diagnostics = _demand_gen_ga4_diagnostics_from_metric_facts(ga4_metric_facts)
    return {
        "ads_diagnostics": _compact_ads_diagnostics_for_lite_context(
            ads_diagnostics,
            allowed_decision_ids={
                "ads_review_campaign_activity",
                "ads_review_budget_context",
                "ads_review_impression_share",
            },
            allowed_action_ids=SKILL_ACTION_ID_SCOPES["wilq-demand-gen-operator"],
        ),
        "ga4_diagnostics": _compact_ga4_diagnostics_for_context(ga4_diagnostics),
        "demand_gen_readiness": _demand_gen_readiness_contract(
            ads_diagnostics,
            ga4_diagnostics,
            demand_gen_metric_facts,
            ga4_metric_facts,
        ).model_dump(mode="json"),
    }


def _build_demand_gen_readiness_contract() -> DemandGenReadinessContract:
    demand_gen_metric_facts = _demand_gen_google_ads_metric_facts()
    ga4_metric_facts = _demand_gen_ga4_metric_facts()
    ads_diagnostics = build_ads_diagnostics().model_dump(mode="json")
    ga4_diagnostics = _demand_gen_ga4_diagnostics_from_metric_facts(ga4_metric_facts)
    return _demand_gen_readiness_contract(
        ads_diagnostics,
        ga4_diagnostics,
        demand_gen_metric_facts,
        ga4_metric_facts,
    )


def _demand_gen_ga4_diagnostics_from_metric_facts(
    ga4_metric_facts: list[MetricFact],
) -> dict[str, Any]:
    evidence_ids = list(
        dict.fromkeys(
            fact.evidence_id for fact in ga4_metric_facts if fact.evidence_id
        )
    )
    return {
        "source_connectors": ["google_analytics_4"],
        "evidence_ids": evidence_ids,
        "metric_fact_count": len(ga4_metric_facts),
        "context_pack_compaction": {
            "metric_facts_removed": True,
            "sections_omitted": True,
            "sections_total": 0,
            "full_endpoint": "/api/ga4/diagnostics",
        },
    }


def _demand_gen_readiness_contract(
    ads_diagnostics: dict[str, Any],
    ga4_diagnostics: dict[str, Any],
    demand_gen_metric_facts: list[MetricFact],
    ga4_metric_facts: list[MetricFact],
) -> DemandGenReadinessContract:
    campaign_rows = [
        row
        for row in _list_at(ads_diagnostics, "campaign_read_contract", "campaign_rows")
        if isinstance(row, dict)
    ]
    channel_counts = _campaign_channel_counts(campaign_rows)
    campaign_channel_read_available = any(
        str(row.get("advertising_channel_type") or "").strip() for row in campaign_rows
    )
    demand_gen_campaign_rows = [
        _compact_campaign_row_for_demand_gen(row)
        for row in campaign_rows
        if _is_demand_gen_channel(row.get("advertising_channel_type"))
    ][:DEMAND_GEN_CAMPAIGN_ROW_LIMIT]
    demand_gen_ad_group_ad_rows = demand_gen_ad_group_ad_rows_from_facts(
        demand_gen_metric_facts,
    )
    demand_gen_creative_asset_rows = demand_gen_creative_asset_rows_from_facts(
        demand_gen_metric_facts,
    )
    demand_gen_campaign_row_dicts = [
        row.model_dump(mode="json") for row in demand_gen_campaign_rows
    ]
    demand_gen_landing_quality_rows = demand_gen_landing_quality_rows_from_facts(
        ga4_metric_facts,
        demand_gen_campaign_row_dicts,
    )
    demand_gen_migration_constraint_rows = (
        demand_gen_migration_constraint_rows_from_campaigns(
            demand_gen_campaign_row_dicts,
        )
    )
    demand_gen_ad_read_available = demand_gen_contract_has_ready_fact(
        demand_gen_metric_facts,
        status_fact_name=DEMAND_GEN_AD_READ_STATUS_FACT,
        row_count_fact_name=DEMAND_GEN_AD_READ_ROW_COUNT_FACT,
    ) or bool(demand_gen_ad_group_ad_rows)
    demand_gen_creative_asset_read_available = demand_gen_contract_has_ready_fact(
        demand_gen_metric_facts,
        status_fact_name=DEMAND_GEN_CREATIVE_ASSET_STATUS_FACT,
        row_count_fact_name=DEMAND_GEN_CREATIVE_ASSET_ROW_COUNT_FACT,
    ) or bool(demand_gen_creative_asset_rows)
    evidence_ids = list(
        dict.fromkeys(
            [
                *(
                    fact.evidence_id
                    for fact in demand_gen_metric_facts
                    if fact.evidence_id and fact.name.startswith("demand_gen_")
                ),
                connector_evidence_id("google_ads"),
                connector_evidence_id("google_analytics_4"),
                *_top_level_evidence_ids(ads_diagnostics),
                *_top_level_evidence_ids(ga4_diagnostics),
            ]
        )
    )[:12]
    available_read_contracts = [
        "google_ads_campaign_activity",
        "google_ads_budget_context",
        "google_ads_impression_share_context",
        "ga4_landing_source_campaign_quality",
        DEMAND_GEN_READINESS_AVAILABLE_CONTRACT,
    ]
    missing_read_contracts = [
        DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT,
        DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT,
    ]
    if campaign_channel_read_available:
        available_read_contracts.append(DEMAND_GEN_CAMPAIGN_ROWS_CONTRACT)
        campaign_context = (
            f"WILQ ocenił {len(campaign_rows)} kampanii Ads z typami kanałów "
            f"({_format_channel_counts(channel_counts)}); "
            f"Demand Gen/Discovery rows={len(demand_gen_campaign_rows)}."
        )
    else:
        missing_read_contracts.insert(0, DEMAND_GEN_CAMPAIGN_ROWS_CONTRACT)
        campaign_context = (
            "WILQ nie ma jeszcze pewnego odczytu typów kanałów kampanii Ads."
        )
    if demand_gen_ad_read_available:
        available_read_contracts.append(DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT)
        missing_read_contracts = [
            contract
            for contract in missing_read_contracts
            if contract != DEMAND_GEN_AD_GROUP_AD_ROWS_CONTRACT
        ]
    if demand_gen_creative_asset_read_available:
        available_read_contracts.append(DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT)
        missing_read_contracts = [
            contract
            for contract in missing_read_contracts
            if contract != DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT
        ]
    available_read_contracts.extend(
        [
            DEMAND_GEN_LANDING_QUALITY_CONTRACT,
            DEMAND_GEN_MIGRATION_CONSTRAINTS_CONTRACT,
        ]
    )
    missing_contract_summary = ", ".join(missing_read_contracts) or "brak"
    title = (
        "Demand Gen: sprawdź istniejące kampanie bez launch/apply"
        if demand_gen_campaign_rows
        else "Demand Gen: brak kampanii do rekomendacji"
    )
    payload = demand_gen_readiness_review_payload(
        campaign_rows_evaluated=len(campaign_rows),
        campaign_channel_counts=channel_counts,
        demand_gen_campaign_rows=[
            row.model_dump(mode="json") for row in demand_gen_campaign_rows
        ],
        demand_gen_ad_group_ad_rows=[
            row.model_dump(mode="json") for row in demand_gen_ad_group_ad_rows
        ],
        demand_gen_creative_asset_rows=[
            row.model_dump(mode="json") for row in demand_gen_creative_asset_rows
        ],
        demand_gen_landing_quality_rows=[
            row.model_dump(mode="json") for row in demand_gen_landing_quality_rows
        ],
        demand_gen_migration_constraint_rows=[
            row.model_dump(mode="json") for row in demand_gen_migration_constraint_rows
        ],
        available_read_contracts=available_read_contracts,
        missing_read_contracts=missing_read_contracts,
        source_connectors=["google_ads", "google_analytics_4"],
        evidence_ids=evidence_ids,
    )
    action_ids = [DEMAND_GEN_READINESS_REVIEW_ACTION_ID] if payload is not None else []
    payload_preview = payload["payload_preview"] if payload is not None else []
    return DemandGenReadinessContract(
        status="blocked",
        title=title,
        summary=(
            f"{campaign_context} WILQ ma Ads i GA4 evidence do oceny ruchu, "
            "a Demand Gen ad/creative read contracts są dostępne, jeśli widnieją "
            "w available_read_contracts. "
            f"Nadal brakujące kontrakty: {missing_contract_summary}. "
            "To jest blocker użytecznej rekomendacji, nie brak promptu."
        ),
        metric_tiles={
            "kampanie Ads": len(campaign_rows),
            "kanały": len(channel_counts),
            "wiersze DG": len(demand_gen_campaign_rows),
            "reklamy DG": len(demand_gen_ad_group_ad_rows),
            "assety DG": len(demand_gen_creative_asset_rows),
            "landingi DG": len(demand_gen_landing_quality_rows),
            "ograniczenia": len(demand_gen_migration_constraint_rows),
            "braki": len(missing_read_contracts),
        },
        available_read_contracts=available_read_contracts,
        missing_read_contracts=missing_read_contracts,
        blocked_claims=DEMAND_GEN_READINESS_BLOCKED_CLAIMS,
        source_connectors=["google_ads", "google_analytics_4"],
        evidence_ids=evidence_ids,
        action_ids=action_ids,
        operator_review_gates=[
            "demand_gen_specific_evidence_required",
            "human_strategy_review",
            "human_confirm_before_apply",
        ],
        payload_preview=payload_preview,
        campaign_rows_evaluated=len(campaign_rows),
        campaign_channel_counts=channel_counts,
        demand_gen_campaign_rows=demand_gen_campaign_rows,
        demand_gen_ad_group_ad_rows=demand_gen_ad_group_ad_rows,
        demand_gen_creative_asset_rows=demand_gen_creative_asset_rows,
        demand_gen_landing_quality_rows=demand_gen_landing_quality_rows,
        demand_gen_migration_constraint_rows=demand_gen_migration_constraint_rows,
        next_step=(
            "Zwaliduj act_review_demand_gen_readiness jako review-only. Zanim skill "
            "pokaże kandydatów launchu albo migracji, sprawdź puste/niepuste "
            "read contracts landing quality i migration constraints."
        ),
    )


def _top_level_evidence_ids(diagnostics: dict[str, Any]) -> list[str]:
    evidence_ids = diagnostics.get("evidence_ids")
    if not isinstance(evidence_ids, list):
        return []
    return [str(evidence_id) for evidence_id in evidence_ids if evidence_id]


def _demand_gen_google_ads_metric_facts() -> list[MetricFact]:
    return metric_store().list_metric_facts(connector_id="google_ads", limit=5000)


def _demand_gen_ga4_metric_facts() -> list[MetricFact]:
    return metric_store().list_metric_facts(connector_id="google_analytics_4", limit=5000)


def _campaign_channel_counts(campaign_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in campaign_rows:
        channel = str(row.get("advertising_channel_type") or "UNKNOWN").strip()
        counts[channel or "UNKNOWN"] += 1
    return dict(sorted(counts.items()))


def _is_demand_gen_channel(channel: Any) -> bool:
    return str(channel or "").strip().upper() in DEMAND_GEN_CHANNEL_TYPES


def _format_channel_counts(channel_counts: dict[str, int]) -> str:
    if not channel_counts:
        return "brak kanałów"
    return ", ".join(f"{channel}={count}" for channel, count in channel_counts.items())


def _compact_campaign_row_for_demand_gen(row: dict[str, Any]) -> AdsCampaignMetricRow:
    return AdsCampaignMetricRow(
        campaign_id=row.get("campaign_id"),
        campaign_name=row.get("campaign_name") or "campaign",
        campaign_status=row.get("campaign_status"),
        advertising_channel_type=row.get("advertising_channel_type"),
        clicks=row.get("clicks"),
        impressions=row.get("impressions"),
        cost_micros=row.get("cost_micros"),
        conversions=row.get("conversions"),
        conversion_value=row.get("conversion_value"),
        evidence_ids=row.get("evidence_ids") or [],
        metric_facts=[],
        missing_metrics=row.get("missing_metrics") or [],
        blocked_claims=row.get("blocked_claims") or [],
    )


def _compact_content_diagnostics_for_context(
    content_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    compact = dict(_without_metric_facts(content_diagnostics))
    sections = compact.pop("sections", [])
    compact["context_pack_compaction"] = {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "sections_total": len(sections) if isinstance(sections, list) else 0,
        "full_endpoint": "/api/content/diagnostics",
    }
    return compact


def _compact_gsc_content_diagnostics_for_context(
    content_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    compact = _compact_content_diagnostics_for_context(content_diagnostics)
    decision_queue = compact.get("decision_queue")
    if isinstance(decision_queue, list):
        compact["decision_queue"] = [
            decision
            for decision in decision_queue
            if isinstance(decision, dict)
            and decision.get("decision_type") != "review_ahrefs_gap_records"
            and "ahrefs" not in decision.get("source_connectors", [])
        ]
    compact["evidence_ids"] = [
        evidence_id
        for evidence_id in compact.get("evidence_ids", [])
        if isinstance(evidence_id, str) and not _is_ahrefs_evidence_id(evidence_id)
    ]
    operator_summary = compact.get("operator_summary")
    if isinstance(operator_summary, dict):
        top_decision_ids = {
            str(decision.get("id"))
            for decision in compact.get("decision_queue", [])
            if isinstance(decision, dict) and decision.get("id")
        }
        operator_summary["top_decision_ids"] = [
            decision_id
            for decision_id in operator_summary.get("top_decision_ids", [])
            if decision_id in top_decision_ids
        ]
        operator_summary["source_connectors"] = [
            connector
            for connector in operator_summary.get("source_connectors", [])
            if connector != "ahrefs"
        ]
        operator_summary["evidence_ids"] = [
            evidence_id
            for evidence_id in operator_summary.get("evidence_ids", [])
            if isinstance(evidence_id, str) and not _is_ahrefs_evidence_id(evidence_id)
        ]
    compaction = compact.get("context_pack_compaction")
    if isinstance(compaction, dict):
        compaction["purpose"] = "gsc_content_doctor_context"
        compaction["ahrefs_decisions_removed"] = True
    return compact


def _is_ahrefs_evidence_id(evidence_id: str) -> bool:
    return "_ahrefs" in evidence_id


def _compact_ga4_diagnostics_for_context(
    ga4_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    compact = dict(_without_metric_facts(ga4_diagnostics))
    sections = compact.pop("sections", [])
    compact["context_pack_compaction"] = {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "sections_total": len(sections) if isinstance(sections, list) else 0,
        "full_endpoint": "/api/ga4/diagnostics",
    }
    return compact


def _compact_merchant_diagnostics_for_context(
    merchant_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    compact = dict(_without_metric_facts(merchant_diagnostics))
    sections = compact.pop("sections", [])
    compact["context_pack_compaction"] = {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "sections_total": len(sections) if isinstance(sections, list) else 0,
        "full_endpoint": "/api/merchant/diagnostics",
    }
    return compact


def _content_landing_context_for_campaign_builder() -> dict[str, Any]:
    diagnostics = build_content_diagnostics().model_dump(mode="json")
    diagnostic_candidates = [
        _campaign_builder_content_decision_candidate(decision)
        for decision in diagnostics.get("decision_queue", [])
        if isinstance(decision, dict)
        and "google_search_console" in decision.get("source_connectors", [])
        and decision.get("page")
        and (decision.get("primary_query") or decision.get("queries"))
        and decision.get("evidence_ids")
    ]
    if diagnostic_candidates:
        diagnostic_candidates.sort(
            key=lambda item: (
                _numeric_or_zero(item.get("impressions")),
                _numeric_or_zero(item.get("clicks")),
            ),
            reverse=True,
        )
        evidence_ids = sorted(
            {
                evidence_id
                for candidate in diagnostic_candidates
                for evidence_id in candidate["evidence_ids"]
            }
        )
        return _campaign_builder_landing_context(
            candidates=diagnostic_candidates,
            evidence_ids=evidence_ids,
            total_count=diagnostics.get("query_page_count", len(diagnostic_candidates)),
            source="content_decision_queue",
        )

    facts = [
        fact
        for fact in metric_store().list_metric_facts(
            connector_id="google_search_console",
            limit=500,
        )
        if {"query", "page"}.issubset(fact.dimensions)
    ]
    grouped: dict[tuple[str, str], list[MetricFact]] = {}
    for fact in facts:
        page = fact.dimensions.get("page")
        query = fact.dimensions.get("query")
        if page and query:
            grouped.setdefault((page, query), []).append(fact)

    candidates = [
        _campaign_builder_query_page_candidate(page, query, group_facts)
        for (page, query), group_facts in grouped.items()
    ]
    candidates.sort(
        key=lambda item: (
            _numeric_or_zero(item.get("impressions")),
            _numeric_or_zero(item.get("clicks")),
        ),
        reverse=True,
    )
    evidence_ids = sorted(
        {
            evidence_id
            for candidate in candidates
            for evidence_id in candidate["evidence_ids"]
        }
    )
    return _campaign_builder_landing_context(
        candidates=candidates,
        evidence_ids=evidence_ids,
        total_count=len(candidates),
        source="metric_facts",
    )


def _campaign_builder_landing_context(
    *,
    candidates: list[dict[str, Any]],
    evidence_ids: list[str],
    total_count: int,
    source: str,
) -> dict[str, Any]:
    return {
        "language": "pl-PL",
        "strict_instruction": (
            "WILQ pokazuje tylko metryki z API/evidence. Brak danych oznacza "
            "blocker, nie domysł marketingowy."
        ),
        "live_data_available": bool(candidates),
        "source_connectors": ["google_search_console"],
        "evidence_ids": evidence_ids,
        "query_page_candidate_count": len(candidates),
        "query_page_candidates": candidates[:8],
        "blocked_claims": [
            "campaign performance",
            "conversion uplift",
            "lead quality",
            "ranking guarantee",
        ],
        "context_pack_compaction": {
            "full_endpoint": "/api/content/diagnostics",
            "metric_facts_removed": True,
            "purpose": "landing_context",
            "source": source,
            "query_page_candidates_total": total_count,
            "query_page_candidates_included": len(candidates[:8]),
        },
    }


def _campaign_builder_content_decision_candidate(decision: dict[str, Any]) -> dict[str, Any]:
    queries = decision.get("queries")
    query = decision.get("primary_query")
    if not query and isinstance(queries, list) and queries:
        query = queries[0]
    return {
        "page": decision.get("page"),
        "query": query,
        "queries": queries if isinstance(queries, list) else [],
        "query_count": decision.get("query_count"),
        "decision_type": decision.get("decision_type"),
        "status": decision.get("status"),
        "next_step": decision.get("next_step"),
        "clicks": decision.get("total_clicks"),
        "impressions": decision.get("total_impressions"),
        "ctr": decision.get("aggregate_ctr"),
        "average_position": decision.get("best_average_position"),
        "wordpress_match": decision.get("wordpress_match"),
        "evidence_ids": decision.get("evidence_ids", []),
        "source_connectors": ["google_search_console"],
        "blocked_claims": decision.get(
            "blocked_claims",
            ["campaign performance", "conversion uplift", "ranking guarantee"],
        ),
    }


def _campaign_builder_query_page_candidate(
    page: str,
    query: str,
    facts: list[MetricFact],
) -> dict[str, Any]:
    return {
        "page": page,
        "query": query,
        "clicks": _metric_value(facts, "clicks"),
        "impressions": _metric_value(facts, "impressions"),
        "ctr": _metric_value(facts, "ctr"),
        "average_position": _metric_value(facts, "average_position"),
        "evidence_ids": sorted({fact.evidence_id for fact in facts if fact.evidence_id}),
        "source_connectors": ["google_search_console"],
        "blocked_claims": [
            "campaign performance",
            "conversion uplift",
            "ranking guarantee",
        ],
    }


def _metric_value(facts: list[MetricFact], name: str) -> float | int | str | None:
    for fact in facts:
        if fact.name == name:
            return fact.value
    return None


def _numeric_or_zero(value: Any) -> float:
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def _compact_ads_diagnostics_for_context(ads_diagnostics: dict[str, Any]) -> dict[str, Any]:
    compact = dict(_without_metric_facts(ads_diagnostics))
    _compact_latest_refresh_for_context(compact)
    campaign_rows = _list_at(compact, "campaign_read_contract", "campaign_rows")
    campaign_triage_rows = _list_at(
        compact,
        "campaign_triage_read_contract",
        "triage_rows",
    )
    kpi_rows = _list_at(compact, "derived_kpi_read_contract", "kpi_rows")
    budget_rows = _list_at(compact, "budget_pacing_read_contract", "budget_rows")
    search_term_rows = _list_at(
        compact,
        "search_terms_read_contract",
        "search_term_rows",
    )
    search_term_ngram_rows = _list_at(
        compact,
        "search_term_ngram_read_contract",
        "ngram_rows",
    )
    safety_rows = _list_at(
        compact,
        "search_term_safety_read_contract",
        "safety_rows",
    )
    keyword_context_rows = _list_at(
        compact,
        "keyword_match_context_read_contract",
        "context_rows",
    )
    recommendation_payload_preview = _list_at(
        compact,
        "recommendations_read_contract",
        "payload_preview",
    )
    custom_payload_preview = _list_at(
        compact,
        "custom_segments_read_contract",
        "payload_preview",
    )
    negative_payload_preview = _list_at(
        compact,
        "negative_keywords_read_contract",
        "payload_preview",
    )
    _limit_contract_rows(
        compact,
        ("campaign_read_contract", "campaign_rows"),
        ADS_CONTEXT_DECISION_ROW_LIMIT,
    )
    _limit_contract_rows(
        compact,
        ("campaign_triage_read_contract", "triage_rows"),
        ADS_CONTEXT_DECISION_ROW_LIMIT,
    )
    _compact_campaign_triage_rows_for_context(
        _list_at(compact, "campaign_triage_read_contract", "triage_rows")
    )
    _limit_contract_rows(
        compact,
        ("budget_pacing_read_contract", "budget_rows"),
        ADS_CONTEXT_ROW_LIMIT,
    )
    budget_payload_preview = _list_at(
        compact,
        "budget_pacing_read_contract",
        "payload_preview",
    )
    _limit_contract_rows(
        compact,
        ("budget_pacing_read_contract", "payload_preview"),
        ADS_CONTEXT_DECISION_ROW_LIMIT,
    )
    _compact_budget_apply_preview_for_context(
        _list_at(compact, "budget_pacing_read_contract", "payload_preview")
    )
    _compact_budget_row_payload_preview_for_context(
        _list_at(compact, "budget_pacing_read_contract", "budget_rows")
    )
    _limit_contract_rows(
        compact,
        ("search_terms_read_contract", "search_term_rows"),
        ADS_CONTEXT_ROW_LIMIT,
    )
    _limit_contract_rows(
        compact,
        ("search_term_ngram_read_contract", "ngram_rows"),
        ADS_CONTEXT_NGRAM_ROW_LIMIT,
    )
    _limit_contract_rows(
        compact,
        ("search_term_safety_read_contract", "safety_rows"),
        ADS_CONTEXT_ROW_LIMIT,
    )
    _limit_contract_rows(
        compact,
        ("keyword_match_context_read_contract", "context_rows"),
        ADS_CONTEXT_ROW_LIMIT,
    )
    _limit_contract_rows(
        compact,
        ("recommendations_read_contract", "payload_preview"),
        ADS_CONTEXT_ROW_LIMIT,
    )
    _limit_recommendation_rows_for_context(compact)
    _limit_contract_rows(
        compact,
        ("custom_segments_read_contract", "payload_preview"),
        ADS_CONTEXT_ROW_LIMIT,
    )
    _compact_custom_segment_payload_preview_for_context(compact)
    _limit_contract_rows(
        compact,
        ("negative_keywords_read_contract", "payload_preview"),
        ADS_CONTEXT_ROW_LIMIT,
    )
    _limit_contract_rows(
        compact,
        ("negative_keywords_read_contract", "candidates"),
        ADS_CONTEXT_DECISION_ROW_LIMIT,
    )
    _limit_candidate_rows(
        compact,
        ("custom_segments_read_contract", "candidates"),
        "search_term_rows",
        ADS_CONTEXT_ROW_LIMIT,
    )
    _limit_candidate_rows(
        compact,
        ("negative_keywords_read_contract", "candidates"),
        "keyword_context_rows",
        ADS_CONTEXT_DECISION_ROW_LIMIT,
    )
    _drop_candidate_nested_payload_preview(
        compact,
        ("custom_segments_read_contract", "candidates"),
    )
    _drop_candidate_keys(
        compact,
        ("custom_segments_read_contract", "candidates"),
        ("rejection_reasons",),
    )
    _drop_candidate_nested_payload_preview(
        compact,
        ("negative_keywords_read_contract", "candidates"),
    )
    _compact_ads_strategy_review_readiness_for_context(compact)
    _compact_ads_optimizer_readiness_for_context(compact)
    _limit_decision_rows(compact)
    _omit_decision_row_payloads(compact)
    _compact_ads_decision_queue_for_context(compact)
    sections = compact.pop("sections", [])
    compact["context_pack_compaction"] = {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "full_endpoint": "/api/ads/diagnostics",
        "sections_total": len(sections) if isinstance(sections, list) else 0,
        "decision_row_payloads_omitted": True,
        "campaign_rows_total": len(campaign_rows),
        "campaign_rows_included": len(
            _list_at(compact, "campaign_read_contract", "campaign_rows")
        ),
        "campaign_triage_rows_total": len(campaign_triage_rows),
        "campaign_triage_rows_included": len(
            _list_at(compact, "campaign_triage_read_contract", "triage_rows")
        ),
        "derived_kpi_rows_total": len(kpi_rows),
        "budget_rows_total": len(budget_rows),
        "budget_rows_included": len(
            _list_at(compact, "budget_pacing_read_contract", "budget_rows")
        ),
        "budget_payload_preview_total": len(budget_payload_preview),
        "budget_payload_preview_included": len(
            _list_at(compact, "budget_pacing_read_contract", "payload_preview")
        ),
        "search_term_rows_total": len(search_term_rows),
        "search_term_rows_included": len(
            _list_at(compact, "search_terms_read_contract", "search_term_rows")
        ),
        "search_term_ngram_rows_total": len(search_term_ngram_rows),
        "search_term_ngram_rows_included": len(
            _list_at(compact, "search_term_ngram_read_contract", "ngram_rows")
        ),
        "search_term_safety_rows_total": len(safety_rows),
        "search_term_safety_rows_included": len(
            _list_at(compact, "search_term_safety_read_contract", "safety_rows")
        ),
        "keyword_match_context_rows_total": len(keyword_context_rows),
        "keyword_match_context_rows_included": len(
            _list_at(compact, "keyword_match_context_read_contract", "context_rows")
        ),
        "recommendation_apply_preview_total": len(recommendation_payload_preview),
        "recommendation_apply_preview_included": len(
            _list_at(compact, "recommendations_read_contract", "payload_preview")
        ),
        "custom_segment_payload_preview_total": len(custom_payload_preview),
        "custom_segment_payload_preview_included": len(
            _list_at(compact, "custom_segments_read_contract", "payload_preview")
        ),
        "negative_keyword_payload_preview_total": len(negative_payload_preview),
        "negative_keyword_payload_preview_included": len(
            _list_at(compact, "negative_keywords_read_contract", "payload_preview")
        ),
        "negative_keyword_candidates_total": len(
            _list_at(ads_diagnostics, "negative_keywords_read_contract", "candidates")
        ),
        "negative_keyword_candidates_included": len(
            _list_at(compact, "negative_keywords_read_contract", "candidates")
        ),
        "optimizer_readiness_compacted": isinstance(
            compact.get("optimizer_readiness_contract"),
            dict,
        ),
    }
    return compact


def _compact_ads_strategy_review_readiness_for_context(data: dict[str, Any]) -> None:
    business_context = data.get("business_context_read_contract")
    if not isinstance(business_context, dict):
        return
    contract = business_context.get("strategy_review_readiness_contract")
    if not isinstance(contract, dict):
        return

    required_missing = [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas_or_cpa",
        "human_strategy_review",
        "approved_human_strategy_review",
    ]
    required_validation = [
        "review_profit_margin_model",
        "review_business_goal",
        "review_human_budget_goal",
        "confirm_target_roas_or_cpa",
        "human_strategy_review",
    ]
    required_blocked = [
        "profitability verdict",
        "target KPI verdict",
        "budget scaling",
        "budget apply",
        "recommendation apply",
        "automatic optimization",
    ]
    summary = _context_pack_text(contract.get("summary"), limit=170)
    next_step = _context_pack_text(contract.get("next_step"), limit=160)
    compact_contract = {
        key: contract.get(key)
        for key in (
            "id",
            "status",
            "latest_review_status",
            "latest_review_outcome",
            "apply_allowed",
            "destructive",
        )
        if key in contract
    }
    if summary is not None:
        compact_contract["summary"] = summary
    if next_step is not None:
        compact_contract["next_step"] = next_step
    compact_contract["current_context"] = contract.get("current_context")
    compact_contract["required_validation"] = _priority_limited_strings(
        contract.get("required_validation"),
        required_validation,
        limit=5,
    )
    compact_contract["missing_read_contracts"] = _priority_limited_strings(
        contract.get("missing_read_contracts"),
        required_missing,
        limit=6,
    )
    compact_contract["blocked_claims"] = _priority_limited_strings(
        contract.get("blocked_claims"),
        required_blocked,
        limit=6,
    )
    compact_contract["evidence_ids"] = _priority_limited_strings(
        contract.get("evidence_ids"),
        [],
        limit=4,
    )
    compact_contract["action_ids"] = _priority_limited_strings(
        contract.get("action_ids"),
        [ADS_STRATEGY_REVIEW_ACTION_ID],
        limit=2,
    )
    business_context["strategy_review_readiness_contract"] = compact_contract


def _compact_ads_optimizer_readiness_for_context(data: dict[str, Any]) -> None:
    contract = data.get("optimizer_readiness_contract")
    if not isinstance(contract, dict):
        return

    required_missing = [
        "change_event_rows",
        "pre_change_performance_window",
        "post_change_performance_window",
        "human_change_impact_review",
        "google_ads_mutation_audit",
        "human_confirm_before_apply",
    ]
    required_blocked = [
        "campaign mutation",
        "change impact",
        "budget apply",
        "negative keyword apply",
        "targeting applied",
    ]
    contract["allowed_metrics"] = _priority_limited_strings(
        contract.get("allowed_metrics"),
        ["clicks", "cost_micros", "conversions", "search_term", "change_event_available"],
        limit=8,
    )
    contract["missing_read_contracts"] = _priority_limited_strings(
        contract.get("missing_read_contracts"),
        required_missing,
        limit=10,
    )
    contract["operator_review_gates"] = _priority_limited_strings(
        contract.get("operator_review_gates"),
        ["human_strategy_review", "human_confirm_before_apply"],
        limit=6,
    )
    contract["blocked_claims"] = _priority_limited_strings(
        contract.get("blocked_claims"),
        required_blocked,
        limit=10,
    )
    contract["evidence_ids"] = _priority_limited_strings(
        contract.get("evidence_ids"),
        [],
        limit=4,
    )

    items = contract.get("readiness_items")
    if not isinstance(items, list):
        return

    compact_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        compact_item = {
            key: item.get(key)
            for key in (
                "id",
                "status",
                "source_contract_ids",
                "risk",
            )
            if key in item
        }
        if item.get("status") == "blocked":
            compact_item["next_step"] = _context_pack_text(
                item.get("next_step"),
                limit=150,
            )
        compact_item["source_contract_ids"] = _priority_limited_strings(
            item.get("source_contract_ids"),
            ["ads_change_history_read_contract", "ads_action_safety_contract"],
            limit=3,
        )
        if item.get("status") == "blocked":
            compact_item["missing_read_contracts"] = _priority_limited_strings(
                item.get("missing_read_contracts"),
                required_missing,
                limit=5,
            )
            compact_item["blocked_claims"] = _priority_limited_strings(
                item.get("blocked_claims"),
                required_blocked,
                limit=5,
            )
        compact_item["action_ids"] = _priority_limited_strings(
            item.get("action_ids"),
            [],
            limit=3,
        )
        compact_items.append(compact_item)
    contract["readiness_items_total"] = len(items)
    contract["readiness_items"] = compact_items


def _compact_ads_decision_queue_for_context(data: dict[str, Any]) -> None:
    required_blocked = [
        "campaign mutation",
        "change impact",
        "budget apply",
        "negative keyword apply",
        "targeting applied",
    ]
    required_missing = [
        "change_event_rows",
        "pre_change_performance_window",
        "post_change_performance_window",
        "human_confirm_before_apply",
    ]
    for decision in _list_at(data, "decision_queue"):
        if not isinstance(decision, dict):
            continue
        for key, limit in (
            ("summary", 120),
            ("rationale", 125),
            ("next_step", 135),
        ):
            compact_text = _context_pack_text(decision.get(key), limit=limit)
            if compact_text is not None:
                decision[key] = compact_text
        decision["allowed_metrics"] = _priority_limited_strings(
            decision.get("allowed_metrics"),
            ["clicks", "cost_micros", "conversions", "search_term", "change_event_available"],
            limit=4,
        )
        decision["missing_read_contracts"] = _priority_limited_strings(
            decision.get("missing_read_contracts"),
            required_missing,
            limit=5,
        )
        decision["operator_review_gates"] = _priority_limited_strings(
            decision.get("operator_review_gates"),
            ["human_strategy_review", "human_confirm_before_apply"],
            limit=3,
        )
        decision["blocked_claims"] = _priority_limited_strings(
            decision.get("blocked_claims"),
            required_blocked,
            limit=5,
        )
        decision["evidence_ids"] = _priority_limited_strings(
            decision.get("evidence_ids"),
            [],
            limit=4,
        )
        decision["action_ids"] = _priority_limited_strings(
            decision.get("action_ids"),
            [],
            limit=4,
        )


def _priority_limited_strings(value: Any, required: list[str], limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in [*required, *value]:
        if not isinstance(item, str) or item in result:
            continue
        if item not in value:
            continue
        result.append(item)
        if len(result) >= limit:
            break
    return result


def _context_pack_text(value: Any, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3]}..."


def _compact_budget_row_payload_preview_for_context(rows: list[Any]) -> None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        payload_preview = row.get("payload_preview")
        if isinstance(payload_preview, dict):
            safety_review = payload_preview.get("safety_review")
            row["payload_preview"] = {
                "id": payload_preview.get("id"),
                "operation_type": payload_preview.get("operation_type"),
                "apply_allowed": payload_preview.get("apply_allowed"),
                "safety_contract": safety_review.get("safety_contract")
                if isinstance(safety_review, dict)
                else None,
                "safety_status": safety_review.get("status")
                if isinstance(safety_review, dict)
                else None,
            }


def _compact_campaign_triage_rows_for_context(rows: list[Any]) -> None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        compact_row = {
            "campaign_id": row.get("campaign_id"),
            "campaign_name": row.get("campaign_name"),
            "review_priority": row.get("review_priority"),
            "review_score": row.get("review_score"),
            "target_status": row.get("target_status"),
            "clicks": row.get("clicks"),
            "cost_micros": row.get("cost_micros"),
            "conversions": row.get("conversions"),
            "roas": row.get("roas"),
            "spend_to_budget_ratio_7d": row.get("spend_to_budget_ratio_7d"),
            "search_budget_lost_impression_share": row.get(
                "search_budget_lost_impression_share"
            ),
            "recommendation_count": row.get("recommendation_count"),
            "has_budget_apply_preview": row.get("has_budget_apply_preview"),
            "has_recommendation_apply_preview": row.get(
                "has_recommendation_apply_preview"
            ),
            "next_step": row.get("next_step"),
            "evidence_ids": row.get("evidence_ids"),
            "action_ids": row.get("action_ids"),
            "blocked_claims": row.get("blocked_claims"),
        }
        row.clear()
        row.update({key: value for key, value in compact_row.items() if value is not None})


def _compact_budget_apply_preview_for_context(preview_items: list[Any]) -> None:
    for index, item in enumerate(preview_items):
        if isinstance(item, dict):
            preview_items[index] = _compact_budget_apply_preview_item(item)


def _compact_budget_apply_preview_item(item: dict[str, Any]) -> dict[str, Any]:
    compact_item = {
        key: item.get(key)
        for key in (
            "id",
            "campaign_id",
            "campaign_name",
            "campaign_budget_id",
            "campaign_budget_name",
            "operation_type",
            "current_budget_amount_micros",
            "proposed_budget_amount_micros",
            "proposed_budget_delta_micros",
            "evidence_ids",
            "api_mutation_ready",
            "apply_allowed",
            "destructive",
        )
        if key in item
    }
    required_validation = item.get("required_validation")
    if isinstance(required_validation, list):
        compact_item["required_validation_total"] = len(required_validation)
    blocked_claims = item.get("blocked_claims")
    if isinstance(blocked_claims, list):
        compact_item["blocked_claims"] = blocked_claims[:4]
    safety_review = item.get("safety_review")
    if isinstance(safety_review, dict):
        compact_item["safety_review"] = _compact_budget_safety_review_item(
            safety_review
        )
    return compact_item


def _compact_budget_safety_review_item(item: dict[str, Any]) -> dict[str, Any]:
    compact_item = {
        key: item.get(key)
        for key in (
            "id",
            "safety_contract",
            "status",
            "reason",
            "max_allowed_delta_percent",
            "proposed_delta_percent",
            "missing_requirements",
            "api_mutation_ready",
            "apply_allowed",
            "destructive",
        )
        if key in item
    }
    required_validation = item.get("required_validation")
    if isinstance(required_validation, list):
        compact_item["required_validation_total"] = len(required_validation)
    blocked_claims = item.get("blocked_claims")
    if isinstance(blocked_claims, list):
        compact_item["blocked_claims"] = blocked_claims[:4]
    return compact_item


def _compact_latest_refresh_for_context(compact: dict[str, Any]) -> None:
    latest_refresh = compact.get("latest_refresh")
    if not isinstance(latest_refresh, dict):
        return
    compact["latest_refresh"] = {
        key: latest_refresh.get(key)
        for key in (
            "id",
            "connector_id",
            "mode",
            "status",
            "completed_at",
            "evidence_ids",
            "external_call_attempted",
            "vendor_data_collected",
            "summary",
        )
        if key in latest_refresh
    }


def _compact_ads_diagnostics_for_lite_context(
    ads_diagnostics: dict[str, Any],
    *,
    allowed_decision_ids: set[str],
    allowed_action_ids: set[str] | None = None,
    extra_keep_contracts: set[str] | None = None,
) -> dict[str, Any]:
    compact = _compact_ads_diagnostics_for_context(ads_diagnostics)
    decision_queue = compact.get("decision_queue")
    if isinstance(decision_queue, list):
        compact["decision_queue"] = [
            decision
            for decision in decision_queue
            if isinstance(decision, dict)
            and str(decision.get("id")) in allowed_decision_ids
        ][:ADS_LITE_DECISION_LIMIT]
    if allowed_action_ids is not None:
        action_ids = compact.get("action_ids")
        if isinstance(action_ids, list):
            compact["action_ids"] = [
                action_id
                for action_id in action_ids
                if isinstance(action_id, str) and action_id in allowed_action_ids
            ]
        decision_queue = compact.get("decision_queue")
        if isinstance(decision_queue, list):
            for decision in decision_queue:
                if not isinstance(decision, dict):
                    continue
                decision_action_ids = decision.get("action_ids")
                if isinstance(decision_action_ids, list):
                    decision["action_ids"] = [
                        action_id
                        for action_id in decision_action_ids
                        if isinstance(action_id, str) and action_id in allowed_action_ids
                    ]
    keep_contracts = {
        "generated_at",
        "language",
        "strict_instruction",
        "latest_refresh",
        "live_data_available",
        "blocked_handoff",
        "campaign_read_contract",
        "business_context_read_contract",
        "derived_kpi_read_contract",
        "budget_pacing_read_contract",
        "impression_share_read_contract",
        "action_ids",
        "evidence_ids",
        "blocker_count",
        "decision_queue",
        "context_pack_compaction",
    }
    if extra_keep_contracts:
        keep_contracts.update(extra_keep_contracts)
    for key in list(compact):
        if key not in keep_contracts:
            compact.pop(key, None)
    compaction = compact.get("context_pack_compaction")
    if isinstance(compaction, dict):
        decision_queue = compact.get("decision_queue")
        compaction["lite_context"] = True
        compaction["omitted_contracts"] = [
            contract
            for contract in [
                "change_history_read_contract",
                "custom_segments_read_contract",
                "keyword_match_context_read_contract",
                "negative_keywords_read_contract",
                "recommendations_read_contract",
                "search_term_safety_read_contract",
                "search_terms_read_contract",
                "sections",
            ]
            if contract not in keep_contracts
        ]
        compaction["decision_rows_included"] = len(
            decision_queue if isinstance(decision_queue, list) else []
        )
    return compact


def _custom_segments_diagnostics_for_context(
    ads_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    compact = _compact_ads_diagnostics_for_lite_context(
        ads_diagnostics,
        allowed_decision_ids={"ads_prepare_custom_segments_from_search_terms"},
        allowed_action_ids=SKILL_ACTION_ID_SCOPES["wilq-custom-segments"],
        extra_keep_contracts={
            "custom_segments_read_contract",
            "search_terms_read_contract",
        },
    )
    keep_contracts = {
        "generated_at",
        "language",
        "strict_instruction",
        "latest_refresh",
        "live_data_available",
        "blocked_handoff",
        "search_terms_read_contract",
        "custom_segments_read_contract",
        "action_ids",
        "evidence_ids",
        "blocker_count",
        "decision_queue",
        "context_pack_compaction",
    }
    for key in list(compact):
        if key not in keep_contracts:
            compact.pop(key, None)
    compaction = compact.get("context_pack_compaction")
    if isinstance(compaction, dict):
        compaction["purpose"] = "custom_segments_context"
        compaction["omitted_contracts"] = [
            contract
            for contract in [
                "business_context_read_contract",
                "campaign_read_contract",
                "derived_kpi_read_contract",
                "budget_pacing_read_contract",
                "impression_share_read_contract",
                "change_history_read_contract",
                "keyword_match_context_read_contract",
                "negative_keywords_read_contract",
                "recommendations_read_contract",
                "search_term_safety_read_contract",
                "sections",
            ]
            if contract not in keep_contracts
        ]
    return compact


def _compact_action_dump_for_context(action: dict[str, Any]) -> dict[str, Any]:
    compact = dict(action)
    if compact.get("id") == KEYWORD_PLANNER_ACCESS_ACTION_ID:
        compact["human_diagnosis"] = (
            "Keyword Planner enrichment jest zablokowany przez Google Ads API."
        )
        compact["recommended_reason"] = (
            "Odblokuj developer token przed forecast, audience size i Keyword Planner claims."
        )
        review_gate = compact.get("review_gate")
        if isinstance(review_gate, dict):
            apply_blockers = review_gate.get("apply_blockers")
            if not isinstance(apply_blockers, list):
                apply_blockers = []
            compact["review_gate"] = {
                "status": review_gate.get("status"),
                "apply_allowed": review_gate.get("apply_allowed"),
                "confirmation_required": review_gate.get("confirmation_required"),
                "apply_blockers_total": len(apply_blockers),
                "apply_blockers": apply_blockers[:4],
                "apply_blockers_included": min(len(apply_blockers), 4),
            }
    if compact.get("id") == SEARCH_TERM_NGRAM_ACTION_ID:
        compact["human_diagnosis"] = (
            "N-gram review z Google Ads search-term evidence; nie apply."
        )
        compact["recommended_reason"] = (
            "Sprawdź intencję tematów i próbki zapytań przed negative keyword queue."
        )
        compact["evidence_ids"] = compact.get("evidence_ids", [])[:1]
    _compact_action_review_gate_for_context(compact)
    metrics = compact.get("metrics")
    if isinstance(metrics, list):
        compact["metrics_total"] = len(metrics)
        compact["metrics"] = [] if compact.get("id") == SEARCH_TERM_NGRAM_ACTION_ID else metrics[:1]
        compact["metrics_included"] = len(compact["metrics"])
    payload = compact.get("payload")
    if not isinstance(payload, dict):
        return compact
    compact_payload = dict(payload)
    if compact.get("id") == KEYWORD_PLANNER_ACCESS_ACTION_ID:
        compact_payload["blocked_reason"] = "PERMISSION_DENIED: DEVELOPER_TOKEN_NOT_APPROVED"
        helper_steps = compact_payload.get("helper_steps")
        if isinstance(helper_steps, list):
            compact_payload["helper_steps_total"] = len(helper_steps)
            compact_payload["helper_steps"] = helper_steps[:1]
            compact_payload["helper_steps_included"] = len(compact_payload["helper_steps"])
    campaign_candidates = compact_payload.get("campaign_candidates")
    if isinstance(campaign_candidates, list):
        compact_payload["campaign_candidates_total"] = len(campaign_candidates)
        compact_payload["campaign_candidates"] = _compact_campaign_candidates_for_context(
            campaign_candidates
        )
        compact_payload["campaign_candidates_included"] = len(
            compact_payload["campaign_candidates"]
        )
    content_brief_preview = compact_payload.get("content_brief_preview")
    if isinstance(content_brief_preview, list):
        compact_payload["content_brief_preview_total"] = len(content_brief_preview)
        compact_payload["content_brief_preview"] = (
            _compact_content_brief_preview_for_context(content_brief_preview)
        )
        compact_payload["content_brief_preview_included"] = len(
            compact_payload["content_brief_preview"]
        )
    wordpress_draft_payload_preview = compact_payload.get("wordpress_draft_payload_preview")
    if isinstance(wordpress_draft_payload_preview, list):
        compact_payload["wordpress_draft_payload_preview_total"] = len(
            wordpress_draft_payload_preview
        )
        compact_payload["wordpress_draft_payload_preview"] = (
            _compact_wordpress_draft_payload_preview_for_context(
                wordpress_draft_payload_preview
            )
        )
        compact_payload["wordpress_draft_payload_preview_included"] = len(
            compact_payload["wordpress_draft_payload_preview"]
        )
    payload_preview_kept = False
    payload_preview = compact_payload.get("payload_preview")
    if (
        compact_payload.get("preview_contract") == "ga4_tracking_quality_review_v1"
        and isinstance(payload_preview, list)
    ):
        compact_payload["payload_preview_total"] = len(payload_preview)
        compact_payload["payload_preview"] = _compact_ga4_tracking_preview_for_context(
            payload_preview
        )
        compact_payload["payload_preview_included"] = len(
            compact_payload["payload_preview"]
        )
        payload_preview_kept = True
    if (
        compact_payload.get("preview_contract") == "local_visibility_review_preview_v1"
        and isinstance(payload_preview, list)
    ):
        compact_payload["payload_preview_total"] = len(payload_preview)
        compact_payload["payload_preview"] = _compact_localo_visibility_preview_for_context(
            payload_preview
        )
        compact_payload["payload_preview_included"] = len(
            compact_payload["payload_preview"]
        )
        payload_preview_kept = True
    if (
        compact_payload.get("preview_contract") == "merchant_feed_issue_review_preview_v1"
        and isinstance(payload_preview, list)
    ):
        compact_payload["payload_preview_total"] = len(payload_preview)
        compact_payload["payload_preview"] = _compact_merchant_issue_preview_for_context(
            payload_preview
        )
        compact_payload["payload_preview_included"] = len(
            compact_payload["payload_preview"]
        )
        payload_preview_kept = True
    if (
        compact_payload.get("preview_contract") == "custom_segment_payload_preview_v1"
        and isinstance(payload_preview, list)
    ):
        compact_payload["payload_preview_total"] = len(payload_preview)
        compact_payload["payload_preview"] = [
            _compact_custom_segment_payload_preview_item(item)
            for item in payload_preview
            if isinstance(item, dict)
        ]
        compact_payload["payload_preview_included"] = len(
            compact_payload["payload_preview"]
        )
        payload_preview_kept = True
    ngram_preview = compact_payload.get("ngram_preview")
    if (
        compact_payload.get("preview_contract") == "search_term_ngram_review_v1"
        and isinstance(ngram_preview, list)
    ):
        compact_payload["ngram_preview_total"] = len(ngram_preview)
        compact_payload["ngram_preview"] = _compact_ngram_preview_for_context(
            ngram_preview
        )
        compact_payload["ngram_preview_included"] = len(
            compact_payload["ngram_preview"]
        )
    for key in (
        "budget_payload_preview",
        "recommendations",
        "terms",
        "source_terms",
        "source_search_terms",
        "payload_preview",
        "keyword_match_context",
    ):
        if key == "payload_preview" and payload_preview_kept:
            continue
        rows = compact_payload.get(key)
        if isinstance(rows, list):
            compact_payload[f"{key}_total"] = len(rows)
            compact_payload[key] = []
            compact_payload[f"{key}_included"] = len(compact_payload[key])
    if compact.get("id") == SEARCH_TERM_NGRAM_ACTION_ID:
        evidence_ids = compact_payload.get("evidence_ids")
        if isinstance(evidence_ids, list):
            compact_payload["evidence_ids"] = evidence_ids[:1]
        compact_payload = {
            key: compact_payload.get(key)
            for key in (
                "action_type",
                "connector",
                "mode",
                "preview_contract",
                "operation_type",
                "ngram_preview",
                "ngram_preview_total",
                "ngram_preview_included",
                "evidence_ids",
                "missing_read_contracts",
                "required_validation",
                "blocked_claims",
                "api_mutation_ready",
                "apply_allowed",
                "destructive",
            )
            if key in compact_payload
        }
    compact["payload"] = compact_payload
    return compact


def _compact_action_review_gate_for_context(action: dict[str, Any]) -> None:
    review_gate = action.get("review_gate")
    if not isinstance(review_gate, dict):
        return

    apply_blockers = review_gate.get("apply_blockers")
    if not isinstance(apply_blockers, list):
        apply_blockers = []
    missing_validation = review_gate.get("missing_validation")
    if not isinstance(missing_validation, list):
        missing_validation = []
    blocked_claims = review_gate.get("blocked_claims")
    if not isinstance(blocked_claims, list):
        blocked_claims = []
    warnings = review_gate.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
    last_mutation_blockers = review_gate.get("last_mutation_blockers")
    if not isinstance(last_mutation_blockers, list):
        last_mutation_blockers = []

    action["review_gate"] = {
        "status": review_gate.get("status"),
        "risk": review_gate.get("risk"),
        "last_review_outcome": review_gate.get("last_review_outcome"),
        "last_reviewed_by": review_gate.get("last_reviewed_by"),
        "last_reviewed_at": review_gate.get("last_reviewed_at"),
        "last_review_summary": review_gate.get("last_review_summary"),
        "last_confirmation_by": review_gate.get("last_confirmation_by"),
        "last_confirmation_at": review_gate.get("last_confirmation_at"),
        "last_confirmation_summary": review_gate.get("last_confirmation_summary"),
        "last_impact_check_status": review_gate.get("last_impact_check_status"),
        "last_impact_checked_by": review_gate.get("last_impact_checked_by"),
        "last_impact_checked_at": review_gate.get("last_impact_checked_at"),
        "last_impact_check_summary": review_gate.get("last_impact_check_summary"),
        "last_mutation_audit_id": review_gate.get("last_mutation_audit_id"),
        "last_mutation_audit_status": review_gate.get("last_mutation_audit_status"),
        "last_mutation_audit_actor": review_gate.get("last_mutation_audit_actor"),
        "last_mutation_audit_at": review_gate.get("last_mutation_audit_at"),
        "last_mutation_audit_summary": review_gate.get("last_mutation_audit_summary"),
        "last_mutation_attempted": review_gate.get("last_mutation_attempted"),
        "last_mutation_adapter": review_gate.get("last_mutation_adapter"),
        "last_mutation_audit_event_id": review_gate.get("last_mutation_audit_event_id"),
        "apply_allowed": review_gate.get("apply_allowed"),
        "confirmation_required": review_gate.get("confirmation_required"),
        "apply_blockers_total": len(apply_blockers),
        "apply_blockers": apply_blockers[:3],
        "apply_blockers_included": min(len(apply_blockers), 3),
        "missing_validation_total": len(missing_validation),
        "missing_validation": missing_validation[:4],
        "missing_validation_included": min(len(missing_validation), 4),
        "blocked_claims_total": len(blocked_claims),
        "blocked_claims": blocked_claims[:4],
        "blocked_claims_included": min(len(blocked_claims), 4),
        "warnings_total": len(warnings),
        "warnings": warnings[:2],
        "warnings_included": min(len(warnings), 2),
        "last_mutation_blockers_total": len(last_mutation_blockers),
        "last_mutation_blockers": last_mutation_blockers[:3],
        "last_mutation_blockers_included": min(len(last_mutation_blockers), 3),
    }


def _compact_ngram_preview_for_context(preview_items: list[Any]) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "id",
        "ngram",
        "ngram_size",
        "source_search_term_count",
        "sample_search_terms",
        "clicks",
        "impressions",
        "cost_micros",
        "conversions",
        "conversion_value",
        "operation_type",
                "required_validation",
                "blocked_claims",
                "evidence_ids",
                "api_mutation_ready",
        "apply_allowed",
        "destructive",
    }
    for item in preview_items[:1]:
        if not isinstance(item, dict):
            continue
        compact_item = {key: item.get(key) for key in keep_keys if key in item}
        sample_search_terms = compact_item.get("sample_search_terms")
        if isinstance(sample_search_terms, list):
            compact_item["sample_search_terms"] = sample_search_terms[:1]
        evidence_ids = compact_item.get("evidence_ids")
        if isinstance(evidence_ids, list):
            compact_item["evidence_ids"] = evidence_ids[:1]
        required_validation = compact_item.get("required_validation")
        if isinstance(required_validation, list):
            compact_item["required_validation_total"] = len(required_validation)
            compact_item["required_validation"] = required_validation[:2]
        blocked_claims = compact_item.get("blocked_claims")
        if isinstance(blocked_claims, list):
            compact_item["blocked_claims"] = blocked_claims[:2]
        compact_items.append(compact_item)
    return compact_items


def _compact_ga4_tracking_preview_for_context(preview_items: list[Any]) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "id",
        "preview_contract",
        "operation_type",
        "landing_page",
        "source_medium",
        "campaign_name",
        "tracking_dimension_gaps",
        "metric_snapshot",
        "reason",
        "required_validation",
        "blocked_claims",
        "evidence_ids",
        "api_mutation_ready",
        "apply_allowed",
        "destructive",
    }
    for item in preview_items[:4]:
        if isinstance(item, dict):
            compact_items.append({key: item[key] for key in keep_keys if key in item})
    return compact_items


def _compact_localo_visibility_preview_for_context(
    preview_items: list[Any],
) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "id",
        "preview_contract",
        "operation_type",
        "metric_snapshot",
        "allowed_contracts",
        "missing_read_contracts",
        "reason",
        "required_validation",
        "blocked_claims",
        "evidence_ids",
        "api_mutation_ready",
        "apply_allowed",
        "destructive",
    }
    for item in preview_items[:1]:
        if not isinstance(item, dict):
            continue
        compact_item = {key: item[key] for key in keep_keys if key in item}
        metric_snapshot = compact_item.get("metric_snapshot")
        if isinstance(metric_snapshot, dict):
            compact_item["metric_snapshot"] = dict(list(metric_snapshot.items())[:12])
        required_validation = compact_item.get("required_validation")
        if isinstance(required_validation, list):
            compact_item["required_validation_total"] = len(required_validation)
            compact_item["required_validation"] = required_validation[:4]
        blocked_claims = compact_item.get("blocked_claims")
        if isinstance(blocked_claims, list):
            compact_item["blocked_claims"] = blocked_claims[:5]
        evidence_ids = compact_item.get("evidence_ids")
        if isinstance(evidence_ids, list):
            compact_item["evidence_ids"] = evidence_ids[:3]
        compact_items.append(compact_item)
    return compact_items


def _compact_merchant_issue_preview_for_context(
    preview_items: list[Any],
) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "id",
        "preview_contract",
        "operation_type",
        "cluster_id",
        "issue_type",
        "affected_attribute",
        "country",
        "reporting_context",
        "severity",
        "resolution",
        "metric_snapshot",
        "sample_products_available",
        "sample_unavailable_reason",
        "reason",
        "required_validation",
        "blocked_claims",
        "evidence_ids",
        "api_mutation_ready",
        "apply_allowed",
        "destructive",
    }
    for item in preview_items[:4]:
        if not isinstance(item, dict):
            continue
        compact_item = {key: item[key] for key in keep_keys if key in item}
        required_validation = compact_item.get("required_validation")
        if isinstance(required_validation, list):
            compact_item["required_validation_total"] = len(required_validation)
            compact_item["required_validation"] = required_validation[:4]
        blocked_claims = compact_item.get("blocked_claims")
        if isinstance(blocked_claims, list):
            compact_item["blocked_claims"] = blocked_claims[:5]
        evidence_ids = compact_item.get("evidence_ids")
        if isinstance(evidence_ids, list):
            compact_item["evidence_ids"] = evidence_ids[:3]
        compact_items.append(compact_item)
    return compact_items


def _compact_content_brief_preview_for_context(
    preview_items: list[Any],
) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "candidate_id",
        "source_type",
        "mode",
        "topic",
        "target_url",
        "source_url",
        "target_site_url",
        "target_site_host",
        "source_site_host",
        "target_site_adaptation_status",
        "target_site_migration_candidate_url",
        "target_site_migration_status",
        "target_site_migration_summary",
        "target_site_review_requirements",
        "target_site_inventory_content_type",
        "target_site_inventory_status",
        "target_site_inventory_source",
        "target_site_inventory_modified_gmt",
        "target_site_inventory_missing_fields",
        "target_site_inventory_summary",
        "inventory_gate_status",
        "canonical_gate_status",
        "duplicate_gate_status",
        "content_gate_summary",
        "competitor_domain",
        "wordpress_inventory_match",
        "gsc_demand",
        "metric_snapshot",
        "brief_goal",
        "content_angle",
        "audience",
        "key_objections",
        "h1_direction",
        "seo_title_direction",
        "meta_description_direction",
        "h2_direction",
        "faq_direction",
        "schema_direction",
        "cta_direction",
        "internal_link_direction",
        "legal_review_notes",
        "brand_voice_notes",
        "publication_readiness_status",
        "publication_blockers",
        "source_facts",
        "missing_evidence",
        "forbidden_claims",
        "required_validation",
        "blocked_claims",
        "source_connectors",
        "evidence_ids",
        "apply_allowed",
        "api_mutation_ready",
        "destructive",
    }
    for item in preview_items[:4]:
        if isinstance(item, dict):
            compact_item = {key: item[key] for key in keep_keys if key in item}
            for key, limit in (
                ("key_objections", 3),
                ("h2_direction", 4),
                ("faq_direction", 4),
                ("internal_link_direction", 3),
                ("legal_review_notes", 4),
                ("brand_voice_notes", 4),
                ("publication_blockers", 6),
                ("source_facts", 4),
                ("missing_evidence", 3),
                ("forbidden_claims", 5),
                ("target_site_review_requirements", 4),
                ("target_site_inventory_missing_fields", 6),
                ("required_validation", 4),
                ("blocked_claims", 5),
                ("source_connectors", 4),
                ("evidence_ids", 3),
            ):
                value = compact_item.get(key)
                if isinstance(value, list):
                    compact_item[key] = value[:limit]
                    compact_item[f"{key}_total"] = len(value)
            compact_items.append(compact_item)
    return compact_items


def _compact_wordpress_draft_payload_preview_for_context(
    preview_items: list[Any],
) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "preview_contract",
        "source_preview_contract",
        "candidate_id",
        "source_type",
        "mode",
        "operation_type",
        "post_status",
        "topic",
        "target_url",
        "source_url",
        "target_site_url",
        "target_site_host",
        "source_site_host",
        "target_site_adaptation_status",
        "target_site_migration_candidate_url",
        "target_site_migration_status",
        "target_site_migration_summary",
        "target_site_review_requirements",
        "target_site_inventory_content_type",
        "target_site_inventory_status",
        "target_site_inventory_source",
        "target_site_inventory_modified_gmt",
        "target_site_inventory_missing_fields",
        "target_site_inventory_summary",
        "inventory_gate_status",
        "canonical_gate_status",
        "duplicate_gate_status",
        "content_gate_summary",
        "draft_generation_status",
        "draft_blockers",
        "required_validation",
        "blocked_claims",
        "source_connectors",
        "evidence_ids",
        "mutation_allowed",
        "apply_allowed",
        "api_mutation_ready",
        "destructive",
    }
    for item in preview_items[:2]:
        if not isinstance(item, dict):
            continue
        compact_item = {key: item[key] for key in keep_keys if key in item}
        draft_payload = item.get("draft_payload")
        if isinstance(draft_payload, dict):
            compact_item["draft_payload"] = {
                key: draft_payload[key]
                for key in (
                    "post_status",
                    "post_title",
                    "post_excerpt_direction",
                )
                if key in draft_payload
            }
            content_blocks = draft_payload.get("content_blocks")
            if isinstance(content_blocks, list):
                compact_item["draft_payload"]["content_blocks_total"] = len(
                    content_blocks
                )
                compact_item["draft_payload"]["content_blocks"] = [
                    block
                    for block in content_blocks[:4]
                    if isinstance(block, dict)
                ]
                compact_item["draft_payload"]["content_blocks_included"] = len(
                    compact_item["draft_payload"]["content_blocks"]
                )
        compact_items.append(compact_item)
    return compact_items


def _compact_campaign_candidates_for_context(
    campaign_candidates: list[Any],
) -> list[dict[str, Any]]:
    compact_candidates: list[dict[str, Any]] = []
    for candidate in campaign_candidates:
        if not isinstance(candidate, dict):
            continue
        evidence_ids = candidate.get("evidence_ids")
        if not isinstance(evidence_ids, list):
            evidence_ids = []
        human_review_gates = candidate.get("human_review_gates")
        if not isinstance(human_review_gates, list):
            human_review_gates = []
        missing_metrics = candidate.get("missing_metrics")
        if not isinstance(missing_metrics, list):
            missing_metrics = []
        compact_candidates.append(
            {
                "campaign_id": candidate.get("campaign_id"),
                "campaign_name": candidate.get("campaign_name"),
                "campaign_status": candidate.get("campaign_status"),
                "advertising_channel_type": candidate.get("advertising_channel_type"),
                "review_priority": candidate.get("review_priority"),
                "review_score": candidate.get("review_score"),
                "review_reason": candidate.get("review_reason"),
                "human_review_gates": human_review_gates,
                "target_context": candidate.get("target_context"),
                "clicks": candidate.get("clicks"),
                "impressions": candidate.get("impressions"),
                "cost_micros": candidate.get("cost_micros"),
                "conversions": candidate.get("conversions"),
                "conversion_value": candidate.get("conversion_value"),
                "derived_kpis": candidate.get("derived_kpis"),
                "missing_metrics": missing_metrics,
                "evidence_ids": evidence_ids[:4],
                "evidence_ids_total": len(evidence_ids),
                "apply_allowed": candidate.get("apply_allowed"),
            }
        )
        if len(compact_candidates) >= ACTION_CONTEXT_CAMPAIGN_CANDIDATE_LIMIT:
            break
    return compact_candidates


def _without_metric_facts(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_metric_facts(item)
            for key, item in value.items()
            if key != "metric_facts" and not key.endswith("_metric_facts")
        }
    if isinstance(value, list):
        return [_without_metric_facts(item) for item in value]
    return value


def _list_at(data: dict[str, Any], *path: str) -> list[Any]:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    return current if isinstance(current, list) else []


def _limit_contract_rows(
    data: dict[str, Any],
    path: tuple[str, str],
    limit: int,
) -> None:
    contract = data.get(path[0])
    if isinstance(contract, dict) and isinstance(contract.get(path[1]), list):
        contract[path[1]] = contract[path[1]][:limit]


def _limit_recommendation_rows_for_context(data: dict[str, Any]) -> None:
    contract = data.get("recommendations_read_contract")
    if not isinstance(contract, dict) or not isinstance(
        contract.get("recommendation_rows"),
        list,
    ):
        return
    rows = contract["recommendation_rows"]
    selected_indexes = {
        index
        for index, row in enumerate(rows)
        if isinstance(row, dict) and row.get("impact_available")
    }
    for index, _row in enumerate(rows):
        if len(selected_indexes) >= ADS_CONTEXT_DECISION_ROW_LIMIT:
            break
        selected_indexes.add(index)
    contract["recommendation_rows"] = [
        row for index, row in enumerate(rows) if index in selected_indexes
    ]


def _limit_candidate_rows(
    data: dict[str, Any],
    candidates_path: tuple[str, str],
    rows_key: str,
    limit: int,
) -> None:
    candidates = _list_at(data, *candidates_path)
    for candidate in candidates:
        if isinstance(candidate, dict) and isinstance(candidate.get(rows_key), list):
            candidate[rows_key] = candidate[rows_key][:limit]


def _drop_candidate_nested_payload_preview(
    data: dict[str, Any],
    candidates_path: tuple[str, str],
) -> None:
    for candidate in _list_at(data, *candidates_path):
        if isinstance(candidate, dict):
            candidate.pop("payload_preview", None)


def _compact_custom_segment_payload_preview_for_context(data: dict[str, Any]) -> None:
    contract = data.get("custom_segments_read_contract")
    if not isinstance(contract, dict):
        return
    payload_preview = contract.get("payload_preview")
    if not isinstance(payload_preview, list):
        return
    compact_items: list[dict[str, Any]] = []
    for item in payload_preview:
        if not isinstance(item, dict):
            continue
        compact_items.append(_compact_custom_segment_payload_preview_item(item))
    contract["payload_preview"] = compact_items


def _compact_custom_segment_payload_preview_item(item: dict[str, Any]) -> dict[str, Any]:
    compact_item = {
        key: item.get(key)
        for key in (
            "id",
            "custom_segment_name",
            "member_type",
            "source_terms",
            "campaign_id",
            "campaign_name",
            "evidence_ids",
            "required_validation",
            "blocked_claims",
            "api_mutation_ready",
            "apply_allowed",
            "destructive",
        )
        if key in item
    }
    compact_item["targeting_preview"] = (
        _compact_custom_segment_targeting_preview_for_context(
            item.get("targeting_preview")
        )
    )
    safety_review = item.get("safety_review")
    if isinstance(safety_review, dict):
        compact_item["safety_review"] = _compact_custom_segment_safety_review_item(
            safety_review
        )
    return compact_item


def _compact_custom_segment_safety_review_item(item: dict[str, Any]) -> dict[str, Any]:
    compact_item = {
        key: item.get(key)
        for key in (
            "id",
            "safety_contract",
            "status",
            "reason",
            "missing_requirements",
            "audit_required",
            "api_mutation_ready",
            "apply_allowed",
            "destructive",
        )
        if key in item
    }
    required_validation = item.get("required_validation")
    if isinstance(required_validation, list):
        compact_item["required_validation_total"] = len(required_validation)
    blocked_claims = item.get("blocked_claims")
    if isinstance(blocked_claims, list):
        compact_item["blocked_claims"] = blocked_claims[:4]
    return compact_item


def _compact_custom_segment_targeting_preview_for_context(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    compact_targets: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        compact_targets.append(
            {
                key: item.get(key)
                for key in (
                    "id",
                    "custom_segment_preview_id",
                    "target_scope",
                    "campaign_id",
                    "campaign_name",
                    "operation_type",
                    "required_validation",
                    "blocked_claims",
                    "api_mutation_ready",
                    "apply_allowed",
                    "destructive",
                )
                if key in item
            }
        )
    return compact_targets


def _drop_candidate_keys(
    data: dict[str, Any],
    candidates_path: tuple[str, str],
    keys: tuple[str, ...],
) -> None:
    for candidate in _list_at(data, *candidates_path):
        if not isinstance(candidate, dict):
            continue
        for key in keys:
            candidate.pop(key, None)


def _limit_decision_rows(data: dict[str, Any]) -> None:
    for decision in _list_at(data, "decision_queue"):
        if not isinstance(decision, dict):
            continue
        for rows_key in (
            "campaign_rows",
            "campaign_triage_rows",
            "derived_kpi_rows",
            "budget_rows",
            "budget_apply_preview",
            "recommendation_rows",
            "recommendation_apply_preview",
            "impression_share_rows",
            "change_history_rows",
            "search_term_rows",
            "search_term_ngram_rows",
            "search_term_safety_rows",
            "keyword_match_context_rows",
            "keyword_planner_idea_rows",
            "custom_segment_candidates",
            "custom_segment_audience_forecast_rows",
            "custom_segment_payload_preview",
            "negative_keyword_candidates",
            "negative_keyword_payload_preview",
        ):
            rows = decision.get(rows_key)
            if isinstance(rows, list):
                decision[rows_key] = rows[:ADS_CONTEXT_DECISION_ROW_LIMIT]
        for candidate in decision.get("custom_segment_candidates", []):
            if isinstance(candidate, dict) and isinstance(
                candidate.get("search_term_rows"),
                list,
            ):
                candidate["search_term_rows"] = candidate["search_term_rows"][
                    :ADS_CONTEXT_DECISION_ROW_LIMIT
                ]
            if isinstance(candidate, dict):
                candidate.pop("payload_preview", None)
        for candidate in decision.get("negative_keyword_candidates", []):
            if isinstance(candidate, dict) and isinstance(
                candidate.get("keyword_context_rows"),
                list,
            ):
                candidate["keyword_context_rows"] = candidate["keyword_context_rows"][
                    :ADS_CONTEXT_DECISION_ROW_LIMIT
                ]
            if isinstance(candidate, dict):
                candidate.pop("payload_preview", None)


def _omit_decision_row_payloads(data: dict[str, Any]) -> None:
    for decision in _list_at(data, "decision_queue"):
        if not isinstance(decision, dict):
            continue
        for rows_key in (
            "campaign_rows",
            "campaign_triage_rows",
            "derived_kpi_rows",
            "budget_rows",
            "budget_apply_preview",
            "recommendation_rows",
            "recommendation_apply_preview",
            "impression_share_rows",
            "change_history_rows",
            "search_term_rows",
            "search_term_ngram_rows",
            "search_term_safety_rows",
            "keyword_match_context_rows",
            "custom_segment_candidates",
            "custom_segment_audience_forecast_rows",
            "custom_segment_payload_preview",
            "negative_keyword_candidates",
            "negative_keyword_payload_preview",
        ):
            rows = decision.get(rows_key)
            if isinstance(rows, list):
                decision[f"{rows_key}_total"] = len(rows)
                decision[rows_key] = []


def _evidence_ids_from_context(
    diagnostics: dict[str, Any],
    actions: list[ActionObject],
    scoped_connectors: set[str],
) -> set[str]:
    evidence_ids: set[str] = set()
    for value in diagnostics.values():
        evidence_ids.update(_collect_values_by_key(value, "evidence_ids"))
    for action in actions:
        if action.connector in scoped_connectors:
            evidence_ids.update(action.evidence_ids)
    return evidence_ids


def _collect_values_by_key(value: Any, key: str) -> set[str]:
    values: set[str] = set()
    if isinstance(value, dict):
        for item_key, item_value in value.items():
            if item_key == key and isinstance(item_value, list):
                values.update(str(item) for item in item_value if item)
            else:
                values.update(_collect_values_by_key(item_value, key))
    elif isinstance(value, list):
        for item in value:
            values.update(_collect_values_by_key(item, key))
    return values


def _opportunities_for_skill_scope(
    skill: str,
    opportunities: list[Opportunity],
    scoped_connectors: set[str],
    max_opportunities: int,
) -> list[Opportunity]:
    scoped = [
        opportunity
        for opportunity in opportunities
        if _connectors_intersect(opportunity.source_connectors, scoped_connectors)
    ]
    allowed_action_ids = SKILL_ACTION_ID_SCOPES.get(skill)
    if allowed_action_ids is None:
        return scoped[:max_opportunities]
    return [
        opportunity
        for opportunity in scoped
        if opportunity.action_ids
        and set(opportunity.action_ids).issubset(allowed_action_ids)
    ][:max_opportunities]


def _actions_for_scope(
    actions: list[ActionObject],
    scoped_connectors: set[str],
    evidence_ids: set[str],
) -> list[ActionObject]:
    del evidence_ids
    return [action for action in actions if action.connector in scoped_connectors]


def _knowledge_cards_for_skill(skill: str) -> list[KnowledgeCard]:
    explicit_ids = SKILL_KNOWLEDGE_CARD_IDS.get(skill, [])
    keywords = SKILL_KEYWORD_SCOPES.get(skill, set())
    cards = compile_playbook_cards()
    explicit_cards = [card for card in cards if card.id in explicit_ids]
    scoped_cards = [
        card
        for card in cards
        if card.id not in explicit_ids
        and _text_matches_scope(
            [card.id, card.card_type, card.title, card.summary, card.source_id],
            keywords,
        )
    ]
    return [*explicit_cards, *scoped_cards][:8]


def _expert_rules_for_skill(skill: str) -> list[ExpertRuleSummary]:
    explicit_ids = SKILL_EXPERT_RULE_IDS.get(skill, [])
    keywords = SKILL_KEYWORD_SCOPES.get(skill, set())
    rules = list_expert_rule_summaries(limit=50)
    explicit_rules = [rule for rule in rules if rule.id in explicit_ids]
    scoped_rules = [
        rule
        for rule in rules
        if rule.id not in explicit_ids
        and _text_matches_scope(
            [
                rule.id,
                rule.name,
                rule.domain,
                rule.source_anchor,
                rule.output_contract,
            ],
            keywords,
        )
    ]
    return [*explicit_rules, *scoped_rules][:8]


def _text_matches_scope(values: list[str], keywords: set[str]) -> bool:
    if not keywords:
        return True
    haystack = " ".join(values).lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def _connectors_intersect(values: list[str], scoped_connectors: set[str]) -> bool:
    return bool(set(values).intersection(scoped_connectors))


@app.get("/")
def root() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "wilq-api",
        "health": "/api/health",
        "system_status": "/api/system/status",
        "connectors": "/api/connectors",
        "command_center": "/api/dashboard/command-center",
        "docs": "/docs",
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "wilq-api"}


@app.get("/api/system/status")
def system_status() -> dict[str, Any]:
    connectors = list_connector_statuses()
    return redact_mapping(
        {
            "generated_at": utc_now().isoformat(),
            "connector_summary": connector_summary(connectors).model_dump(),
            "credential_runtime": credential_runtime_status(detailed=False),
            "codex_runtime": codex_runtime_status(),
            "job_scheduler": scheduler_status(),
            "local_state": local_state_store().status(),
            "metric_store": metric_store().status(),
            "opportunity_types": list(OPPORTUNITY_TYPES),
        }
    )


@app.get("/api/connectors", response_model=list[ConnectorStatus])
def connectors() -> list[ConnectorStatus]:
    return list_connector_statuses()


@app.get("/api/connectors/refresh-runs", response_model=list[ConnectorRefreshRun])
def connector_refresh_runs() -> list[ConnectorRefreshRun]:
    return list_connector_refresh_runs()


@app.get("/api/connectors/refresh-runs/{run_id}", response_model=ConnectorRefreshRun)
def connector_refresh_run_detail(run_id: str) -> ConnectorRefreshRun:
    run = get_connector_refresh_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Unknown connector refresh run: {run_id}")
    return run


@app.get("/api/connectors/{connector}/status", response_model=ConnectorStatus)
def connector_status_endpoint(connector: str) -> ConnectorStatus:
    status = get_connector_status(connector)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Unknown connector: {connector}")
    return status


@app.get("/api/connectors/{connector}/refresh-runs", response_model=list[ConnectorRefreshRun])
def connector_refresh_runs_for_connector(connector: str) -> list[ConnectorRefreshRun]:
    if get_connector_status(connector) is None:
        raise HTTPException(status_code=404, detail=f"Unknown connector: {connector}")
    return list_connector_refresh_runs(connector_id=connector)


@app.post("/api/connectors/{connector}/refresh", response_model=ConnectorRefreshRun)
def connector_refresh(
    connector: str,
    request: ConnectorRefreshRequest | None = None,
) -> ConnectorRefreshRun:
    run = run_connector_refresh(connector, request)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Unknown connector: {connector}")
    clear_api_view_model_caches()
    return run


@app.get("/api/dashboard/command-center", response_model=CommandCenterResponse)
def command_center() -> CommandCenterResponse:
    return build_daily_command_center()


@app.get("/api/marketing/brief", response_model=MarketingBrief)
def marketing_brief() -> MarketingBrief:
    return build_daily_marketing_brief()


@app.get("/api/marketing/tactical-queue", response_model=TacticalQueueResponse)
def marketing_tactical_queue() -> TacticalQueueResponse:
    return build_tactical_queue()


@app.get("/api/ads/diagnostics", response_model=AdsDiagnosticsResponse)
def ads_diagnostics(view: str | None = None) -> AdsDiagnosticsResponse:
    return build_ads_diagnostics(view="summary" if view == "summary" else "full")


@app.get("/api/merchant/diagnostics", response_model=MerchantDiagnosticsResponse)
def merchant_diagnostics() -> MerchantDiagnosticsResponse:
    return build_merchant_diagnostics()


@app.get("/api/content/diagnostics", response_model=ContentDiagnosticsResponse)
def content_diagnostics() -> ContentDiagnosticsResponse:
    return build_content_diagnostics()


@app.get("/api/ga4/diagnostics", response_model=Ga4DiagnosticsResponse)
def ga4_diagnostics() -> Ga4DiagnosticsResponse:
    return build_ga4_diagnostics()


@app.get("/api/localo/diagnostics", response_model=LocaloDiagnosticsResponse)
def localo_diagnostics() -> LocaloDiagnosticsResponse:
    return build_localo_diagnostics()


@app.get("/api/ahrefs/diagnostics", response_model=AhrefsDiagnosticsResponse)
def ahrefs_diagnostics() -> AhrefsDiagnosticsResponse:
    return build_ahrefs_diagnostics()


@app.get("/api/demand-gen/diagnostics", response_model=DemandGenReadinessContract)
def demand_gen_diagnostics() -> DemandGenReadinessContract:
    return _build_demand_gen_readiness_contract()


@app.get("/api/opportunities", response_model=list[Opportunity])
def opportunities() -> list[Opportunity]:
    return list_opportunities()


@app.get("/api/opportunities/{opportunity_id}", response_model=Opportunity)
def opportunity(opportunity_id: str) -> Opportunity:
    item = get_opportunity(opportunity_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Unknown opportunity: {opportunity_id}")
    return item


@app.post("/api/opportunities/recompute", response_model=list[Opportunity])
def recompute_opportunities() -> list[Opportunity]:
    return list_opportunities()


@app.get("/api/actions")
def actions() -> list[dict[str, Any]]:
    return [action.model_dump(mode="json") for action in list_actions()]


@app.get("/api/evidence", response_model=list[Evidence])
def evidence_items() -> list[Evidence]:
    return list_evidence()


@app.get("/api/evidence/{evidence_id}", response_model=Evidence)
def evidence_detail(evidence_id: str) -> Evidence:
    evidence = get_evidence(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail=f"Unknown evidence: {evidence_id}")
    return evidence


@app.get("/api/metrics", response_model=list[MetricFact])
def metric_facts(connector_id: str | None = None, limit: int = 100) -> list[MetricFact]:
    return metric_store().list_metric_facts(connector_id=connector_id, limit=limit)


@app.get("/api/metrics/status")
def metric_store_status() -> dict[str, Any]:
    return metric_store().status()


@app.get("/api/jobs", response_model=list[ScheduledJob])
def jobs() -> list[ScheduledJob]:
    return list_jobs()


@app.get("/api/jobs/status")
def jobs_status() -> dict[str, Any]:
    return scheduler_status()


@app.get("/api/jobs/{job_id}", response_model=ScheduledJob)
def job_detail(job_id: str) -> ScheduledJob:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")
    return job


@app.post("/api/jobs/{job_id}/run", response_model=JobRun)
def run_job_endpoint(job_id: str, request: JobRunRequest | None = None) -> JobRun:
    run = run_job(job_id, request)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")
    return run


@app.get("/api/job-runs", response_model=list[JobRun])
def job_runs() -> list[JobRun]:
    return list_job_runs()


@app.get("/api/job-runs/{run_id}", response_model=JobRun)
def job_run_detail(run_id: str) -> JobRun:
    run = get_job_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Unknown job run: {run_id}")
    return run


@app.get("/api/actions/{action_id}")
def action_detail(action_id: str) -> dict[str, Any]:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    return action.model_dump(mode="json")


@app.post("/api/actions/{action_id}/validate")
def validate_action_endpoint(action_id: str) -> dict[str, Any]:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    result = validate_action(action).model_dump(mode="json")
    clear_api_view_model_caches()
    return result


@app.post("/api/actions/{action_id}/review")
def review_action_endpoint(
    action_id: str,
    request: ActionReviewRequest,
) -> dict[str, Any]:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    result = record_action_review(action, request)
    local_state_store().save_audit_event(result.audit_event)
    if action.id == ADS_STRATEGY_REVIEW_ACTION_ID:
        local_state_store().save_ads_strategy_review(
            AdsStrategyReviewRecord(
                id=f"ads_strategy_review_{uuid4().hex[:12]}",
                action_id=action.id,
                outcome=request.outcome,
                reviewed_by=request.reviewed_by,
                notes=request.notes,
                checked_items=request.checked_items,
                blockers=request.blockers,
                audit_event_id=result.audit_event.id,
                evidence_ids=action.evidence_ids,
            )
        )
    clear_api_view_model_caches()
    return result.model_dump(mode="json")


@app.post("/api/actions/{action_id}/preview")
def preview_action_endpoint(
    action_id: str,
    request: ActionPreviewRequest | None = None,
) -> dict[str, Any]:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    result = preview_action(action, request)
    local_state_store().save_audit_event(result.audit_event)
    clear_api_view_model_caches()
    return result.model_dump(mode="json")


@app.post("/api/actions/{action_id}/confirm")
def confirm_action_endpoint(
    action_id: str,
    request: ActionConfirmRequest,
) -> dict[str, Any]:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    result = confirm_action(action, request)
    local_state_store().save_audit_event(result.audit_event)
    if action.id == ADS_TARGET_CONFIRMATION_ACTION_ID and result.confirmed:
        local_state_store().save_ads_target_guardrail_confirmation(
            AdsTargetGuardrailConfirmation(
                id=f"ads_target_guardrail_{uuid4().hex[:12]}",
                action_id=action.id,
                target_roas=request.target_roas,
                target_cpa_micros=request.target_cpa_micros,
                confirmed_by=request.confirmed_by,
                notes=request.notes,
                audit_event_id=result.audit_event.id,
                evidence_ids=action.evidence_ids,
            )
        )
    clear_api_view_model_caches()
    return result.model_dump(mode="json")


@app.post("/api/actions/{action_id}/impact-check")
def impact_check_action_endpoint(
    action_id: str,
    request: ActionImpactCheckRequest,
) -> dict[str, Any]:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    result = impact_check_action(action, request)
    local_state_store().save_audit_event(result.audit_event)
    clear_api_view_model_caches()
    return result.model_dump(mode="json")


@app.post("/api/actions/{action_id}/apply")
def apply_action_endpoint(
    action_id: str,
    request: ActionApplyRequest | None = None,
) -> dict[str, Any]:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    result = apply_action(action, request)
    local_state_store().save_audit_event(result.audit_event)
    local_state_store().save_action_mutation_audit(result.mutation_audit)
    clear_api_view_model_caches()
    if not result.applied:
        raise HTTPException(status_code=409, detail=result.model_dump(mode="json"))
    return result.model_dump(mode="json")


@app.get("/api/audit/events", response_model=list[AuditEvent])
def audit_events(action_id: str | None = None) -> list[AuditEvent]:
    return local_state_store().list_audit_events(action_id=action_id)


@app.get("/api/action-mutation-audits", response_model=list[ActionMutationAuditRecord])
def action_mutation_audits(
    action_id: str | None = None,
) -> list[ActionMutationAuditRecord]:
    return local_state_store().list_action_mutation_audits(action_id=action_id)


@app.get(
    "/api/actions/{action_id}/mutation-audits",
    response_model=list[ActionMutationAuditRecord],
)
def action_mutation_audits_for_action(action_id: str) -> list[ActionMutationAuditRecord]:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    return local_state_store().list_action_mutation_audits(action_id=action_id)


@app.get("/api/knowledge/cards", response_model=list[KnowledgeCard])
def knowledge_cards() -> list[KnowledgeCard]:
    return compile_playbook_cards()


@app.get("/api/knowledge/search")
def knowledge_search(q: str = "") -> list[dict[str, Any]]:
    query = q.lower()
    cards = compile_playbook_cards()
    if query:
        cards = [
            card for card in cards if query in card.title.lower() or query in card.summary.lower()
        ]
    return [card.model_dump(mode="json") for card in cards]


@app.get("/api/knowledge/playbooks", response_model=list[MarketingPlaybook])
def knowledge_playbooks() -> list[MarketingPlaybook]:
    return list(list_playbooks())


@app.get("/api/knowledge/playbooks/{playbook_id}", response_model=MarketingPlaybook)
def knowledge_playbook_detail(playbook_id: str) -> MarketingPlaybook:
    playbook = get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(status_code=404, detail=f"Unknown playbook: {playbook_id}")
    return playbook


@app.get("/api/knowledge/operating-map", response_model=KnowledgeOperatingMapResponse)
def knowledge_operating_map() -> KnowledgeOperatingMapResponse:
    return build_knowledge_operating_map()


@app.post("/api/knowledge/condense", response_model=KnowledgeCompilerResult)
def knowledge_condense() -> KnowledgeCompilerResult:
    return condense_playbooks()


@app.get("/api/expert/rules", response_model=list[ExpertRule])
def expert_rules(domain: str | None = None) -> list[ExpertRule]:
    rules = list(list_expert_rules())
    if domain is not None:
        rules = [rule for rule in rules if rule.domain == domain]
    return rules


@app.get("/api/expert/rules/{rule_id}", response_model=ExpertRule)
def expert_rule_detail(rule_id: str) -> ExpertRule:
    rule = get_expert_rule(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Unknown expert rule: {rule_id}")
    return rule


@app.get("/api/expert/rule-summaries", response_model=list[ExpertRuleSummary])
def expert_rule_summaries() -> list[ExpertRuleSummary]:
    return list_expert_rule_summaries()


@app.get("/api/expert/capabilities", response_model=list[ExpertCapability])
def expert_capabilities() -> list[ExpertCapability]:
    return list_expert_capabilities()


@app.get("/api/codex/context")
def codex_context() -> dict[str, Any]:
    return context_pack()


@app.post("/api/codex/context-pack")
def codex_context_pack(request: ContextPackRequest) -> dict[str, Any]:
    return context_pack(request)


@app.post("/api/codex/runs", response_model=CodexRun)
def create_codex_run(run: CodexRun) -> CodexRun:
    return local_state_store().save_codex_run(run)


@app.get("/api/codex/runs", response_model=list[CodexRun])
def codex_runs() -> list[CodexRun]:
    return local_state_store().list_codex_runs()


@app.get("/api/workflows")
def workflows() -> list[dict[str, Any]]:
    return [workflow.model_dump(mode="json") for workflow in list_workflows()]


@app.post("/api/workflows/{workflow_id}/runs", response_model=WorkflowRun)
def create_workflow_run(workflow_id: str, request: WorkflowRunCreateRequest) -> WorkflowRun:
    if workflow_id not in {workflow.id for workflow in list_workflows()}:
        raise HTTPException(status_code=404, detail=f"Unknown workflow: {workflow_id}")
    run = WorkflowRun(
        id=request.id or f"run_{workflow_id}_{uuid4().hex[:10]}",
        workflow_id=workflow_id,
        status="queued",
        input=request.input,
    )
    return local_state_store().save_workflow_run(run)


@app.get("/api/workflow-runs", response_model=list[WorkflowRun])
def workflow_runs() -> list[WorkflowRun]:
    return local_state_store().list_workflow_runs()


@app.get("/api/workflow-runs/{run_id}", response_model=WorkflowRun)
def workflow_run_detail(run_id: str) -> WorkflowRun:
    run = local_state_store().get_workflow_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Unknown workflow run: {run_id}")
    return run
