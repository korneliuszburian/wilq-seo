from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from wilq.actions.service import apply_action, get_action, list_actions, validate_action
from wilq.briefing.ads_diagnostics import build_ads_diagnostics
from wilq.briefing.command_center import (
    build_command_center_action_plan,
    build_command_center_brief,
    build_daily_decisions,
)
from wilq.briefing.content_diagnostics import build_content_diagnostics
from wilq.briefing.ga4_diagnostics import build_ga4_diagnostics
from wilq.briefing.marketing_brief import build_marketing_brief, core_brief_actions
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
from wilq.evidence.registry import get_evidence, list_evidence
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
from wilq.opportunities.engine import OPPORTUNITY_TYPES, get_opportunity, list_opportunities
from wilq.schemas import (
    ActionApplyRequest,
    ActionObject,
    AdsDiagnosticsResponse,
    AuditEvent,
    CodexRun,
    CommandCenterResponse,
    ConnectorRefreshRequest,
    ConnectorRefreshRun,
    ConnectorStatus,
    ConnectorSummary,
    ContentDiagnosticsResponse,
    Evidence,
    ExpertCapability,
    ExpertRule,
    ExpertRuleSummary,
    Ga4DiagnosticsResponse,
    KnowledgeCard,
    KnowledgeCompilerResult,
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


def cors_origins() -> list[str]:
    configured = os.getenv("WILQ_CORS_ORIGINS")
    if not configured:
        return list(DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app = FastAPI(title="WILQ Marketing API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "testclient", "testserver"}


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
    connectors = list_connector_statuses()
    opportunities = list_opportunities()
    max_opportunities = request.max_opportunities if request else 5
    skill = request.skill if request else None
    if request and skill and skill != "wilq-daily-command" and not request.full_context:
        return _skill_scoped_context_pack(request, connectors, opportunities)
    active_actions = _full_context_actions_for_skill(skill)
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
        "command_center": command_center().model_dump(mode="json"),
        "marketing_brief": build_marketing_brief().model_dump(mode="json"),
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


SKILL_CONNECTOR_SCOPES: dict[str, set[str]] = {
    "wilq-ads-doctor": {"google_ads"},
    "wilq-ahrefs-gap-finder": {"ahrefs", "google_search_console", "wordpress_ekologus"},
    "wilq-campaign-builder": {
        "google_ads",
        "google_analytics_4",
        "google_search_console",
        "google_merchant_center",
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
        "google_merchant_center",
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
    "wilq-ads-doctor": {"ads", "google_ads", "negative", "search", "pmax"},
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


def _skill_scoped_context_pack(
    request: ContextPackRequest,
    connectors: list[ConnectorStatus],
    opportunities: list[Opportunity],
) -> dict[str, Any]:
    skill = request.skill or "unknown"
    scoped_connectors = SKILL_CONNECTOR_SCOPES.get(skill, set())
    if not scoped_connectors:
        scoped_connectors = {connector.id for connector in connectors if connector.configured}
    max_opportunities = request.max_opportunities

    actions = list_actions()
    diagnostics = _diagnostics_for_skill(skill)
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
            action.model_dump(mode="json") for action in scoped_actions
        ],
        "connector_refresh_runs": [
            run.model_dump(mode="json")
            for run in list_connector_refresh_runs()[:25]
            if run.connector_id in scoped_connectors
        ][:10],
        "evidence_summaries": [
            evidence.model_dump(mode="json")
            for evidence in list_evidence()
            if evidence.id in evidence_ids or evidence.source_connector in scoped_connectors
        ][:80],
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
    return redact_mapping(pack)


def _diagnostics_for_skill(skill: str) -> dict[str, Any]:
    if skill in {"wilq-content-strategist", "wilq-gsc-content-doctor"}:
        return {"content_diagnostics": build_content_diagnostics().model_dump(mode="json")}
    if skill == "wilq-ads-doctor":
        return {"ads_diagnostics": build_ads_diagnostics().model_dump(mode="json")}
    if skill == "wilq-merchant-feed-operator":
        return {"merchant_diagnostics": build_merchant_diagnostics().model_dump(mode="json")}
    if skill == "wilq-ga4-analyst":
        return {"ga4_diagnostics": build_ga4_diagnostics().model_dump(mode="json")}
    if skill == "wilq-demand-gen-operator":
        return {
            "ads_diagnostics": build_ads_diagnostics().model_dump(mode="json"),
            "ga4_diagnostics": build_ga4_diagnostics().model_dump(mode="json"),
            "merchant_diagnostics": build_merchant_diagnostics().model_dump(mode="json"),
        }
    if skill in {"wilq-campaign-builder", "wilq-custom-segments"}:
        return {
            "ads_diagnostics": build_ads_diagnostics().model_dump(mode="json"),
            "content_diagnostics": build_content_diagnostics().model_dump(mode="json"),
        }
    if skill == "wilq-social-publisher":
        return {
            "marketing_brief": build_marketing_brief().model_dump(mode="json"),
            "tactical_queue": build_tactical_queue().model_dump(mode="json"),
        }
    return {"marketing_brief": build_marketing_brief().model_dump(mode="json")}


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
    keywords = SKILL_KEYWORD_SCOPES.get(skill, set())
    return [
        card
        for card in compile_playbook_cards()
        if _text_matches_scope(
            [card.id, card.card_type, card.title, card.summary, card.source_id],
            keywords,
        )
    ][:8]


def _expert_rules_for_skill(skill: str) -> list[ExpertRuleSummary]:
    keywords = SKILL_KEYWORD_SCOPES.get(skill, set())
    return [
        rule
        for rule in list_expert_rule_summaries(limit=50)
        if _text_matches_scope(
            [
                rule.id,
                rule.name,
                rule.domain,
                rule.source_anchor,
                rule.output_contract,
            ],
            keywords,
        )
    ][:8]


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
    return run


@app.get("/api/dashboard/command-center", response_model=CommandCenterResponse)
def command_center() -> CommandCenterResponse:
    connectors = list_connector_statuses()
    operator_brief, primary_next_step, blocker_count = build_command_center_brief()
    tactical_queue = build_tactical_queue()
    action_plan = build_command_center_action_plan(operator_brief, tactical_queue.items)
    return CommandCenterResponse(
        strict_instruction=(
            "WILQ pokazuje tylko metryki z API/evidence. Brak danych oznacza blocker, "
            "nie domysł marketingowy."
        ),
        primary_next_step=primary_next_step,
        blocker_count=blocker_count,
        tactical_item_count=len(tactical_queue.items),
        daily_decisions=build_daily_decisions(action_plan),
        operator_brief=operator_brief,
        demo_script=[],
        action_plan=action_plan,
        connector_summary=connector_summary(connectors),
        sections={},
        active_actions=[],
        connector_health=connectors,
        codex_operator_status=codex_runtime_status(),
    )


@app.get("/api/marketing/brief", response_model=MarketingBrief)
def marketing_brief() -> MarketingBrief:
    return build_marketing_brief()


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
    return validate_action(action).model_dump(mode="json")


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
