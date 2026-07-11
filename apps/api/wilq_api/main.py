from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.wilq_api import (
    context_daily,
    context_demand_gen,
    context_full,
    context_skill,
)
from apps.api.wilq_api.context_cache import (
    clear_skill_context_cache,
    request_skill,
)
from apps.api.wilq_api.context_models import ContextPackRequest
from apps.api.wilq_api.routers.actions import create_actions_router
from apps.api.wilq_api.routers.codex import create_codex_router
from apps.api.wilq_api.routers.connectors import create_connectors_router
from apps.api.wilq_api.routers.content_workflow import router as content_workflow_router
from apps.api.wilq_api.routers.demand_gen import create_demand_gen_router
from apps.api.wilq_api.routers.diagnostics import router as diagnostics_router
from apps.api.wilq_api.routers.evidence import router as evidence_router
from apps.api.wilq_api.routers.expert import router as expert_router
from apps.api.wilq_api.routers.jobs import create_jobs_router
from apps.api.wilq_api.routers.knowledge import router as knowledge_router
from apps.api.wilq_api.routers.metrics import router as metrics_router
from apps.api.wilq_api.routers.opportunities import router as opportunities_router
from apps.api.wilq_api.routers.social import router as social_router
from apps.api.wilq_api.routers.system import router as system_router
from apps.api.wilq_api.routers.workflows import router as workflows_router
from wilq.actions.service import clear_action_list_cache, list_actions_cached
from wilq.briefing.ads_diagnostics import (
    clear_ads_summary_cache,
)
from wilq.briefing.content_diagnostics import (
    build_content_diagnostics_cached,
    clear_content_diagnostics_cache,
)
from wilq.briefing.daily_runtime import (
    clear_daily_runtime_cache,
)
from wilq.briefing.merchant_diagnostics import (
    build_merchant_diagnostics_cached,
    clear_merchant_diagnostics_cache,
)
from wilq.briefing.tactical_queue import clear_tactical_queue_cache
from wilq.connectors.registry import list_connector_statuses
from wilq.opportunities.engine import list_opportunities

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




@asynccontextmanager
async def wilq_lifespan(_: FastAPI) -> AsyncIterator[None]:
    if not os.getenv("PYTEST_CURRENT_TEST"):
        with suppress(Exception):
            build_content_diagnostics_cached()
        with suppress(Exception):
            build_merchant_diagnostics_cached()
        with suppress(Exception):
            list_actions_cached()
    yield


app = FastAPI(title="WILQ Marketing API", version="0.1.0", lifespan=wilq_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_origin_regex=LOCAL_CORS_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(diagnostics_router)
app.include_router(content_workflow_router)
app.include_router(evidence_router)
app.include_router(expert_router)
app.include_router(knowledge_router)
app.include_router(metrics_router)
app.include_router(opportunities_router)
app.include_router(social_router)
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
        return context_daily.daily_command_context_pack(
            request,
            list_opportunities(),
            product_rules=CONTEXT_PRODUCT_RULES,
            strict_instruction=CONTEXT_STRICT_INSTRUCTION,
        )
    connectors = list_connector_statuses()
    opportunities = list_opportunities()
    max_opportunities = request.max_opportunities if request else 5
    if request and skill and skill != "wilq-daily-command" and not request.full_context:
        return context_skill.skill_scoped_context_pack(
            request,
            connectors,
            opportunities,
            product_rules=CONTEXT_PRODUCT_RULES,
            strict_instruction=CONTEXT_STRICT_INSTRUCTION,
        )
    return context_full.full_context_pack(
        skill=skill,
        connectors=connectors,
        opportunities=opportunities,
        max_opportunities=max_opportunities,
        product_rules=CONTEXT_PRODUCT_RULES,
        strict_instruction=CONTEXT_STRICT_INSTRUCTION,
    )


def clear_api_view_model_caches() -> None:
    clear_tactical_queue_cache()
    clear_content_diagnostics_cache()
    clear_merchant_diagnostics_cache()
    clear_action_list_cache()
    clear_ads_summary_cache()
    clear_daily_runtime_cache()
    clear_skill_context_cache()


app.include_router(create_actions_router(clear_api_view_model_caches))
app.include_router(create_connectors_router(clear_api_view_model_caches))
app.include_router(create_jobs_router(clear_api_view_model_caches))
app.include_router(create_codex_router(context_pack))
app.include_router(create_demand_gen_router(context_demand_gen.build_readiness_contract))
