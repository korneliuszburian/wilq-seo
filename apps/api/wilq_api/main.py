from __future__ import annotations

import asyncio
import ipaddress
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
    build_daily_check_runtime,
    build_daily_marketing_brief,
    clear_daily_runtime_cache,
    finish_daily_check_prewarm,
    start_daily_check_prewarm,
)
from wilq.briefing.ga4_diagnostics import (
    build_ga4_diagnostics_cached,
    clear_ga4_diagnostics_cache,
)
from wilq.briefing.merchant_diagnostics import (
    build_merchant_diagnostics_cached,
    clear_merchant_diagnostics_cache,
)
from wilq.briefing.tactical_queue import clear_tactical_queue_cache
from wilq.connectors.registry import list_connector_statuses
from wilq.content.workflow.catalog import build_content_inventory_catalog_cached
from wilq.knowledge.operating_map import (
    build_knowledge_operating_map_cached,
    clear_knowledge_operating_map_cache,
)
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
    knowledge_prewarm_task: asyncio.Task[None] | None = None
    daily_runtime_prewarm_task: asyncio.Task[None] | None = None
    inventory_catalog_prewarm_task: asyncio.Task[None] | None = None
    if not os.getenv("PYTEST_CURRENT_TEST"):
        with suppress(Exception):
            build_content_diagnostics_cached()
        with suppress(Exception):
            build_merchant_diagnostics_cached()
        with suppress(Exception):
            list_actions_cached()
        knowledge_prewarm_task = asyncio.create_task(_prewarm_knowledge_map())
        inventory_catalog_prewarm_task = asyncio.create_task(
            _prewarm_inventory_catalog()
        )
        start_daily_check_prewarm()
        daily_runtime_prewarm_task = asyncio.create_task(_prewarm_daily_runtime())
    try:
        yield
    finally:
        if knowledge_prewarm_task is not None:
            with suppress(Exception):
                await knowledge_prewarm_task
        if daily_runtime_prewarm_task is not None:
            with suppress(Exception):
                await daily_runtime_prewarm_task
        if inventory_catalog_prewarm_task is not None:
            with suppress(Exception):
                await inventory_catalog_prewarm_task


async def _prewarm_knowledge_map() -> None:
    """Warm the expensive map after readiness without delaying API startup."""
    with suppress(Exception):
        await asyncio.to_thread(build_knowledge_operating_map_cached)


async def _prewarm_inventory_catalog() -> None:
    """Warm the selected-page index without delaying API readiness."""
    with suppress(Exception):
        await asyncio.to_thread(build_content_inventory_catalog_cached)


async def _prewarm_daily_runtime() -> None:
    """Warm the daily operator view after readiness without blocking startup."""
    try:
        with suppress(Exception):
            await asyncio.to_thread(build_daily_check_runtime)
        with suppress(Exception):
            await asyncio.to_thread(build_daily_marketing_brief)
        with suppress(Exception):
            await asyncio.to_thread(build_ga4_diagnostics_cached)
    finally:
        finish_daily_check_prewarm()


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

ASGI_TEST_PEERS = {"testclient", "testserver"}

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
    peer_host = request.client.host if request.client is not None else None
    if not _is_loopback_peer(peer_host):
        return JSONResponse(
            status_code=403,
            content={
                "detail": "WILQ API przyjmuje połączenia wyłącznie z interfejsu loopback."
            },
        )
    return await call_next(request)


def _is_loopback_peer(peer_host: str | None) -> bool:
    if peer_host in ASGI_TEST_PEERS:
        return True
    if peer_host is None:
        return False
    try:
        address = ipaddress.ip_address(peer_host)
    except ValueError:
        return False
    if address.is_loopback:
        return True
    if isinstance(address, ipaddress.IPv6Address):
        return bool(address.ipv4_mapped and address.ipv4_mapped.is_loopback)
    return False


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
    clear_knowledge_operating_map_cache()
    clear_daily_runtime_cache()
    clear_ga4_diagnostics_cache()
    clear_skill_context_cache()


app.include_router(create_actions_router(clear_api_view_model_caches))
app.include_router(create_connectors_router(clear_api_view_model_caches))
app.include_router(create_jobs_router(clear_api_view_model_caches))
app.include_router(create_codex_router(context_pack))
app.include_router(create_demand_gen_router(context_demand_gen.build_readiness_contract))
