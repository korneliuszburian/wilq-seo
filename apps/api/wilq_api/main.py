from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import monotonic
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from wilq.actions.service import apply_action, get_action, list_actions, validate_action
from wilq.briefing.ads_diagnostics import build_ads_diagnostics
from wilq.briefing.ahrefs_diagnostics import build_ahrefs_diagnostics
from wilq.briefing.content_diagnostics import build_content_diagnostics
from wilq.briefing.daily_runtime import build_daily_runtime, clear_daily_runtime_cache
from wilq.briefing.ga4_diagnostics import build_ga4_diagnostics
from wilq.briefing.localo_diagnostics import build_localo_diagnostics
from wilq.briefing.marketing_brief import core_brief_actions
from wilq.briefing.merchant_diagnostics import build_merchant_diagnostics
from wilq.briefing.tactical_queue import build_tactical_queue
from wilq.codex.runtime_status import codex_runtime_status
from wilq.connectors.refresh import (
    get_connector_refresh_run,
    list_connector_refresh_runs,
    run_connector_refresh,
)
from wilq.connectors.registry import get_connector_status, list_connector_statuses
from wilq.credentials.runtime import credential_runtime_status
from wilq.evidence.registry import get_evidence, list_evidence, list_evidence_by_ids
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
    ActionObject,
    AdsDiagnosticsResponse,
    AhrefsDiagnosticsResponse,
    AuditEvent,
    CodexRun,
    CommandCenterResponse,
    ConnectorRefreshRequest,
    ConnectorRefreshRun,
    ConnectorStatus,
    ConnectorSummary,
    ContentDiagnosticsResponse,
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
ADS_CONTEXT_ROW_LIMIT = 8
ADS_CONTEXT_DECISION_ROW_LIMIT = 4
ADS_LITE_DECISION_LIMIT = 5
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
            opportunity.model_dump(mode="json") for opportunity in scoped_opportunities
        ],
        "active_action_objects": [
            _compact_daily_action_for_context(action) for action in active_actions
        ],
        "connector_refresh_runs": [
            run.model_dump(mode="json")
            for run in daily_runtime.refresh_runs[:30]
            if run.connector_id in source_connectors
        ][:10],
        "evidence_summaries": [
            evidence.model_dump(mode="json")
            for evidence in list_evidence_by_ids(sorted(evidence_ids))
        ][:80],
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
            "marketing_brief_metric_facts_compacted": True,
            "full_action_endpoint_template": "/api/actions/{action_id}",
            "full_marketing_brief_endpoint": "/api/marketing/brief",
            "full_command_center_endpoint": "/api/dashboard/command-center",
        },
        "strict_instruction": "Codex must not invent metrics; fetch WILQ API evidence first.",
    }
    return redact_mapping(pack)


def _compact_daily_action_for_context(action: ActionObject) -> dict[str, Any]:
    dumped = action.model_dump(mode="json")
    payload = dumped.get("payload")
    payload_keys = sorted(payload) if isinstance(payload, dict) else []
    return {
        "id": dumped["id"],
        "title": dumped["title"],
        "domain": dumped["domain"],
        "connector": dumped["connector"],
        "mode": dumped["mode"],
        "risk": dumped["risk"],
        "status": dumped["status"],
        "validation_status": dumped["validation_status"],
        "evidence_ids": dumped["evidence_ids"],
        "human_diagnosis": dumped["human_diagnosis"],
        "recommended_reason": dumped["recommended_reason"],
        "metric_count": len(dumped.get("metrics", [])),
        "payload_keys": payload_keys,
        "api_endpoint_template": "/api/actions/{action_id}",
    }


