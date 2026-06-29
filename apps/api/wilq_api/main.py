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
    DEMAND_GEN_CAMPAIGN_MODE_REVIEW_CONTRACT,
    DEMAND_GEN_CAMPAIGN_ROWS_CONTRACT,
    DEMAND_GEN_CREATIVE_ASSET_ROW_COUNT_FACT,
    DEMAND_GEN_CREATIVE_ASSET_ROWS_CONTRACT,
    DEMAND_GEN_CREATIVE_ASSET_STATUS_FACT,
    DEMAND_GEN_LANDING_QUALITY_CONTRACT,
    DEMAND_GEN_READINESS_AVAILABLE_CONTRACT,
    DEMAND_GEN_READINESS_BLOCKED_CLAIMS,
    DEMAND_GEN_READINESS_REVIEW_ACTION_ID,
    demand_gen_ad_group_ad_rows_from_facts,
    demand_gen_campaign_mode_review_rows_from_campaigns,
    demand_gen_campaign_status_label,
    demand_gen_channel_label,
    demand_gen_channel_labels,
    demand_gen_contract_has_ready_fact,
    demand_gen_contract_labels,
    demand_gen_creative_asset_rows_from_facts,
    demand_gen_landing_quality_rows_from_facts,
    demand_gen_readiness_review_payload,
)
from wilq.actions.google_ads.keyword_planner import KEYWORD_PLANNER_ACCESS_ACTION_ID
from wilq.actions.google_ads.search_term_ngrams import SEARCH_TERM_NGRAM_ACTION_ID
from wilq.actions.service import (
    _action_audit_event_label,
    apply_action,
    confirm_action,
    demand_gen_readiness_preview_cards,
    get_action,
    impact_check_action,
    list_actions,
    preview_action,
    record_action_review,
    validate_action,
)
from wilq.briefing.ads_diagnostics import build_ads_diagnostics
from wilq.briefing.ahrefs_diagnostics import build_ahrefs_diagnostics
from wilq.briefing.content_diagnostics import (
    build_content_diagnostics,
    build_content_preflight,
)
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
from wilq.operator_labels import (
    connector_refresh_status_label,
    credential_field_count_label,
    evidence_count_label,
    evidence_source_type_label,
    freshness_state_label,
    metric_fact_label,
    source_connector_label,
    source_connector_labels,
)
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
    ContentPreflightResponse,
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
    connector_status_label,
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
    skill_id: str | None = None
    focus: str | None = None
    max_opportunities: int = Field(default=5, ge=1, le=25)
    full_context: bool = False


def _request_skill(request: ContextPackRequest | None) -> str | None:
    if request is None:
        return None
    return request.skill or request.skill_id


def connector_summary(connectors: list[ConnectorStatus]) -> ConnectorSummary:
    missing = sum(1 for connector in connectors if connector.missing_credentials)
    configured = sum(1 for connector in connectors if connector.configured)
    return ConnectorSummary(
        total=len(connectors),
        configured=configured,
        missing_credentials=missing,
    )


