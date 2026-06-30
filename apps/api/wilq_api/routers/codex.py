from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter

from apps.api.wilq_api.context_models import ContextPackRequest
from wilq.schemas import CodexRun
from wilq.storage.local_state import local_state_store


def create_codex_router(
    build_context_pack: Callable[[ContextPackRequest | None], dict[str, Any]],
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/codex/context")
    def codex_context() -> dict[str, Any]:
        return build_context_pack(None)

    @router.post("/api/codex/context-pack")
    def codex_context_pack(request: ContextPackRequest) -> dict[str, Any]:
        return build_context_pack(request)

    @router.post("/api/codex/runs", response_model=CodexRun)
    def create_codex_run(run: CodexRun) -> CodexRun:
        return local_state_store().save_codex_run(run)

    @router.get("/api/codex/runs", response_model=list[CodexRun])
    def codex_runs() -> list[CodexRun]:
        return local_state_store().list_codex_runs()

    return router
