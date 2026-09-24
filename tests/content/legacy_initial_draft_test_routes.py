"""Test adapter; remove when v2 draft ActionObject integration replaces legacy POST proofs."""

from __future__ import annotations

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

import apps.api.wilq_api.routers.content_initial_draft as initial_draft_router
from tests.content.legacy_route_insertion import insert_legacy_test_post
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftConflictResponse,
    ContentWorkItemInitialDraftRequest,
    ContentWorkItemInitialDraftResponse,
)


def register_legacy_initial_draft_test_route(
    router: APIRouter,
    *,
    snapshot_loader: initial_draft_router.ContentInitialDraftSnapshotLoader,
    authority_resolver: initial_draft_router.ContentInitialDraftAuthorityResolver | None = None,
    refresh_authority_factory: (
        initial_draft_router.ContentRefreshPreparationAuthorityFactory | None
    ) = None,
) -> None:
    """Register the historical POST behavior before the production gate route."""

    @router.post(
        "/api/content/work-items/{work_item_id}/initial-draft",
        response_model=ContentWorkItemInitialDraftResponse,
        responses={409: {"model": ContentInitialDraftConflictResponse}},
    )
    def legacy_initial_draft_test_post(
        work_item_id: str,
        request: ContentWorkItemInitialDraftRequest,
    ) -> ContentWorkItemInitialDraftResponse | JSONResponse:
        result = initial_draft_router._submit_initial_draft(
            work_item_id,
            request,
            snapshot_loader,
            authority_resolver=authority_resolver,
            refresh_authority_factory=refresh_authority_factory,
        )
        if isinstance(result, JSONResponse):
            return result
        return initial_draft_router._content_work_item_initial_draft_response(result)


def register_legacy_initial_draft_test_route_before_production(
    app: FastAPI,
    *,
    monkeypatch: pytest.MonkeyPatch,
    snapshot_loader: initial_draft_router.ContentInitialDraftSnapshotLoader,
    authority_resolver: initial_draft_router.ContentInitialDraftAuthorityResolver | None = None,
    refresh_authority_factory: (
        initial_draft_router.ContentRefreshPreparationAuthorityFactory | None
    ) = None,
) -> None:
    """Temporarily insert the opt-in test POST before the production gate route."""

    router = APIRouter()
    register_legacy_initial_draft_test_route(
        router,
        snapshot_loader=snapshot_loader,
        authority_resolver=authority_resolver,
        refresh_authority_factory=refresh_authority_factory,
    )
    insert_legacy_test_post(
        app,
        router.routes[0],
        path="/api/content/work-items/{work_item_id}/initial-draft",
        monkeypatch=monkeypatch,
    )


__all__ = [
    "register_legacy_initial_draft_test_route",
    "register_legacy_initial_draft_test_route_before_production",
]