def context_pack(request: ContextPackRequest | None = None) -> dict[str, Any]:
    skill = _request_skill(request)
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
        "current_product_rules": CONTEXT_PRODUCT_RULES,
        "available_connectors": [connector.id for connector in connectors],
        "connector_status": [
            _compact_connector_status_for_operator_context(connector)
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
    pack = _strip_raw_operator_context(pack)
    return redact_mapping(pack)


def _compact_daily_action_for_context(
    action: ActionObject,
    decision: DailyDecision | None = None,
) -> dict[str, Any]:
    dumped = action.model_dump(mode="json")
    audit_events = dumped.get("audit_events")
    latest_audit_event = _compact_audit_event_for_daily_context(
        _latest_audit_event_for_context(audit_events)
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
    _compact_action_review_gate_for_context(compact)
    if decision is not None:
        compact.update(
            {
                "decision_id": decision.id,
                "decision_status": decision.status,
                "decision_title": decision.title,
                "human_diagnosis": (f"{decision.co_widzimy} {decision.dlaczego_to_ma_znaczenie}"),
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
    return _compact_refresh_run_for_operator_context(run)


def _compact_refresh_run_for_operator_context(run: dict[str, Any]) -> dict[str, Any]:
    raw_evidence_ids = run.get("evidence_ids")
    evidence_ids: list[Any] = raw_evidence_ids if isinstance(raw_evidence_ids, list) else []
    raw_missing_credentials = run.get("missing_credentials")
    missing_credentials: list[Any] = (
        raw_missing_credentials if isinstance(raw_missing_credentials, list) else []
    )
    checked_credentials = (
        run.get("checked_credentials") if isinstance(run.get("checked_credentials"), list) else []
    )
    metric_summary = run.get("metric_summary")
    metric_keys = sorted(metric_summary.keys()) if isinstance(metric_summary, dict) else []
    connector_id = str(run.get("connector_id") or "")
    metric_labels = [metric_fact_label(key, connector_id) for key in metric_keys]
    source_label = source_connector_label(str(run.get("connector_id") or ""))
    status_label = connector_refresh_status_label(run.get("status"))
    evidence_summary_label = evidence_count_label(str(item) for item in evidence_ids)
    missing_credentials_summary_label = credential_field_count_label(
        str(item) for item in missing_credentials
    )
    summary = (
        f"Odczyt danych {source_label}: {status_label}; "
        f"{evidence_summary_label}; {missing_credentials_summary_label}."
    )
    return {
        "id": run.get("id"),
        "connector_id": run.get("connector_id"),
        "status": run.get("status"),
        "status_label": status_label,
        "connector_label": source_label,
        "started_at": run.get("started_at"),
        "completed_at": run.get("completed_at"),
        "summary": summary,
        "evidence_ids": evidence_ids,
        "missing_credentials": missing_credentials,
        "checked_credentials": checked_credentials,
        "external_call_attempted": bool(run.get("external_call_attempted")),
        "vendor_data_collected": bool(run.get("vendor_data_collected")),
        "metric_summary": {
            "metric_key_count": len(metric_keys),
            "metric_labels": metric_labels[:8],
            "metric_labels_included": min(len(metric_labels), 8),
        },
        "errors": [],
        "redacted": True,
    }


def _compact_connector_status_for_operator_context(
    connector: ConnectorStatus | dict[str, Any],
) -> dict[str, Any]:
    dumped = (
        connector.model_dump(mode="json")
        if isinstance(connector, ConnectorStatus)
        else dict(connector)
    )
    freshness = dumped.get("freshness")
    compact_freshness: Any
    if isinstance(freshness, dict):
        freshness_state = freshness.get("state") or "unknown"
        compact_freshness = {
            "state": freshness_state,
            "label": freshness_state_label(str(freshness_state)),
            "checked_at": freshness.get("checked_at"),
            "last_success_at": freshness.get("last_success_at"),
            "notes": freshness.get("notes"),
        }
    else:
        compact_freshness = freshness
    capabilities = dumped.get("capabilities")
    supported_actions = dumped.get("supported_actions")
    missing_credentials = dumped.get("missing_credentials")
    status_label = dumped.get("status_label") or connector_status_label(
        str(dumped.get("status") or "unknown")
    )
    freshness_label = (
        compact_freshness.get("label")
        if isinstance(compact_freshness, dict)
        else freshness_state_label(None)
    )
    return {
        "id": dumped.get("id"),
        "label": dumped.get("label"),
        "status": dumped.get("status"),
        "status_label": status_label,
        "configured": dumped.get("configured"),
        "freshness": compact_freshness,
        "last_success_at": dumped.get("last_success_at"),
        "missing_credentials": (
            missing_credentials if isinstance(missing_credentials, list) else []
        ),
        "capability_count": len(capabilities) if isinstance(capabilities, list) else 0,
        "supported_action_count": (
            len(supported_actions) if isinstance(supported_actions, list) else 0
        ),
        "summary": (
            f"Źródło danych {dumped.get('label') or dumped.get('id')}: "
            f"{status_label}; {freshness_label}."
        ),
    }


def _compact_evidence_for_operator_context(evidence: Evidence) -> dict[str, Any]:
    dumped = evidence.model_dump(mode="json")
    freshness = dumped.get("freshness")
    freshness_state = None
    if isinstance(freshness, dict):
        freshness_state = freshness.get("state")
    source_connector = dumped.get("source_connector")
    source_type = dumped.get("source_type")
    source_label = source_connector_label(source_connector)
    source_type_label = evidence_source_type_label(source_type)
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


def _strip_raw_operator_context(value: Any) -> Any:
    if isinstance(value, list):
        return [_strip_raw_operator_context(item) for item in value]
    if not isinstance(value, dict):
        return value
    stripped: dict[str, Any] = {}
    for key, item in value.items():
        if key == "mode" and item == "vendor_read":
            continue
        stripped[key] = _strip_raw_operator_context(item)
    return stripped


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


def _compact_audit_event_for_daily_context(event: dict[str, Any] | None) -> dict[str, Any] | None:
    if event is None:
        return None
    event_type = event.get("event_type") or "unknown"
    event_type_label = event.get("event_type_label") or _action_audit_event_label(str(event_type))
    summary = (
        f"Ślad bezpieczeństwa: {event_type_label}. "
        "Szczegóły techniczne są dostępne w szczegółach akcji WILQ."
    )
    return {
        "id": event.get("id"),
        "action_id": event.get("action_id"),
        "event_type": event_type,
        "event_type_label": event_type_label,
        "actor": event.get("actor"),
        "created_at": event.get("created_at"),
        "summary": summary,
    }


def _compact_audit_event_for_skill_context(event: dict[str, Any] | None) -> dict[str, Any] | None:
    if event is None:
        return None
    event_type = event.get("event_type") or "unknown"
    event_type_label = event.get("event_type_label") or _action_audit_event_label(str(event_type))
    return {
        "id": event.get("id"),
        "action_id": event.get("action_id"),
        "event_type": event_type,
        "event_type_label": event_type_label,
        "actor": event.get("actor"),
        "created_at": event.get("created_at"),
        "summary": (
            f"Ślad bezpieczeństwa: {event_type_label}. "
            "Szczegóły techniczne są dostępne w szczegółach akcji WILQ."
        ),
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
            _compact_metric_fact_for_context(fact)
            for fact in metric_facts[:8]
            if isinstance(fact, dict)
        ]
        compact["metric_facts_included"] = len(compact["metric_facts"])
    return compact


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


def _compact_marketing_brief_for_skill_context(
    brief: MarketingBrief,
    *,
    include_top_metric_facts: bool = True,
) -> dict[str, Any]:
    dumped = brief.model_dump(mode="json")
    compact_sections = []
    item_total = 0
    for section in dumped.get("sections", []):
        items = section.get("items", []) if isinstance(section, dict) else []
        item_total += len(items)
        compact_items = []
        for item in items[:3]:
            if not isinstance(item, dict):
                continue
            metric_facts = item.get("metric_facts")
            compact_items.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "kind": item.get("kind"),
                    "priority": item.get("priority"),
                    "source_connectors": item.get("source_connectors") or [],
                    "evidence_ids": (item.get("evidence_ids") or [])[:6],
                    "action_ids": item.get("action_ids") or [],
                    "summary": _context_pack_text(item.get("summary"), limit=180),
                    "next_step": _context_pack_text(item.get("next_step"), limit=180),
                    "risk": item.get("risk"),
                    "metric_fact_count": (
                        len(metric_facts) if isinstance(metric_facts, list) else 0
                    ),
                }
            )
        compact_sections.append(
            {
                "id": section.get("id"),
                "title": section.get("title"),
                "description": _context_pack_text(section.get("description"), limit=180),
                "items": compact_items,
                "items_total": len(items),
                "items_included": len(compact_items),
            }
        )
    return {
        "generated_at": dumped.get("generated_at"),
        "language": dumped.get("language"),
        "strict_instruction": dumped.get("strict_instruction"),
        "connector_summary": dumped.get("connector_summary"),
        "sections": compact_sections,
        "top_metric_facts": [
            _compact_metric_fact_for_context(fact)
            for fact in dumped.get("top_metric_facts", [])[:5]
            if isinstance(fact, dict)
        ]
        if include_top_metric_facts
        else [],
        "evidence_ids": (dumped.get("evidence_ids") or [])[:20],
        "action_ids": dumped.get("action_ids") or [],
        "blocker_count": dumped.get("blocker_count"),
        "recommendation_count": dumped.get("recommendation_count"),
        "context_pack_compaction": {
            "sections_compacted": True,
            "items_total": item_total,
            "items_per_section_limit": 3,
            "top_metric_facts_limit": 5 if include_top_metric_facts else 0,
            "full_endpoint": "/api/marketing/brief",
        },
    }


def _compact_tactical_queue_for_skill_context(
    queue: TacticalQueueResponse,
) -> dict[str, Any]:
    dumped = queue.model_dump(mode="json")
    raw_items = dumped.get("items")
    items: list[Any] = raw_items if isinstance(raw_items, list) else []
    raw_groups = dumped.get("compact_groups")
    groups: list[Any] = raw_groups if isinstance(raw_groups, list) else []
    compact_items = []
    for item in items[:8]:
        if not isinstance(item, dict):
            continue
        metric_facts = item.get("metric_facts")
        compact_items.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "domain": item.get("domain"),
                "intent": item.get("intent"),
                "priority": item.get("priority"),
                "risk": item.get("risk"),
                "source_connectors": item.get("source_connectors") or [],
                "evidence_ids": (item.get("evidence_ids") or [])[:6],
                "action_ids": item.get("action_ids") or [],
                "diagnosis": _context_pack_text(item.get("diagnosis"), limit=180),
                "next_step": _context_pack_text(item.get("next_step"), limit=180),
                "blocked_claims": (item.get("blocked_claims") or [])[:6],
                "metric_fact_count": (len(metric_facts) if isinstance(metric_facts, list) else 0),
            }
        )
    compact_groups = []
    for group in groups[:8]:
        if not isinstance(group, dict):
            continue
        compact_groups.append(
            {
                "id": group.get("id"),
                "title": group.get("title"),
                "meta": group.get("meta"),
                "diagnosis": _context_pack_text(group.get("diagnosis"), limit=180),
                "next_step": _context_pack_text(group.get("next_step"), limit=180),
                "priority": group.get("priority"),
                "risk": group.get("risk"),
                "source_connectors": group.get("source_connectors") or [],
                "evidence_ids": (group.get("evidence_ids") or [])[:6],
                "action_ids": group.get("action_ids") or [],
                "blocked_claims": (group.get("blocked_claims") or [])[:6],
            }
        )
    return {
        "generated_at": dumped.get("generated_at"),
        "language": dumped.get("language"),
        "strict_instruction": dumped.get("strict_instruction"),
        "items": compact_items,
        "compact_groups": compact_groups,
        "evidence_ids": (dumped.get("evidence_ids") or [])[:20],
        "action_ids": dumped.get("action_ids") or [],
        "context_pack_compaction": {
            "items_compacted": True,
            "items_total": len(items),
            "items_included": len(compact_items),
            "compact_groups_total": len(groups),
            "compact_groups_included": len(compact_groups),
            "metric_facts_removed": True,
            "full_endpoint": "/api/marketing/tactical-queue",
        },
    }


def _compact_metric_fact_for_context(fact: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric_label": fact.get("metric_label"),
        "value": fact.get("value"),
        "unit": fact.get("unit"),
        "period": fact.get("period"),
        "source_connector": fact.get("source_connector"),
        "evidence_id": fact.get("evidence_id"),
        "dimensions": _compact_dimensions_for_context(
            fact.get("dimensions"),
            dimension_labels=fact.get("dimension_labels"),
            dimension_value_labels=fact.get("dimension_value_labels"),
        ),
        "freshness_label": fact.get("freshness_label"),
        "trend": fact.get("trend"),
    }