def _compact_command_center_for_daily_context(command: CommandCenterResponse) -> dict[str, Any]:
    dumped = command.model_dump(mode="json")
    return {
        "generated_at": dumped["generated_at"],
        "strict_instruction": dumped["strict_instruction"],
        "primary_next_step": dumped["primary_next_step"],
        "blocker_count": dumped["blocker_count"],
        "tactical_item_count": dumped["tactical_item_count"],
        "daily_decisions": dumped["daily_decisions"],
        "operator_brief": dumped["operator_brief"],
        "demo_script": dumped["demo_script"],
        "action_plan": dumped["action_plan"],
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
    "wilq-ahrefs-gap-finder": set(),
    "wilq-campaign-builder": {
        "act_prepare_ads_campaign_review_queue",
        "act_prepare_google_ads_recommendation_review_queue",
    },
    "wilq-demand-gen-operator": set(),
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
    scoped_opportunities = [
        opportunity
        for opportunity in opportunities
        if _connectors_intersect(opportunity.source_connectors, scoped_connectors)
    ][:max_opportunities]
    evidence_ids.update(
        evidence_id
        for opportunity in scoped_opportunities
        for evidence_id in opportunity.evidence_ids
    )
    scoped_evidence = list_evidence_by_ids(sorted(evidence_ids))
    evidence_summary_limit = 40 if skill == "wilq-custom-segments" else 80

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
        ][:3],
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
    if skill in {"wilq-content-strategist", "wilq-gsc-content-doctor"}:
        return {
            "content_diagnostics": _compact_content_diagnostics_for_context(
                build_content_diagnostics().model_dump(mode="json")
            )
        }
    if skill == "wilq-ahrefs-gap-finder":
        return {"ahrefs_diagnostics": build_ahrefs_diagnostics().model_dump(mode="json")}
    if skill == "wilq-ads-doctor":
        return {
            "ads_diagnostics": _compact_ads_diagnostics_for_context(
                build_ads_diagnostics().model_dump(mode="json")
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
            "ads_diagnostics": _compact_ads_diagnostics_for_context(
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


def _demand_gen_diagnostics_for_context() -> dict[str, Any]:
    with ThreadPoolExecutor(max_workers=2) as executor:
        ads_future = executor.submit(build_ads_diagnostics)
        ga4_future = executor.submit(build_ga4_diagnostics)
        ads_diagnostics = ads_future.result().model_dump(mode="json")
        ga4_diagnostics = ga4_future.result().model_dump(mode="json")
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
        ).model_dump(mode="json"),
    }


def _demand_gen_readiness_contract(
    ads_diagnostics: dict[str, Any],
    ga4_diagnostics: dict[str, Any],
) -> DemandGenReadinessContract:
    evidence_ids = sorted(
        {
            *_collect_values_by_key(ads_diagnostics, "evidence_ids"),
            *_collect_values_by_key(ga4_diagnostics, "evidence_ids"),
        }
    )[:12]
    return DemandGenReadinessContract(
        status="blocked",
        summary=(
            "WILQ ma Ads i GA4 evidence do oceny ruchu, ale nie ma jeszcze "
            "Demand Gen-specific read contractów dla assetów, kreacji, typów "
            "kampanii ani migracji. To jest blocker użytecznej rekomendacji, "
            "nie brak promptu."
        ),
        available_read_contracts=[
            "google_ads_campaign_activity",
            "google_ads_budget_context",
            "google_ads_impression_share_context",
            "ga4_landing_source_campaign_quality",
        ],
        missing_read_contracts=[
            "demand_gen_campaign_rows",
            "demand_gen_asset_group_rows",
            "demand_gen_creative_asset_rows",
            "demand_gen_landing_quality_by_campaign",
            "demand_gen_migration_constraints",
            "demand_gen_action_object",
        ],
        blocked_claims=[
            "Demand Gen launch recommendation",
            "Demand Gen migration ready",
            "creative quality verdict",
            "asset performance verdict",
            "campaign apply",
            "performance uplift",
        ],
        source_connectors=["google_ads", "google_analytics_4"],
        evidence_ids=evidence_ids,
        action_ids=[],
        operator_review_gates=[
            "demand_gen_specific_evidence_required",
            "human_strategy_review",
            "human_confirm_before_apply",
        ],
        next_step=(
            "Zbuduj osobny Demand Gen read contract zanim skill pokaże "
            "kandydatów kampanii lub migracji. Do tego czasu używaj GA4/Ads "
            "tylko jako kontekstu jakości ruchu."
        ),
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
            "query_page_candidates_total": len(candidates),
            "query_page_candidates_included": len(candidates[:8]),
        },
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
    campaign_rows = _list_at(compact, "campaign_read_contract", "campaign_rows")
    kpi_rows = _list_at(compact, "derived_kpi_read_contract", "kpi_rows")
    budget_rows = _list_at(compact, "budget_pacing_read_contract", "budget_rows")
    search_term_rows = _list_at(
        compact,
        "search_terms_read_contract",
        "search_term_rows",
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
    _limit_contract_rows(
        compact,
        ("search_terms_read_contract", "search_term_rows"),
        ADS_CONTEXT_ROW_LIMIT,
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
    _limit_contract_rows(
        compact,
        ("recommendations_read_contract", "recommendation_rows"),
        ADS_CONTEXT_DECISION_ROW_LIMIT,
    )
    _limit_contract_rows(
        compact,
        ("custom_segments_read_contract", "payload_preview"),
        ADS_CONTEXT_ROW_LIMIT,
    )
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
    _drop_candidate_nested_payload_preview(
        compact,
        ("negative_keywords_read_contract", "candidates"),
    )
    _limit_decision_rows(compact)
    _omit_decision_row_payloads(compact)
    sections = compact.pop("sections", [])
    compact["context_pack_compaction"] = {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "full_endpoint": "/api/ads/diagnostics",
        "sections_total": len(sections) if isinstance(sections, list) else 0,
        "decision_row_payloads_omitted": True,
        "campaign_rows_total": len(campaign_rows),
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
    }
    return compact


def _compact_ads_diagnostics_for_lite_context(
    ads_diagnostics: dict[str, Any],
    *,
    allowed_decision_ids: set[str],
    allowed_action_ids: set[str] | None = None,
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
    for key in list(compact):
        if key not in keep_contracts:
            compact.pop(key, None)
    compaction = compact.get("context_pack_compaction")
    if isinstance(compaction, dict):
        decision_queue = compact.get("decision_queue")
        compaction["lite_context"] = True
        compaction["omitted_contracts"] = [
            "change_history_read_contract",
            "custom_segments_read_contract",
            "keyword_match_context_read_contract",
            "negative_keywords_read_contract",
            "recommendations_read_contract",
            "search_term_safety_read_contract",
            "search_terms_read_contract",
            "sections",
        ]
        compaction["decision_rows_included"] = len(
            decision_queue if isinstance(decision_queue, list) else []
        )
    return compact


def _compact_action_dump_for_context(action: dict[str, Any]) -> dict[str, Any]:
    compact = dict(action)
    metrics = compact.get("metrics")
    if isinstance(metrics, list):
        compact["metrics_total"] = len(metrics)
        compact["metrics"] = metrics[:3]
        compact["metrics_included"] = len(compact["metrics"])
    payload = compact.get("payload")
    if not isinstance(payload, dict):
        return compact
    compact_payload = dict(payload)
    for key in (
        "campaign_candidates",
        "budget_payload_preview",
        "recommendations",
        "terms",
        "source_terms",
        "payload_preview",
        "keyword_match_context",
    ):
        rows = compact_payload.get(key)
        if isinstance(rows, list):
            compact_payload[f"{key}_total"] = len(rows)
            compact_payload[key] = []
            compact_payload[f"{key}_included"] = len(compact_payload[key])
    compact["payload"] = compact_payload
    return compact


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


def _limit_decision_rows(data: dict[str, Any]) -> None:
    for decision in _list_at(data, "decision_queue"):
        if not isinstance(decision, dict):
            continue
        for rows_key in (
            "campaign_rows",
            "derived_kpi_rows",
            "budget_rows",
            "budget_apply_preview",
            "recommendation_rows",
            "recommendation_apply_preview",
            "impression_share_rows",
            "change_history_rows",
            "search_term_rows",
            "search_term_safety_rows",
            "keyword_match_context_rows",
            "custom_segment_candidates",
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
            "derived_kpi_rows",
            "budget_rows",
            "budget_apply_preview",
            "recommendation_rows",
            "recommendation_apply_preview",
            "impression_share_rows",
            "change_history_rows",
            "search_term_rows",
            "search_term_safety_rows",
            "keyword_match_context_rows",
            "custom_segment_candidates",
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
    clear_daily_runtime_cache()
    clear_skill_context_cache()
    return run


@app.get("/api/dashboard/command-center", response_model=CommandCenterResponse)
def command_center() -> CommandCenterResponse:
    return build_daily_runtime().command_center


@app.get("/api/marketing/brief", response_model=MarketingBrief)
def marketing_brief() -> MarketingBrief:
    return build_daily_runtime().marketing_brief


@app.get("/api/marketing/tactical-queue", response_model=TacticalQueueResponse)
def marketing_tactical_queue() -> TacticalQueueResponse:
    return build_tactical_queue()


@app.get("/api/ads/diagnostics", response_model=AdsDiagnosticsResponse)
def ads_diagnostics() -> AdsDiagnosticsResponse:
    return build_ads_diagnostics()


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
    clear_daily_runtime_cache()
    clear_skill_context_cache()
    return result


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
    clear_daily_runtime_cache()
    clear_skill_context_cache()
    if not result.applied:
        raise HTTPException(status_code=409, detail=result.model_dump(mode="json"))
    return result.model_dump(mode="json")


@app.get("/api/audit/events", response_model=list[AuditEvent])
def audit_events(action_id: str | None = None) -> list[AuditEvent]:
    return local_state_store().list_audit_events(action_id=action_id)


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
