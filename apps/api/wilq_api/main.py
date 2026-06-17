from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from wilq.access_pack.manifest import access_pack_status
from wilq.actions.service import apply_action, get_action, list_actions, validate_action
from wilq.codex.runtime_status import codex_runtime_status
from wilq.connectors.registry import get_connector_status, list_connector_statuses
from wilq.expert.rules import (
    get_expert_rule,
    list_expert_capabilities,
    list_expert_rule_summaries,
    list_expert_rules,
)
from wilq.knowledge.cards import seed_cards
from wilq.opportunities.engine import OPPORTUNITY_TYPES, get_opportunity, list_opportunities
from wilq.schemas import (
    CodexRun,
    CommandCenterResponse,
    ConnectorStatus,
    ConnectorSummary,
    ExpertCapability,
    ExpertRule,
    ExpertRuleSummary,
    Opportunity,
    utc_now,
)
from wilq.security.redaction import redact_mapping
from wilq.workflows.registry import list_workflows

app = FastAPI(title="WILQ Marketing API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

CODEX_RUNS: list[CodexRun] = []

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
        "active_action_objects": [action.model_dump(mode="json") for action in list_actions()],
        "knowledge_card_summaries": [card.model_dump(mode="json") for card in seed_cards()],
        "expert_rule_summaries": [
            rule.model_dump(mode="json") for rule in list_expert_rule_summaries(limit=12)
        ],
        "expert_capabilities": [
            capability.model_dump(mode="json") for capability in list_expert_capabilities()
        ],
        "strict_instruction": "Codex must not invent metrics; fetch WILQ API evidence first.",
    }
    return redact_mapping(pack)


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
            "access_pack": access_pack_status(detailed=False),
            "codex_runtime": codex_runtime_status(),
            "opportunity_types": list(OPPORTUNITY_TYPES),
        }
    )


@app.get("/api/connectors", response_model=list[ConnectorStatus])
def connectors() -> list[ConnectorStatus]:
    return list_connector_statuses()


@app.get("/api/connectors/{connector}/status", response_model=ConnectorStatus)
def connector_status_endpoint(connector: str) -> ConnectorStatus:
    status = get_connector_status(connector)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Unknown connector: {connector}")
    return status


@app.post("/api/connectors/{connector}/refresh", response_model=ConnectorStatus)
def connector_refresh(connector: str) -> ConnectorStatus:
    status = get_connector_status(connector)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Unknown connector: {connector}")
    return status


@app.get("/api/dashboard/command-center", response_model=CommandCenterResponse)
def command_center() -> CommandCenterResponse:
    connectors = list_connector_statuses()
    opportunities = list_opportunities()
    return CommandCenterResponse(
        strict_instruction="No WILQ API evidence means no marketing recommendation.",
        connector_summary=connector_summary(connectors),
        sections={
            "todays_moves": opportunities[:2],
            "money_leaks": [item for item in opportunities if item.domain.value == "google_ads"],
            "traffic_wins": [
                item for item in opportunities if item.domain.value in {"gsc_seo", "ga4"}
            ],
            "content_to_rewrite": [],
            "content_to_create": [],
            "local_visibility_moves": [
                item for item in opportunities if item.domain.value == "localo"
            ],
            "social_queue": [item for item in opportunities if item.domain.value == "social"],
            "codex_operator_status": [],
            "connector_health": [],
        },
        active_actions=list_actions(),
        connector_health=connectors,
        codex_operator_status=codex_runtime_status(),
    )


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
def apply_action_endpoint(action_id: str) -> dict[str, Any]:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")
    result = apply_action(action)
    if not result.applied:
        raise HTTPException(status_code=409, detail=result.model_dump(mode="json"))
    return result.model_dump(mode="json")


@app.get("/api/knowledge/cards")
def knowledge_cards() -> list[dict[str, Any]]:
    return [card.model_dump(mode="json") for card in seed_cards()]


@app.get("/api/knowledge/search")
def knowledge_search(q: str = "") -> list[dict[str, Any]]:
    query = q.lower()
    cards = seed_cards()
    if query:
        cards = [
            card for card in cards if query in card.title.lower() or query in card.summary.lower()
        ]
    return [card.model_dump(mode="json") for card in cards]


@app.post("/api/knowledge/condense")
def knowledge_condense() -> dict[str, Any]:
    return {"status": "queued", "rule": "Condense source material into cards before Codex context."}


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
    redacted = CodexRun.model_validate(redact_mapping(run.model_dump(mode="json")))
    CODEX_RUNS.append(redacted)
    return redacted


@app.get("/api/codex/runs", response_model=list[CodexRun])
def codex_runs() -> list[CodexRun]:
    return CODEX_RUNS


@app.get("/api/workflows")
def workflows() -> list[dict[str, Any]]:
    return [workflow.model_dump(mode="json") for workflow in list_workflows()]
