from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from wilq.schemas import DemandGenReadinessContract


def create_demand_gen_router(
    build_readiness_contract: Callable[[], DemandGenReadinessContract],
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/demand-gen/diagnostics", response_model=DemandGenReadinessContract)
    def demand_gen_diagnostics() -> DemandGenReadinessContract:
        return build_readiness_contract()

    return router
