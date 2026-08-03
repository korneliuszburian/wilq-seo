from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_codex_proposal
from wilq.content.drafts.codex_section_proposal import propose_content_section_revision
from wilq.content.drafts.codex_section_proposal_contracts import (
    ContentCodexRuntimeTrace,
    ContentCodexSectionProposalBlocker,
    ContentCodexSectionProposalRequest,
    ContentCodexSectionProposalResponse,
)
from wilq.content.workflow.revisions import ContentDraftRevision, ContentDraftRevisionSection


@pytest.mark.parametrize("review_status", ["unreviewed", "approved"])
def test_repair_owner_requires_recorded_human_needs_changes(review_status: str) -> None:
    revision = ContentDraftRevision.model_construct(
        revision_id="content_revision_bdo_1",
        work_item_id="content_work_item_bdo",
        content_digest="a" * 64,
        sections=[
            ContentDraftRevisionSection.model_construct(
                section_id="section_bdo_1",
                heading="Zakres obowiązku",
            )
        ],
        cta_blocks=[],
    )
    snapshot = SimpleNamespace(
        preflight=SimpleNamespace(
            item=SimpleNamespace(
                id=revision.work_item_id,
                evidence_ids=[],
                source_connectors=[],
            )
        ),
        structured_generation=SimpleNamespace(
            structured_generation_result=SimpleNamespace(contract=None)
        ),
        revision_workspace=SimpleNamespace(
            latest_revision=revision,
            context_current=True,
            status=review_status,
            can_save=False,
        )
    )
    request = ContentCodexSectionProposalRequest(
        expected_base_digest=revision.content_digest,
        selected_section_ids=["section_bdo_1"],
        requested_by="wilku",
    )

    response = propose_content_section_revision(
        snapshot=cast(object, snapshot),
        base_revision_id=revision.revision_id,
        request=request,
        client=cast(object, None),
        workflow_store=cast(object, None),
        run_store=cast(object, None),
    )

    assert response.status == "blocked"
    assert response.revision is None
    assert response.blockers[0].code == "revision_not_ready_for_proposal"


def test_revision_repair_route_adapts_one_stable_component_without_prompt_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = APIRouter()
    app_for_test = FastAPI()
    observed: dict[str, object] = {}

    def snapshot_loader(work_item_id: str) -> SimpleNamespace:
        assert work_item_id == "content_work_item_bdo"
        return SimpleNamespace(revision_workspace=SimpleNamespace(latest_revision=None))

    def proposal(**kwargs: object) -> ContentCodexSectionProposalResponse:
        request = cast(ContentCodexSectionProposalRequest, kwargs["request"])
        observed["request"] = request
        return ContentCodexSectionProposalResponse(
            status="blocked",
            work_item_id="content_work_item_bdo",
            base_revision_id="content_revision_bdo_1",
            selected_section_headings=[],
            selected_cta_ids=request.selected_cta_ids,
            runtime=ContentCodexRuntimeTrace(status="not_started"),
            blockers=[
                ContentCodexSectionProposalBlocker(
                    code="revision_not_ready_for_proposal",
                    label="Ta wersja nie czeka na poprawki",
                    reason="Brakuje zapisanej decyzji człowieka.",
                    next_step="Zapisz decyzję review.",
                )
            ],
            safe_next_step="Zapisz decyzję review.",
        )

    monkeypatch.setattr(content_codex_proposal, "propose_content_section_revision", proposal)
    content_codex_proposal.register_content_revision_repair_route(
        router,
        snapshot_loader=snapshot_loader,
    )
    app_for_test.include_router(router)

    response = TestClient(app_for_test).post(
        "/api/content/work-items/content_work_item_bdo/draft-revisions/"
        "content_revision_bdo_1/repair-proposal",
        json={
            "expected_base_digest": "a" * 64,
            "selected_section_ids": ["section_bdo_1"],
            "requested_by": "wilku",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    request = cast(ContentCodexSectionProposalRequest, observed["request"])
    assert request.selected_section_ids == ["section_bdo_1"]
    assert request.selected_section_headings == []
    assert "model_input" not in response.text
    assert "system_instruction" not in response.text


def test_legacy_section_proposal_route_remains_retired() -> None:
    response = TestClient(app).post(
        "/api/content/work-items/content_work_item_retired/draft-revisions/"
        "content_revision_retired/codex-proposal",
        json={},
    )

    assert response.status_code == 404
