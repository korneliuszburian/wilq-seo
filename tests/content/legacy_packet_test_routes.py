"""Test-only v1 planning writer; remove when v2 packet tests supersede history."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI

from apps.api.wilq_api.routers.content_planning_proposals import (
    _generate_content_work_item_planning_proposal,
)
from tests.content.legacy_route_insertion import insert_legacy_test_post
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalRequest


def register_legacy_packet_fixture_route(
    router: APIRouter,
    snapshot_loader: Callable[[str], Any],
    refresh_authority_factory: Callable[[], Any],
) -> None:
    """Seed historical end-to-end tests without reopening the product POST."""

    @router.post("/api/content/work-items/{work_item_id}/planning-proposals")
    def legacy_packet_fixture(work_item_id: str, request: ContentPlanningProposalRequest) -> Any:
        return _generate_content_work_item_planning_proposal(
            work_item_id=work_item_id,
            request=request,
            snapshot_loader=snapshot_loader,
            refresh_authority=refresh_authority_factory(),
        )


def register_legacy_packet_fixture_route_before_production(
    app: FastAPI,
    *,
    monkeypatch: pytest.MonkeyPatch,
    snapshot_loader: Callable[[str], Any],
    refresh_authority_factory: Callable[[], Any],
) -> None:
    router = APIRouter()
    register_legacy_packet_fixture_route(router, snapshot_loader, refresh_authority_factory)
    insert_legacy_test_post(
        app,
        router.routes[0],
        path="/api/content/work-items/{work_item_id}/planning-proposals",
        monkeypatch=monkeypatch,
    )