def _compact_dimensions_for_context(
    dimensions: Any,
    *,
    dimension_labels: Any = None,
    dimension_value_labels: Any = None,
) -> dict[str, str]:
    if not isinstance(dimensions, dict):
        return {}
    labels = dimension_labels if isinstance(dimension_labels, dict) else {}
    value_labels = dimension_value_labels if isinstance(dimension_value_labels, dict) else {}
    compact: dict[str, str] = {}
    for key, _value in list(dimensions.items())[:8]:
        label = str(labels.get(key) or "").strip()
        value_label = str(value_labels.get(key) or "").strip()
        if label in {"", "wymiar"} or value_label in {
            "",
            "wartość wymiaru do sprawdzenia",
        }:
            continue
        compact_label = label
        suffix = 2
        while compact_label in compact:
            compact_label = f"{label} {suffix}"
            suffix += 1
        compact[compact_label] = (
            value_label if len(value_label) <= 160 else f"{value_label[:157]}..."
        )
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
    "wilq-content-strategist": {"act_prepare_content_refresh_queue"},
    "wilq-custom-segments": {
        "act_prepare_custom_segments_from_search_terms",
    },
    "wilq-demand-gen-operator": {DEMAND_GEN_READINESS_REVIEW_ACTION_ID},
    "wilq-ga4-analyst": {"act_review_ga4_tracking_quality"},
    "wilq-gsc-content-doctor": {"act_prepare_content_refresh_queue"},
    "wilq-localo-operator": {"act_review_localo_visibility_facts"},
    "wilq-social-publisher": {
        "act_prepare_facebook_social_drafts",
        "act_prepare_linkedin_social_drafts",
    },
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
    "wilq-content-strategist": [
        "seo_gsc_opportunities_v1",
        "seo_query_page_matrix_v1",
        "seo_content_decay_v1",
        "seo_cannibalization_v1",
        "content_duplication_rules_v1",
        "content_brief_rules_v1",
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
    skill = _request_skill(request) or "unknown"
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
        evidence_id for action in scoped_actions for evidence_id in action.evidence_ids
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
        "current_product_rules": CONTEXT_PRODUCT_RULES,
        "available_connectors": [connector.id for connector in connectors],
        "connector_status": [
            _compact_connector_status_for_operator_context(connector)
            for connector in connectors
            if connector.id in scoped_connectors
        ],
        "top_opportunities": [
            _compact_opportunity_for_daily_context(opportunity)
            for opportunity in scoped_opportunities
        ],
        "active_action_objects": [
            _compact_action_dump_for_context(action.model_dump(mode="json"), skill=skill)
            for action in scoped_actions
        ],
        "connector_refresh_runs": [
            _compact_refresh_run_for_operator_context(run.model_dump(mode="json"))
            for run in list_connector_refresh_runs()[:25]
            if run.connector_id in scoped_connectors
        ][:connector_refresh_run_limit],
        "evidence_summaries": [
            _compact_evidence_for_operator_context(evidence) for evidence in scoped_evidence
        ][:evidence_summary_limit],
        "knowledge_card_summaries": [
            _compact_knowledge_card_for_operator_context(card)
            for card in _knowledge_cards_for_skill(skill)
        ],
        "expert_rule_summaries": [
            _compact_expert_rule_for_operator_context(rule)
            for rule in _expert_rules_for_skill(skill)
        ],
        "expert_capabilities": [
            _compact_expert_capability_for_operator_context(capability)
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
    pack = _strip_raw_operator_context(pack)
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
            _request_skill(request) or "",
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
        content = build_content_diagnostics()
        return {
            "content_diagnostics": _compact_content_diagnostics_for_context(
                content.model_dump(mode="json")
            ),
            "content_preflight": build_content_preflight(content).model_dump(mode="json"),
        }
    if skill == "wilq-gsc-content-doctor":
        content = build_content_diagnostics()
        return {
            "content_diagnostics": _compact_gsc_content_diagnostics_for_context(
                content.model_dump(mode="json")
            ),
            "content_preflight": build_content_preflight(content).model_dump(mode="json"),
        }
    if skill == "wilq-ahrefs-gap-finder":
        return {
            "ahrefs_diagnostics": _compact_ahrefs_diagnostics_for_context(
                build_ahrefs_diagnostics().model_dump(mode="json")
            )
        }
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
        runtime = build_daily_runtime()
        return {
            "marketing_brief": _compact_marketing_brief_for_skill_context(
                runtime.marketing_brief,
                include_top_metric_facts=False,
            ),
            "tactical_queue": _compact_tactical_queue_for_skill_context(build_tactical_queue()),
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
    missing_publish_access = {
        connector_id: connector_status_by_id[connector_id].missing_credentials
        for connector_id in ("linkedin", "facebook")
        if connector_id in connector_status_by_id
        and connector_status_by_id[connector_id].missing_credentials
    }
    source_inputs: list[dict[str, Any]] = []
    draft_constraints: list[str] = []
    blocked_claims = ["opublikowanie posta", "wzrost skuteczności social"]
    source_metric_names: list[str] = []
    source_connectors: list[str] = []
    evidence_ids: list[str] = []
    for action in social_actions:
        payload = action.payload
        if isinstance(payload, dict):
            source_inputs.extend(
                item for item in payload.get("source_inputs", []) if isinstance(item, dict)
            )
            draft_constraints.extend(
                str(item) for item in payload.get("draft_constraints", []) if item
            )
            blocked_claims.extend(str(item) for item in payload.get("blocked_claims", []) if item)
            source_metric_names.extend(
                str(item) for item in payload.get("source_metric_names", []) if item
            )
            source_connectors.extend(
                str(item) for item in payload.get("source_connectors", []) if item
            )
        evidence_ids.extend(action.evidence_ids)
    return {
        "mode": "review_only",
        "publish_allowed": False,
        "missing_publish_access": missing_publish_access,
        "draft_action_ids": [action.id for action in social_actions],
        "source_inputs": source_inputs[:8],
        "draft_constraints": sorted(set(draft_constraints)),
        "blocked_claims": sorted(set(blocked_claims)),
        "source_metric_names": sorted(set(source_metric_names)),
        "source_connectors": sorted(set(source_connectors)),
        "evidence_ids": list(dict.fromkeys(evidence_ids))[:12],
        "operator_next_step": (
            "Przygotuj szkice do sprawdzenia z dowodami; publikacja pozostaje "
            "zablokowana do czasu konfiguracji uprawnień LinkedIn/Facebook."
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
        dict.fromkeys(fact.evidence_id for fact in ga4_metric_facts if fact.evidence_id)
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
    demand_gen_campaign_mode_review_rows = demand_gen_campaign_mode_review_rows_from_campaigns(
        demand_gen_campaign_row_dicts,
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
        labeled_channel_counts = demand_gen_channel_labels(channel_counts)
        channel_summary = (
            ", ".join(
                f"{label}: {channel_counts[channel]}"
                for channel, label in labeled_channel_counts.items()
            )
            or "brak rozpoznanych kanałów"
        )
        campaign_context = (
            f"WILQ ocenił {len(campaign_rows)} kampanii Ads. "
            f"Kanały w odczycie: {channel_summary}. "
            f"Kampanie Demand Gen/Discovery: {len(demand_gen_campaign_rows)}. "
        )
    else:
        missing_read_contracts.insert(0, DEMAND_GEN_CAMPAIGN_ROWS_CONTRACT)
        campaign_context = "WILQ nie ma jeszcze pewnego odczytu typów kanałów kampanii Ads."
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
            DEMAND_GEN_CAMPAIGN_MODE_REVIEW_CONTRACT,
        ]
    )
    available_contract_labels = demand_gen_contract_labels(available_read_contracts)
    missing_contract_labels = demand_gen_contract_labels(missing_read_contracts)
    operator_review_gates = [
        "demand_gen_specific_evidence_required",
        "human_strategy_review",
        "human_confirm_before_apply",
    ]
    missing_contract_summary = ", ".join(missing_contract_labels)
    title = (
        "Demand Gen: sprawdź istniejące kampanie bez uruchamiania zmian"
        if demand_gen_campaign_rows
        else "Demand Gen: brak kampanii do rekomendacji"
    )
    payload = demand_gen_readiness_review_payload(
        campaign_rows_evaluated=len(campaign_rows),
        campaign_channel_counts=channel_counts,
        demand_gen_campaign_rows=[row.model_dump(mode="json") for row in demand_gen_campaign_rows],
        demand_gen_ad_group_ad_rows=[
            row.model_dump(mode="json") for row in demand_gen_ad_group_ad_rows
        ],
        demand_gen_creative_asset_rows=[
            row.model_dump(mode="json") for row in demand_gen_creative_asset_rows
        ],
        demand_gen_landing_quality_rows=[
            row.model_dump(mode="json") for row in demand_gen_landing_quality_rows
        ],
        demand_gen_campaign_mode_review_rows=[
            row.model_dump(mode="json") for row in demand_gen_campaign_mode_review_rows
        ],
        available_read_contracts=available_read_contracts,
        missing_read_contracts=missing_read_contracts,
        source_connectors=["google_ads", "google_analytics_4"],
        evidence_ids=evidence_ids,
    )
    action_ids = [DEMAND_GEN_READINESS_REVIEW_ACTION_ID] if payload is not None else []
    payload_preview = payload["payload_preview"] if payload is not None else []
    preview_cards = demand_gen_readiness_preview_cards(payload) if payload is not None else []
    return DemandGenReadinessContract(
        status="blocked",
        title=title,
        summary=(
            f"{campaign_context} WILQ ma dowody Ads i GA4 do oceny ruchu. "
            "Odczyty reklam i kreacji Demand Gen są traktowane jako dostępne "
            "tylko wtedy, gdy API zwraca je w dostępnych danych. "
            + (
                f"Nadal brakuje danych: {missing_contract_summary}. "
                if missing_contract_summary
                else (
                    "WILQ nie wykrywa brakujących danych w tym odczycie, "
                    "ale nadal nie widzi kampanii Demand Gen/Discovery do rekomendacji. "
                )
            )
            + "To blokuje użyteczną rekomendację; nie jest to problem treści polecenia."
        ),
        metric_tiles={
            "kampanie Ads": len(campaign_rows),
            "kanały": len(channel_counts),
            "kampanie Demand Gen": len(demand_gen_campaign_rows),
            "reklamy Demand Gen": len(demand_gen_ad_group_ad_rows),
            "kreacje Demand Gen": len(demand_gen_creative_asset_rows),
            "strony wejścia Demand Gen": len(demand_gen_landing_quality_rows),
            "kontrola trybu": len(demand_gen_campaign_mode_review_rows),
            "braki": len(missing_read_contracts),
        },
        available_read_contracts=available_read_contracts,
        available_read_contract_labels=available_contract_labels,
        missing_read_contracts=missing_read_contracts,
        missing_read_contract_labels=missing_contract_labels,
        blocked_claims=DEMAND_GEN_READINESS_BLOCKED_CLAIMS,
        source_connectors=["google_ads", "google_analytics_4"],
        source_connector_labels=source_connector_labels(["google_ads", "google_analytics_4"]),
        evidence_ids=evidence_ids,
        evidence_summary_label=evidence_count_label(evidence_ids),
        action_ids=action_ids,
        operator_review_gates=operator_review_gates,
        operator_review_gate_labels=demand_gen_contract_labels(operator_review_gates),
        payload_preview=payload_preview,
        preview_cards=preview_cards,
        campaign_rows_evaluated=len(campaign_rows),
        campaign_channel_counts=channel_counts,
        campaign_channel_labels=demand_gen_channel_labels(channel_counts),
        demand_gen_campaign_rows=demand_gen_campaign_rows,
        demand_gen_ad_group_ad_rows=demand_gen_ad_group_ad_rows,
        demand_gen_creative_asset_rows=demand_gen_creative_asset_rows,
        demand_gen_landing_quality_rows=demand_gen_landing_quality_rows,
        demand_gen_campaign_mode_review_rows=demand_gen_campaign_mode_review_rows,
        next_step=(
            "Sprawdź gotowość Demand Gen w WILQ jako akcję tylko do przeglądu. "
            "Zanim WILQ pokaże propozycje uruchomienia albo zmiany trybu kampanii, "
            "potwierdź dostępność danych o jakości stron wejścia i kontroli trybu kampanii."
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


def _compact_campaign_row_for_demand_gen(row: dict[str, Any]) -> AdsCampaignMetricRow:
    return AdsCampaignMetricRow(
        campaign_id=row.get("campaign_id"),
        campaign_name=row.get("campaign_name") or "campaign",
        campaign_status=row.get("campaign_status"),
        campaign_status_label=demand_gen_campaign_status_label(row.get("campaign_status")),
        advertising_channel_type=row.get("advertising_channel_type"),
        advertising_channel_type_label=demand_gen_channel_label(
            row.get("advertising_channel_type")
        ),
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
    decision_queue = compact.get("decision_queue")
    if isinstance(decision_queue, list):
        compact["decision_queue"] = [
            _compact_content_decision_for_context(decision)
            for decision in decision_queue
            if isinstance(decision, dict)
        ]
    sections = compact.pop("sections", [])
    connectors = compact.get("connectors")
    if isinstance(connectors, list):
        compact["connectors"] = [
            _compact_connector_status_for_operator_context(connector)
            for connector in connectors
            if isinstance(connector, dict)
        ]
    latest_refreshes = compact.get("latest_refreshes")
    if isinstance(latest_refreshes, list):
        compact["latest_refreshes"] = [
            _compact_refresh_run_for_operator_context(refresh)
            for refresh in latest_refreshes
            if isinstance(refresh, dict)
        ]
    compact["context_pack_compaction"] = {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "sections_total": len(sections) if isinstance(sections, list) else 0,
        "connectors_compacted": True,
        "latest_refreshes_compacted": True,
        "full_endpoint": "/api/content/diagnostics",
    }
    return compact


def _compact_content_decision_for_context(decision: dict[str, Any]) -> dict[str, Any]:
    compact = dict(decision)
    ahrefs_rows = compact.get("ahrefs_candidate_rows")
    if isinstance(ahrefs_rows, list):
        compact["ahrefs_candidate_rows_total"] = len(ahrefs_rows)
        compact["ahrefs_candidate_rows"] = [
            _compact_content_ahrefs_candidate_row_for_context(row)
            for row in ahrefs_rows[:4]
            if isinstance(row, dict)
        ]
        compact["ahrefs_candidate_rows_included"] = len(compact["ahrefs_candidate_rows"])
    return compact


def _compact_content_ahrefs_candidate_row_for_context(
    row: dict[str, Any],
) -> dict[str, Any]:
    keep_keys = {
        "topic",
        "gap_type_label",
        "relevance_status_label",
        "relevance_score",
        "business_relevance_reason_labels",
        "gsc_demand_label",
        "wordpress_inventory_match_label",
        "gsc_overlap_terms",
        "wordpress_overlap_urls",
        "keyword",
        "competitor_domain",
        "source_url",
        "referenced_public_url",
        "metric_value",
        "evidence_ids",
        "next_step",
    }
    compact = {key: row[key] for key in keep_keys if key in row}
    for key, limit in (
        ("business_relevance_reason_labels", 4),
        ("gsc_overlap_terms", 4),
        ("wordpress_overlap_urls", 3),
        ("evidence_ids", 3),
    ):
        value = compact.get(key)
        if isinstance(value, list):
            compact[key] = value[:limit]
            compact[f"{key}_total"] = len(value)
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


def _compact_ahrefs_diagnostics_for_context(
    ahrefs_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    compact = dict(_without_metric_facts(ahrefs_diagnostics))
    sections = compact.pop("sections", [])
    connector = compact.get("connector")
    if isinstance(connector, dict):
        compact["connector"] = _compact_connector_status_for_operator_context(connector)
    connector_status = compact.get("connector_status")
    if isinstance(connector_status, dict):
        compact["connector_status"] = _compact_connector_status_for_operator_context(
            connector_status
        )
    latest_refresh = compact.get("latest_refresh")
    if isinstance(latest_refresh, dict):
        compact["latest_refresh"] = _compact_refresh_run_for_operator_context(latest_refresh)
    gap_contract = compact.get("gap_read_contract")
    if isinstance(gap_contract, dict):
        _compact_labelled_contract_list_for_context(
            gap_contract,
            raw_key="available_read_contracts",
            label_key="available_read_contract_labels",
        )
        _compact_labelled_contract_list_for_context(
            gap_contract,
            raw_key="allowed_evidence",
            label_key="allowed_evidence_labels",
        )
        _compact_labelled_contract_list_for_context(
            gap_contract,
            raw_key="missing_read_contracts",
            label_key="missing_read_contract_labels",
        )
        gap_records = gap_contract.pop("gap_records", [])
        gap_record_count = gap_contract.get("gap_record_count")
        if gap_record_count is None:
            gap_contract["gap_record_count"] = (
                len(gap_records) if isinstance(gap_records, list) else 0
            )
        gap_contract["gap_records_omitted"] = True
        gap_contract["gap_records_total"] = len(gap_records) if isinstance(gap_records, list) else 0
    operator_summary = compact.get("operator_summary")
    if isinstance(operator_summary, dict):
        _compact_labelled_contract_list_for_context(
            operator_summary,
            raw_key="available_read_contracts",
            label_key="available_read_contract_labels",
        )
        _compact_labelled_contract_list_for_context(
            operator_summary,
            raw_key="missing_read_contracts",
            label_key="missing_read_contract_labels",
        )
    decision_queue = compact.get("decision_queue")
    if isinstance(decision_queue, list):
        compact["decision_queue"] = [
            _compact_ahrefs_decision_for_context(decision)
            for decision in decision_queue
            if isinstance(decision, dict)
        ]
    compact["context_pack_compaction"] = {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "sections_total": len(sections) if isinstance(sections, list) else 0,
        "latest_refresh_compacted": isinstance(latest_refresh, dict),
        "gap_records_omitted": isinstance(gap_contract, dict),
        "full_endpoint": "/api/ahrefs/diagnostics",
    }
    return compact


def _compact_ahrefs_decision_for_context(decision: dict[str, Any]) -> dict[str, Any]:
    compact = dict(decision)
    _compact_labelled_contract_list_for_context(
        compact,
        raw_key="allowed_evidence",
        label_key="allowed_evidence_labels",
    )
    _compact_labelled_contract_list_for_context(
        compact,
        raw_key="missing_read_contracts",
        label_key="missing_read_contract_labels",
    )
    metric_fact_labels = compact.get("metric_fact_labels")
    if isinstance(metric_fact_labels, dict):
        labels = list(metric_fact_labels.values())
        compact["metric_fact_labels_total"] = len(labels)
        compact["metric_fact_labels"] = labels[:8]
        compact["metric_fact_labels_included"] = len(compact["metric_fact_labels"])
    return compact


def _compact_labelled_contract_list_for_context(
    payload: dict[str, Any],
    *,
    raw_key: str,
    label_key: str,
) -> None:
    raw_values = payload.get(raw_key)
    labels = payload.get(label_key)
    raw_count = len(raw_values) if isinstance(raw_values, list) else 0
    if isinstance(labels, list):
        payload[f"{label_key}_total"] = len(labels)
        payload[label_key] = labels[:6]
        payload[f"{label_key}_included"] = len(payload[label_key])
    elif raw_count:
        payload[f"{label_key}_total"] = raw_count
        payload[f"{label_key}_included"] = 0
    payload[f"{raw_key}_total"] = raw_count
    payload.pop(raw_key, None)


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
    issue_clusters = compact.pop("issue_clusters", [])
    decision_queue = compact.pop("decision_queue", [])
    product_performance = compact.get("product_performance_readiness")
    if isinstance(product_performance, dict):
        performance_rows = product_performance.get("performance_rows")
        if isinstance(performance_rows, list):
            product_performance["performance_rows_total"] = len(performance_rows)
            product_performance["performance_rows"] = []
            product_performance["performance_rows_included"] = 0
    price_impact = compact.get("price_impact_readiness")
    if isinstance(price_impact, dict):
        change_preview = price_impact.get("change_preview")
        if isinstance(change_preview, list):
            price_impact["change_preview_total"] = len(change_preview)
            price_impact["change_preview"] = [
                _compact_merchant_price_impact_preview_for_context(preview)
                for preview in change_preview[:2]
                if isinstance(preview, dict)
            ]
            price_impact["change_preview_included"] = len(price_impact["change_preview"])
    operator_summary = compact.get("operator_summary")
    if isinstance(operator_summary, dict):
        operator_summary.pop("top_decision_ids", None)
        operator_summary.pop("top_issue_cluster_ids", None)
        operator_summary.pop("top_tactical_item_ids", None)
        operator_summary["decision_source"] = "kolejka decyzji Merchant"
        operator_summary["drilldown_source"] = "szczegóły problemów feedu"
        operator_summary["count_semantics"] = "zgłoszenia problemów, nie unikalne produkty"
    compact["issue_cluster_summaries"] = _compact_merchant_issue_clusters_for_context(
        issue_clusters
    )
    compact["decision_queue"] = _compact_merchant_decision_queue_for_context(decision_queue)
    compact["context_pack_compaction"] = {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "sections_total": len(sections) if isinstance(sections, list) else 0,
        "issue_clusters_total": len(issue_clusters) if isinstance(issue_clusters, list) else 0,
        "issue_clusters_included": len(compact["issue_cluster_summaries"]),
        "decision_queue_total": len(decision_queue) if isinstance(decision_queue, list) else 0,
        "decision_queue_included": len(compact["decision_queue"]),
        "raw_merchant_vendor_values_removed": True,
        "full_endpoint": "/api/merchant/diagnostics",
    }
    return compact


def _compact_merchant_issue_clusters_for_context(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    compact_clusters: list[dict[str, Any]] = []
    for cluster in value[:4]:
        if not isinstance(cluster, dict):
            continue
        compact_clusters.append(
            {
                "problem": cluster.get("issue_type_label") or "problem feedu",
                "atrybut": cluster.get("affected_attribute_label") or "atrybut",
                "kontekst": cluster.get("reporting_context_label") or "kontekst raportowania",
                "status": cluster.get("severity_label") or cluster.get("risk"),
                "rozwiązanie": cluster.get("resolution_label") or "wymaga sprawdzenia w Merchant",
                "zgłoszenia": cluster.get("product_count"),
                "country": cluster.get("country"),
                "next_step": _context_pack_text(cluster.get("next_step"), limit=180),
                "evidence_ids": (cluster.get("evidence_ids") or [])[:3],
                "action_id": cluster.get("action_id"),
            }
        )
    return compact_clusters


def _compact_merchant_decision_queue_for_context(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    selected_decisions = _selected_merchant_context_decisions(value)
    compact_decisions: list[dict[str, Any]] = []
    for index, decision in enumerate(selected_decisions, start=1):
        if not isinstance(decision, dict):
            continue
        change_preview = decision.get("change_preview")
        compact_decision = {
            "decision_ref": f"merchant_decision_{index}",
            "decision_type": decision.get("decision_type"),
            "status": decision.get("status"),
            "priority": decision.get("priority"),
            "problem": decision.get("issue_type_label") or "problem feedu",
            "atrybut": decision.get("affected_attribute_label") or "atrybut",
            "kontekst": (decision.get("reporting_context_label") or "kontekst raportowania"),
            "summary": _context_pack_text(decision.get("summary"), limit=220),
            "next_step": _context_pack_text(decision.get("next_step"), limit=200),
            "metric_tiles": decision.get("metric_tiles") or {},
            "change_preview_total": (
                len(change_preview) if isinstance(change_preview, list) else 0
            ),
            "change_preview": _compact_merchant_issue_preview_for_context(
                change_preview if isinstance(change_preview, list) else []
            ),
            "evidence_ids": (decision.get("evidence_ids") or [])[:4],
            "source_connectors": decision.get("source_connectors") or [],
            "action_ids": decision.get("action_ids") or [],
            "blocked_claims": _priority_limited_strings(
                decision.get("blocked_claims"),
                [
                    "wpływ zmiany ceny",
                    "zwrot z reklam na poziomie produktu",
                    "opłacalność produktu",
                    "zapis do feedu",
                    "odzyskany przychód produktu",
                    "efekt naprawy produktu",
                ],
                limit=6,
            ),
            "count_semantics": "zgłoszenia problemów, nie unikalne produkty",
        }
        safe_id = _safe_merchant_context_id(decision.get("id"))
        if safe_id is not None:
            compact_decision["id"] = safe_id
        compact_decisions.append(compact_decision)
    return compact_decisions


def _selected_merchant_context_decisions(value: list[Any]) -> list[Any]:
    required_ids = {
        "merchant_decision_review_ads_product_state_mapping",
        "merchant_decision_review_price_impact_readiness",
    }
    selected: list[Any] = []
    seen: set[int] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        if item.get("id") in required_ids:
            selected.append(item)
            seen.add(id(item))
    for item in value:
        if len(selected) >= 6:
            break
        if not isinstance(item, dict) or id(item) in seen:
            continue
        selected.append(item)
        seen.add(id(item))
    return selected


def _safe_merchant_context_id(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    blocked_fragments = {
        "landing_page_error",
        "shopping_ads",
        "merchant_action",
        "free_listings",
        "n_link",
    }
    lowered = value.lower()
    if any(fragment in lowered for fragment in blocked_fragments):
        return None
    return value


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
        {evidence_id for candidate in candidates for evidence_id in candidate["evidence_ids"]}
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
    _drop_recommendation_row_nested_payload_preview_for_context(compact)
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
    _compact_custom_segment_candidate_search_term_rows_for_context(compact)
    _limit_candidate_rows(
        compact,
        ("negative_keywords_read_contract", "candidates"),
        "keyword_context_rows",
        ADS_CONTEXT_DECISION_ROW_LIMIT,
    )
    _compact_negative_keyword_candidate_context_rows_for_context(compact)
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
    _drop_empty_decision_row_lists_for_context(compact)
    _compact_ads_decision_queue_for_context(compact)
    sections = compact.pop("sections", [])
    compact["context_pack_compaction"] = {
        "metric_facts_removed": True,
        "sections_omitted": True,
        "full_endpoint": "/api/ads/diagnostics",
        "sections_total": len(sections) if isinstance(sections, list) else 0,
        "decision_row_payloads_omitted": True,
        "empty_decision_row_lists_omitted": True,
        "campaign_rows_total": len(campaign_rows),
        "campaign_rows_included": len(_list_at(compact, "campaign_read_contract", "campaign_rows")),
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
        "recommendation_row_payload_previews_omitted": True,
        "custom_segment_payload_preview_total": len(custom_payload_preview),
        "custom_segment_payload_preview_included": len(
            _list_at(compact, "custom_segments_read_contract", "payload_preview")
        ),
        "custom_segment_candidate_search_term_rows_compacted": True,
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
        "negative_keyword_candidate_context_rows_compacted": True,
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
        "zmiana budżetu",
        "zapis rekomendacji",
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
        "zmiana budżetu",
        "dodanie wykluczających słów kluczowych",
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
        "zmiana budżetu",
        "dodanie wykluczających słów kluczowych",
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
            "search_budget_lost_impression_share": row.get("search_budget_lost_impression_share"),
            "recommendation_count": row.get("recommendation_count"),
            "has_budget_apply_preview": row.get("has_budget_apply_preview"),
            "has_recommendation_apply_preview": row.get("has_recommendation_apply_preview"),
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
        compact_item["safety_review"] = _compact_budget_safety_review_item(safety_review)
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
            if isinstance(decision, dict) and str(decision.get("id")) in allowed_decision_ids
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


def _compact_action_dump_for_context(action: dict[str, Any], *, skill: str) -> dict[str, Any]:
    compact = dict(action)
    if compact.get("id") == KEYWORD_PLANNER_ACCESS_ACTION_ID:
        compact["human_diagnosis"] = (
            "Wzbogacenie Keyword Planner jest zablokowane przez Google Ads API."
        )
        compact["recommended_reason"] = (
            "Odblokuj dostęp tokena deweloperskiego przed użyciem prognoz, "
            "rozmiaru odbiorców i twierdzeń opartych na Keyword Plannerze."
        )
        review_gate = compact.get("review_gate")
        if isinstance(review_gate, dict):
            apply_blockers = review_gate.get("apply_blockers")
            if not isinstance(apply_blockers, list):
                apply_blockers = []
            apply_blocker_labels = review_gate.get("apply_blocker_labels")
            if not isinstance(apply_blocker_labels, list):
                apply_blocker_labels = []
            compact["review_gate"] = {
                "status": review_gate.get("status"),
                "apply_allowed": review_gate.get("apply_allowed"),
                "confirmation_required": review_gate.get("confirmation_required"),
                "apply_blockers_total": len(apply_blockers),
                "apply_blocker_labels": apply_blocker_labels[:4],
                "apply_blockers_included": min(len(apply_blockers), 4),
            }
    if compact.get("id") == SEARCH_TERM_NGRAM_ACTION_ID:
        compact["human_diagnosis"] = (
            "Przegląd tematów zapytań z Google Ads oparty o dowody "
            "z wyszukiwanych haseł; nie wykonuj zmian."
        )
        compact["recommended_reason"] = (
            "Sprawdź intencję tematów i próbki zapytań przed kolejką sprawdzenia wykluczeń."
        )
        compact["evidence_ids"] = compact.get("evidence_ids", [])[:1]
    audit_events = compact.get("audit_events")
    compact["latest_audit_event"] = _compact_audit_event_for_skill_context(
        _latest_audit_event_for_context(audit_events)
    )
    compact.pop("audit_events", None)
    _compact_action_review_gate_for_context(compact)
    metrics = compact.get("metrics")
    if isinstance(metrics, list):
        compact["metrics_total"] = len(metrics)
        compact["metrics"] = (
            []
            if compact.get("id") in {SEARCH_TERM_NGRAM_ACTION_ID, "act_review_merchant_feed_issues"}
            else [
                _compact_metric_fact_for_context(metric)
                for metric in metrics[:1]
                if isinstance(metric, dict)
            ]
        )
        compact["metrics_included"] = len(compact["metrics"])
    preview_cards = compact.get("preview_cards")
    if isinstance(preview_cards, list):
        compact["preview_cards_total"] = len(preview_cards)
        compact["preview_cards"] = [
            _compact_preview_card_for_skill_context(card)
            for card in preview_cards[:3]
            if isinstance(card, dict)
        ]
        compact["preview_cards_included"] = len(compact["preview_cards"])
    payload = compact.get("payload")
    if isinstance(payload, dict):
        if _action_payload_should_survive_skill_context(
            str(compact.get("id") or ""),
            skill=skill,
        ):
            _compact_action_payload_for_context(
                payload,
                action_id=str(compact.get("id") or ""),
            )
            compact["action_plan"] = payload
            compact.pop("payload", None)
        else:
            compact.pop("payload", None)
    compact["api_endpoint_template"] = "/api/actions/{action_id}"
    return compact


def _action_payload_should_survive_skill_context(action_id: str, *, skill: str) -> bool:
    allowed_by_skill: dict[str, set[str]] = {
        "wilq-content-strategist": {"act_prepare_content_refresh_queue"},
        "wilq-gsc-content-doctor": {"act_prepare_content_refresh_queue"},
        "wilq-ga4-analyst": {"act_review_ga4_tracking_quality"},
        "wilq-localo-operator": {"act_review_localo_visibility_facts"},
        "wilq-ads-doctor": {
            "act_review_ads_search_term_ngrams",
            "act_prepare_ads_campaign_review_queue",
            "act_prepare_custom_segments_from_search_terms",
        },
        "wilq-custom-segments": {"act_prepare_custom_segments_from_search_terms"},
        "wilq-campaign-builder": {"act_prepare_ads_campaign_review_queue"},
        "wilq-demand-gen-operator": {"act_review_demand_gen_readiness"},
    }
    return action_id in allowed_by_skill.get(skill, set())


def _compact_action_payload_for_context(payload: dict[str, Any], *, action_id: str) -> None:
    payload.pop("source_metric_names", None)
    _compact_action_row_list_for_context(
        payload,
        "campaign_candidates",
        keep_limit=3 if action_id == "act_prepare_ads_campaign_review_queue" else 0,
    )
    for key in ("recommendations", "terms", "source_terms", "keyword_match_context"):
        _compact_action_row_list_for_context(payload, key, keep_limit=0)
    _compact_preview_list_for_context(payload, "payload_preview")
    _compact_preview_list_for_context(payload, "budget_payload_preview", limit=0)
    _compact_preview_list_for_context(payload, "custom_segment_payload_preview")
    _compact_preview_list_for_context(payload, "negative_keyword_payload_preview")
    _compact_preview_list_for_context(payload, "ngram_preview")
    _compact_content_action_payload_for_context(payload)
    _label_action_plan_for_context(payload)


def _compact_action_row_list_for_context(
    payload: dict[str, Any],
    key: str,
    *,
    keep_limit: int,
) -> None:
    value = payload.get(key)
    if not isinstance(value, list):
        return
    payload[f"{key}_total"] = len(value)
    payload[key] = value[:keep_limit]
    payload[f"{key}_included"] = len(payload[key])


def _compact_preview_list_for_context(
    payload: dict[str, Any],
    key: str,
    *,
    limit: int = 4,
) -> None:
    value = payload.get(key)
    if not isinstance(value, list):
        return
    payload[f"{key}_total"] = len(value)
    payload[key] = value[:limit]
    payload[f"{key}_included"] = len(payload[key])


def _compact_content_action_payload_for_context(payload: dict[str, Any]) -> None:
    url_contract = payload.pop("content_url_review_contract", None)
    if isinstance(url_contract, dict):
        required_fields = url_contract.get("required_fields")
        allowed_outcomes = url_contract.get("allowed_outcomes")
        payload["content_url_review_summary"] = {
            "required_fields_total": (
                len(required_fields) if isinstance(required_fields, list) else 0
            ),
            "allowed_outcomes_total": (
                len(allowed_outcomes) if isinstance(allowed_outcomes, list) else 0
            ),
            "next_step": "Sprawdź publiczny i kanoniczny URL przed pisaniem.",
        }

    content_preview = payload.get("content_brief_preview")
    if isinstance(content_preview, list):
        payload["content_brief_preview_total"] = len(content_preview)
        payload["content_brief_preview"] = _compact_content_brief_preview_for_context(
            content_preview
        )
        payload["content_brief_preview_included"] = len(payload["content_brief_preview"])

    wordpress_preview = payload.get("wordpress_draft_payload_preview")
    if isinstance(wordpress_preview, list):
        payload["wordpress_draft_payload_preview_total"] = len(wordpress_preview)
        payload["wordpress_draft_payload_preview"] = (
            _compact_wordpress_draft_payload_preview_for_context(wordpress_preview)
        )
        payload["wordpress_draft_payload_preview_included"] = len(
            payload["wordpress_draft_payload_preview"]
        )

    for key in ("content_brief_preview", "wordpress_draft_payload_preview"):
        value = payload.get(key)
        if isinstance(value, list):
            payload.setdefault(f"{key}_total", len(value))
            payload.setdefault(f"{key}_included", len(value))


ACTION_PLAN_LIST_KEY_LABELS = {
    "payload_preview": "preview_items",
    "budget_payload_preview": "budget_preview_items",
    "custom_segment_payload_preview": "custom_segment_preview_items",
    "negative_keyword_payload_preview": "negative_keyword_preview_items",
    "ngram_preview": "search_term_theme_preview_items",
    "content_brief_preview": "content_plan_items",
    "wordpress_draft_payload_preview": "wordpress_draft_preview_items",
}


def _label_action_plan_for_context(value: Any) -> None:
    if isinstance(value, dict):
        _rename_action_plan_list_keys(value)
        _label_action_plan_status_fields(value)
        for child in list(value.values()):
            _label_action_plan_for_context(child)
        return
    if isinstance(value, list):
        for item in value:
            _label_action_plan_for_context(item)


def _rename_action_plan_list_keys(value: dict[str, Any]) -> None:
    for old_key, new_key in ACTION_PLAN_LIST_KEY_LABELS.items():
        if old_key in value:
            value[new_key] = value.pop(old_key)
        total_key = f"{old_key}_total"
        if total_key in value:
            value[f"{new_key}_total"] = value.pop(total_key)
        included_key = f"{old_key}_included"
        if included_key in value:
            value[f"{new_key}_included"] = value.pop(included_key)


def _label_action_plan_status_fields(value: dict[str, Any]) -> None:
    value.pop("action_type", None)
    value.pop("connector", None)
    value.pop("mode", None)

    value.pop("operation_type", None)
    value.pop("source_metric_names", None)
    for key in list(value):
        if key.endswith("_micros"):
            value.pop(key, None)

    preview_contract_label = value.pop("preview_contract_label", None)
    if isinstance(preview_contract_label, str) and preview_contract_label:
        value.setdefault("review_type_label", preview_contract_label)
    value.pop("preview_contract", None)
    value.pop("source_preview_contract", None)

    required_validation_labels = value.pop("required_validation_labels", None)
    if isinstance(required_validation_labels, list):
        value.setdefault("required_check_labels", required_validation_labels)
    value.pop("required_validation", None)
    required_validation_total = value.pop("required_validation_total", None)
    if isinstance(required_validation_total, int):
        value.setdefault("required_checks_total", required_validation_total)

    if "blocked_claim_labels" in value:
        value.pop("blocked_claims", None)
    if "missing_read_contract_labels" in value:
        value.pop("missing_read_contracts", None)
    if "allowed_contract_labels" in value:
        value.pop("allowed_contracts", None)
    if "available_read_contract_labels" in value:
        value.pop("available_read_contracts", None)
    if "operator_review_gate_labels" in value:
        value.pop("operator_review_gates", None)
    _label_action_plan_metric_snapshot(value)

    apply_allowed = value.pop("apply_allowed", None)
    if isinstance(apply_allowed, bool):
        value.setdefault(
            "apply_status_label",
            "gotowe do potwierdzenia" if apply_allowed else "zablokowane do sprawdzenia",
        )

    api_mutation_ready = value.pop("api_mutation_ready", None)
    if isinstance(api_mutation_ready, bool):
        value.setdefault(
            "write_status_label",
            "gotowe do zapisu" if api_mutation_ready else "bez zapisu automatycznego",
        )

    destructive = value.pop("destructive", None)
    if isinstance(destructive, bool):
        value.setdefault(
            "change_risk_label",
            "zmiana destrukcyjna" if destructive else "bezpieczny podgląd",
        )


def _label_action_plan_metric_snapshot(value: dict[str, Any]) -> None:
    metric_snapshot = value.get("metric_snapshot")
    metric_snapshot_labels = value.get("metric_snapshot_labels")
    if not isinstance(metric_snapshot, dict) or not isinstance(metric_snapshot_labels, dict):
        return

    metric_tiles: dict[str, Any] = {}
    for metric_name, metric_value in metric_snapshot.items():
        metric_label = metric_snapshot_labels.get(metric_name)
        if isinstance(metric_label, str) and metric_label:
            metric_tiles[metric_label] = metric_value
    if metric_tiles:
        value["metric_tiles"] = metric_tiles
        value.pop("metric_snapshot", None)
        value.pop("metric_snapshot_labels", None)


def _compact_action_review_gate_for_context(action: dict[str, Any]) -> None:
    review_gate = action.get("review_gate")
    if not isinstance(review_gate, dict):
        return

    apply_blockers = review_gate.get("apply_blockers")
    if not isinstance(apply_blockers, list):
        apply_blockers = []
    apply_blocker_labels = review_gate.get("apply_blocker_labels")
    if not isinstance(apply_blocker_labels, list):
        apply_blocker_labels = []
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
    last_mutation_blocker_labels = review_gate.get("last_mutation_blocker_labels")
    if not isinstance(last_mutation_blocker_labels, list):
        last_mutation_blocker_labels = []

    action["review_gate"] = {
        "status": review_gate.get("status"),
        "risk": review_gate.get("risk"),
        "last_review_outcome": review_gate.get("last_review_outcome"),
        "last_reviewed_by": review_gate.get("last_reviewed_by"),
        "last_confirmation_by": review_gate.get("last_confirmation_by"),
        "last_impact_check_status": review_gate.get("last_impact_check_status"),
        "last_mutation_audit_status": review_gate.get("last_mutation_audit_status"),
        "last_mutation_attempted": review_gate.get("last_mutation_attempted"),
        "apply_allowed": review_gate.get("apply_allowed"),
        "confirmation_required": review_gate.get("confirmation_required"),
        "apply_blockers_total": len(apply_blockers),
        "apply_blocker_labels": apply_blocker_labels[:3],
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
        "last_mutation_blocker_labels": last_mutation_blocker_labels[:3],
        "last_mutation_blockers_included": min(len(last_mutation_blockers), 3),
    }


def _compact_preview_card_for_skill_context(card: dict[str, Any]) -> dict[str, Any]:
    compact = dict(card)
    compact.pop("id", None)
    rows = compact.get("rows")
    if isinstance(rows, list):
        compact["rows_total"] = len(rows)
        compact["rows"] = rows[:6]
        compact["rows_included"] = len(compact["rows"])
    return compact


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
        "metric_snapshot_labels",
        "reason",
        "required_validation",
        "blocked_claims",
        "evidence_ids",
        "api_mutation_ready",
        "apply_allowed",
        "destructive",
    }
    for item in preview_items[:3]:
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
        "preview_contract",
        "operation_type",
        "country",
        "metric_snapshot",
        "sample_products_available",
        "sample_unavailable_reason",
        "reason",
        "required_validation_labels",
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
        compact_item["issue_summary"] = _context_pack_text(item.get("reason"), limit=180)
        required_validation = compact_item.get("required_validation_labels")
        if isinstance(required_validation, list):
            compact_item["required_validation_total"] = len(required_validation)
            compact_item["required_validation_labels"] = required_validation[:4]
        blocked_claims = compact_item.get("blocked_claims")
        if isinstance(blocked_claims, list):
            compact_item["blocked_claims"] = blocked_claims[:5]
        evidence_ids = compact_item.get("evidence_ids")
        if isinstance(evidence_ids, list):
            compact_item["evidence_ids"] = evidence_ids[:3]
        compact_items.append(compact_item)
    return compact_items


def _compact_merchant_price_impact_preview_for_context(
    preview: dict[str, Any],
) -> dict[str, Any]:
    compact = {
        "preview_contract": preview.get("preview_contract"),
        "preview_contract_label": preview.get("preview_contract_label"),
        "reason": _context_pack_text(preview.get("reason"), limit=180),
        "api_mutation_ready": preview.get("api_mutation_ready"),
        "apply_allowed": preview.get("apply_allowed"),
        "destructive": preview.get("destructive"),
    }
    products = preview.get("products")
    compact["products_total"] = len(products) if isinstance(products, list) else 0
    missing_read_contracts = preview.get("missing_read_contracts")
    if isinstance(missing_read_contracts, list):
        compact["missing_read_contracts_total"] = len(missing_read_contracts)
    required_validation = preview.get("required_validation_labels")
    if isinstance(required_validation, list):
        compact["required_validation_total"] = len(required_validation)
        compact["required_validation_labels"] = required_validation[:4]
    blocked_claims = preview.get("blocked_claims")
    if isinstance(blocked_claims, list):
        compact["blocked_claims"] = blocked_claims[:5]
    evidence_ids = preview.get("evidence_ids")
    if isinstance(evidence_ids, list):
        compact["evidence_ids"] = evidence_ids[:3]
    return compact


def _compact_content_brief_preview_for_context(
    preview_items: list[Any],
) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "candidate_id",
        "source_type",
        "source_type_label",
        "mode",
        "mode_label",
        "topic",
        "source_public_url",
        "preview_url",
        "intended_final_url",
        "final_canonical_url",
        "inventory_gate_status",
        "canonical_gate_status",
        "duplicate_gate_status",
        "content_gate_summary",
        "competitor_domain",
        "wordpress_inventory_match",
        "gsc_demand",
        "metric_snapshot",
        "metric_snapshot_labels",
        "brief_goal",
        "intent",
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
        "publication_readiness_status_label",
        "publication_blockers",
        "publication_blocker_labels",
        "source_facts",
        "missing_evidence",
        "forbidden_claims",
        "decision_option_labels",
        "required_validation",
        "required_validation_labels",
        "blocked_claims",
        "blocked_claim_labels",
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
                ("required_validation", 4),
                ("blocked_claims", 5),
                ("source_connectors", 4),
                ("evidence_ids", 3),
            ):
                value = compact_item.get(key)
                if isinstance(value, list):
                    values = value[:limit]
                    if key == "source_facts":
                        values = _compact_content_source_facts_for_context(values)
                    compact_item[key] = values
                    compact_item[f"{key}_total"] = len(value)
            compact_items.append(compact_item)
    return compact_items


def _compact_content_source_facts_for_context(values: list[Any]) -> list[Any]:
    compact_values: list[Any] = []
    for value in values:
        if isinstance(value, str) and value.startswith("Strona z GSC:"):
            compact_values.append("Strona z GSC: publiczny adres strony")
        else:
            compact_values.append(value)
    return compact_values


def _compact_wordpress_draft_payload_preview_for_context(
    preview_items: list[Any],
) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "preview_contract",
        "source_preview_contract",
        "candidate_id",
        "source_type",
        "source_type_label",
        "mode",
        "mode_label",
        "operation_type",
        "operation_type_label",
        "post_status",
        "post_status_label",
        "topic",
        "intent",
        "source_public_url",
        "preview_url",
        "intended_final_url",
        "final_canonical_url",
        "inventory_gate_status",
        "inventory_gate_status_label",
        "canonical_gate_status",
        "canonical_gate_status_label",
        "duplicate_gate_status",
        "duplicate_gate_status_label",
        "content_gate_summary",
        "draft_generation_status",
        "draft_generation_status_label",
        "draft_blockers",
        "draft_blocker_labels",
        "draft_generation_summary",
        "draft_generation_contract",
        "draft_readiness_review_contract",
        "draft_readiness_review_contract_summary",
        "draft_readiness_review_recorded_outcome",
        "draft_readiness_review_summary",
        "canonical_review_recorded_outcome",
        "duplicate_review_recorded_outcome",
        "legal_factual_review_recorded_outcome",
        "human_review_recorded_outcome",
        "wordpress_draft_handoff_status",
        "wordpress_draft_handoff_blockers",
        "wordpress_draft_handoff_blocker_labels",
        "wordpress_draft_handoff_summary",
        "wordpress_draft_handoff_contract",
        "wordpress_draft_handoff_contract_summary",
        "post_publication_measurement_plan",
        "post_publication_measurement_summary",
        "required_validation",
        "required_validation_labels",
        "blocked_claims",
        "blocked_claim_labels",
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
        draft_generation_contract = compact_item.get("draft_generation_contract")
        if isinstance(draft_generation_contract, dict):
            for key, limit in (
                ("blocked_until", 6),
                ("requires_passed_gates", 7),
                ("output_must_include", 10),
                ("forbidden_outputs", 6),
            ):
                value = draft_generation_contract.get(key)
                if isinstance(value, list):
                    draft_generation_contract[key] = value[:limit]
                    draft_generation_contract[f"{key}_total"] = len(value)
        draft_readiness_contract = compact_item.get("draft_readiness_review_contract")
        if isinstance(draft_readiness_contract, dict):
            for key, limit in (
                ("allowed_outcomes", 5),
                ("required_fields", 7),
                ("blocked_outputs", 6),
            ):
                value = draft_readiness_contract.get(key)
                if isinstance(value, list):
                    draft_readiness_contract[key] = value[:limit]
                    draft_readiness_contract[f"{key}_total"] = len(value)
        wordpress_draft_handoff_contract = compact_item.get("wordpress_draft_handoff_contract")
        if isinstance(wordpress_draft_handoff_contract, dict):
            for key, limit in (
                ("blocked_until", 7),
                ("requires_passed_gates", 7),
                ("blocked_outputs", 5),
            ):
                value = wordpress_draft_handoff_contract.get(key)
                if isinstance(value, list):
                    wordpress_draft_handoff_contract[key] = value[:limit]
                    wordpress_draft_handoff_contract[f"{key}_total"] = len(value)
        _compact_post_publication_measurement_plan(compact_item)
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
                compact_item["draft_payload"]["content_blocks_total"] = len(content_blocks)
                compact_item["draft_payload"]["content_blocks"] = [
                    block for block in content_blocks[:4] if isinstance(block, dict)
                ]
                compact_item["draft_payload"]["content_blocks_included"] = len(
                    compact_item["draft_payload"]["content_blocks"]
                )
        compact_items.append(compact_item)
    return compact_items


def _compact_wordpress_draft_handoff_preview_for_context(
    preview_items: list[Any],
) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "preview_contract",
        "operation_type",
        "candidate_id",
        "topic",
        "source_public_url",
        "preview_url",
        "intended_final_url",
        "final_canonical_url",
        "canonical_gate_status",
        "duplicate_gate_status",
        "wordpress_draft_handoff_status",
        "required_next_action_contract",
        "post_publication_measurement_plan",
        "required_validation",
        "blocked_claims",
        "apply_allowed",
        "api_mutation_ready",
        "destructive",
    }
    for item in preview_items[:4]:
        if not isinstance(item, dict):
            continue
        compact_item = {key: item[key] for key in keep_keys if key in item}
        for key, limit in (
            ("required_validation", 6),
            ("blocked_claims", 5),
        ):
            value = compact_item.get(key)
            if isinstance(value, list):
                compact_item[key] = value[:limit]
                compact_item[f"{key}_total"] = len(value)
        _compact_post_publication_measurement_plan(compact_item)
        compact_items.append(compact_item)
    return compact_items


def _compact_post_publication_measurement_plan(item: dict[str, Any]) -> None:
    measurement_plan = item.get("post_publication_measurement_plan")
    if not isinstance(measurement_plan, dict):
        return
    keep_keys = {
        "contract_version",
        "scope",
        "final_canonical_url",
        "status",
        "baseline_window",
        "followup_windows",
        "required_source_connectors",
        "required_metric_groups",
        "requires_before_claims",
        "blocked_outputs",
    }
    compact_plan = {key: measurement_plan[key] for key in keep_keys if key in measurement_plan}
    for key, limit in (
        ("followup_windows", 3),
        ("required_source_connectors", 3),
        ("required_metric_groups", 3),
        ("requires_before_claims", 5),
        ("blocked_outputs", 5),
    ):
        value = compact_plan.get(key)
        if isinstance(value, list):
            compact_plan[key] = value[:limit]
            compact_plan[f"{key}_total"] = len(value)
    item["post_publication_measurement_plan"] = compact_plan


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


def _drop_recommendation_row_nested_payload_preview_for_context(data: dict[str, Any]) -> None:
    contract = data.get("recommendations_read_contract")
    if not isinstance(contract, dict):
        return
    rows = contract.get("recommendation_rows")
    if not isinstance(rows, list):
        return
    for row in rows:
        if not isinstance(row, dict):
            continue
        payload_preview = row.pop("payload_preview", None)
        if isinstance(payload_preview, list):
            row["payload_preview_total"] = len(payload_preview)
        elif isinstance(payload_preview, dict):
            row["payload_preview_total"] = 1
        else:
            row["payload_preview_total"] = 0
        row["payload_preview_included"] = 0


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


def _compact_negative_keyword_candidate_context_rows_for_context(data: dict[str, Any]) -> None:
    candidates = _list_at(data, "negative_keywords_read_contract", "candidates")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        rows = candidate.get("keyword_context_rows")
        if not isinstance(rows, list):
            continue
        candidate["keyword_context_rows_total"] = len(rows)
        compact_rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            compact_rows.append(
                {
                    "keyword_text": row.get("keyword_text"),
                    "match_type": row.get("match_type"),
                    "criterion_status": row.get("criterion_status"),
                    "negative": row.get("negative"),
                    "evidence_ids": row.get("evidence_ids") or [],
                }
            )
        candidate["keyword_context_rows"] = compact_rows
        candidate["keyword_context_rows_included"] = len(compact_rows)


def _compact_custom_segment_candidate_search_term_rows_for_context(data: dict[str, Any]) -> None:
    candidates = _list_at(data, "custom_segments_read_contract", "candidates")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        rows = candidate.get("search_term_rows")
        if not isinstance(rows, list):
            continue
        candidate["search_term_rows_total"] = len(rows)
        compact_rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            compact_rows.append(
                {
                    "search_term": row.get("search_term"),
                    "clicks": row.get("clicks"),
                    "cost_micros": row.get("cost_micros"),
                    "conversions": row.get("conversions"),
                    "evidence_ids": row.get("evidence_ids") or [],
                    "missing_metrics": row.get("missing_metrics") or [],
                }
            )
        candidate["search_term_rows"] = compact_rows
        candidate["search_term_rows_included"] = len(compact_rows)


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
    compact_item["targeting_preview"] = _compact_custom_segment_targeting_preview_for_context(
        item.get("targeting_preview")
    )
    safety_review = item.get("safety_review")
    if isinstance(safety_review, dict):
        compact_item["safety_review"] = _compact_custom_segment_safety_review_item(safety_review)
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


def _drop_empty_decision_row_lists_for_context(data: dict[str, Any]) -> None:
    row_keys = (
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
    )
    for decision in _list_at(data, "decision_queue"):
        if not isinstance(decision, dict):
            continue
        omitted_count = 0
        for rows_key in row_keys:
            rows = decision.get(rows_key)
            if rows == []:
                decision.pop(rows_key, None)
                omitted_count += 1
        if omitted_count:
            decision["omitted_empty_row_lists_count"] = omitted_count


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
        if opportunity.action_ids and set(opportunity.action_ids).issubset(allowed_action_ids)
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


@app.get("/api/content/preflight", response_model=ContentPreflightResponse)
def content_preflight() -> ContentPreflightResponse:
    return build_content_preflight()


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
    return [_label_evidence_item(item) for item in list_evidence()]


@app.get("/api/evidence/{evidence_id}", response_model=Evidence)
def evidence_detail(evidence_id: str) -> Evidence:
    evidence = get_evidence(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail=f"Unknown evidence: {evidence_id}")
    return _label_evidence_item(evidence)


def _label_evidence_item(evidence: Evidence) -> Evidence:
    source_label = source_connector_label(evidence.source_connector)
    source_type_label = evidence_source_type_label(evidence.source_type)
    freshness_label = freshness_state_label(evidence.freshness.state)
    return evidence.model_copy(
        update={
            "title_label": f"Dowód z {source_label}",
            "source_connector_label": source_label,
            "source_type_label": source_type_label,
            "freshness_label": freshness_label,
            "trace_summary_label": f"{source_label}: {source_type_label}, {freshness_label}",
        }
    )


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
    return result.model_dump(mode="json", exclude_none=True)


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
