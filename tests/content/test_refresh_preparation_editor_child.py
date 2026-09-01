from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import wilq.content.workflow.decisions.production as production_module
from apps.api.wilq_api.routers import content_workflow as workflow_router
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from wilq.content.workflow.contracts.contracts import (
    ContentDraftRevisionSaveRequest,
    ContentDraftRevisionWorkspace,
)
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationRow,
    classification_counts,
)
from wilq.content.workflow.documents.codex_revision_commit import ContentDraftRevisionContext
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionPageAssets,
    ContentDraftRevisionProposalMetadata,
    ContentDraftRevisionProposalSectionLineage,
    ContentDraftRevisionReviewCommand,
    ContentDraftRevisionSection,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationClassificationBinding,
    build_content_refresh_preparation_authorization,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.schemas.core import utc_now

_SERVICE_CARD_ID = "ekologus_service_bdo_reporting"
_PLANNING_INPUT_DIGEST = "a" * 64


def test_needs_changes_editor_child_preserves_refresh_binding_without_codex_completion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    store, parent = _bound_parent(tmp_path)
    _mark_parent_needs_changes(store, parent)
    client = _editor_client(monkeypatch, store, parent)

    response = client.post(
        f"/api/content/work-items/{parent.work_item_id}/draft-revisions",
        json=_editor_request(parent),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "created"
    child = store.load_draft_revision_state(parent.work_item_id).latest_revision
    assert child is not None
    assert child.base_revision_id == parent.revision_id
    assert child.proposal_metadata is None
    assert child.refresh_preparation_binding == parent.refresh_preparation_binding


def test_full_document_editor_child_route_persists_page_assets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    store, parent = _bound_parent(tmp_path)
    _mark_parent_needs_changes(store, parent)
    client = _editor_client(monkeypatch, store, parent)
    payload = _editor_request(parent)
    payload["page_assets"] = parent.page_assets.model_copy(
        update={"wordpress_title": payload["title"]}
    ).model_dump(mode="json")

    response = client.post(
        f"/api/content/work-items/{parent.work_item_id}/draft-revisions",
        json=payload,
    )

    assert response.status_code == 200, response.text
    assert response.json()["revision"]["page_assets"] == payload["page_assets"]


def test_stale_full_document_editor_child_returns_typed_conflict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    store, parent = _bound_parent(tmp_path)
    _mark_parent_needs_changes(store, parent)
    client = _editor_client(monkeypatch, store, parent, context_current=False)
    payload = _editor_request(parent)
    payload["page_assets"] = parent.page_assets.model_copy(
        update={"wordpress_title": payload["title"]}
    ).model_dump(mode="json")

    response = client.post(
        f"/api/content/work-items/{parent.work_item_id}/draft-revisions",
        json=payload,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "stale_context"


def test_stale_refresh_receipt_in_editor_child_returns_typed_conflict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    store, parent = _bound_parent(tmp_path)
    _mark_parent_needs_changes(store, parent)
    binding = parent.refresh_preparation_binding
    assert binding is not None
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            """
            UPDATE content_refresh_preparation_authorizations
            SET public_url = 'https://www.ekologus.pl/inny-adres/'
            WHERE authorization_id = ?
            """,
            (binding.authorization_id,),
        )
    client = _editor_client(monkeypatch, store, parent)

    response = client.post(
        f"/api/content/work-items/{parent.work_item_id}/draft-revisions",
        json=_editor_request(parent),
    )

    assert response.status_code == 409, response.text
    assert response.json()["status"] == "conflict"
    assert response.json()["code"] == "stale_context"
    state = store.load_draft_revision_state(parent.work_item_id)
    assert state.latest_revision == parent
    assert state.revision_count == 1


def _bound_parent(tmp_path) -> tuple[ContentWorkflowStore, object]:
    store = ContentWorkflowStore(tmp_path / "refresh-editor.sqlite3")
    run = _refresh_run()
    store.record_production_classification(run)
    row = run.rows[0]
    work_item_id = row.current_work_item_id
    assert work_item_id is not None
    classification = ContentRefreshPreparationClassificationBinding(
        classification_run_id=run.run_id,
        classification_run_digest=run.run_digest,
        decision_set_digest=run.input.decision_set_digest,
        source_packet_row_digest=row.source_packet_row_digest,
        current_work_item_id=work_item_id,
        canonical_path=row.canonical_path,
        public_url=row.public_url,
        classification_blocker_codes=[blocker.code for blocker in row.blockers],
    )
    authorization = build_content_refresh_preparation_authorization(
        work_item_id=work_item_id,
        classification=classification,
        planning_input_digest=_PLANNING_INPUT_DIGEST,
        service_card_id=_SERVICE_CARD_ID,
        acknowledged_classification_blocker_codes=classification.classification_blocker_codes,
        authorized_by="wilku",
        authorized_at=utc_now(),
    )
    store.record_refresh_preparation_authorization(authorization)
    title = "BDO — pełna wersja związana z refresh"
    section = ContentDraftRevisionSection(
        section_id="section_refresh",
        heading="Zakres obowiązków",
        body_markdown="Treść oparta na bieżącym planie refresh.",
        evidence_ids=["ev_bdo"],
    )
    command = ContentDraftRevisionAppendCommand(
        schema_version="wilq_content_draft_revision_v2",
        work_item_id=work_item_id,
        draft_package_id="draft_package_refresh",
        draft_package_digest="b" * 64,
        planning_digest="c" * 64,
        planning_input_digest=_PLANNING_INPUT_DIGEST,
        service_card_id=_SERVICE_CARD_ID,
        service_digest="d" * 64,
        inventory_digest="e" * 64,
        final_canonical_url=row.public_url,
        title=title,
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title=title,
            meta_title="BDO — Ekologus",
            meta_description="Sprawdź obowiązki BDO.",
            h1="Obowiązki BDO",
            lead="Najpierw sprawdź obowiązki firmy.",
        ),
        sections=[section],
        proposal_metadata=ContentDraftRevisionProposalMetadata(
            codex_run_id="codex_refresh_parent",
            selected_section_headings=[section.heading],
            section_lineage=[
                ContentDraftRevisionProposalSectionLineage(
                    heading=section.heading,
                    evidence_ids=section.evidence_ids,
                )
            ],
            quality_verdict="reviewable",
            review_scope="persisted_selected_sections_and_declared_lineage",
            refresh_preparation_binding=authorization.binding,
        ),
        refresh_preparation_binding=authorization.binding,
        correction_reason="official_source_lineage_rebase",
        created_by="wilku",
    )
    result = store.append_draft_revision(command)
    assert result.revision is not None
    return store, result.revision


def _mark_parent_needs_changes(store: ContentWorkflowStore, parent: object) -> None:
    revision = parent
    result = store.review_draft_revision(
        ContentDraftRevisionReviewCommand(
            work_item_id=revision.work_item_id,
            revision_id=revision.revision_id,
            revision_digest=revision.content_digest,
            decision="needs_changes",
            reviewed_by="wilku",
            notes="Doprecyzuj pierwszą odpowiedź.",
        )
    )
    assert result.status == "created"


def _editor_client(
    monkeypatch: pytest.MonkeyPatch,
    store: ContentWorkflowStore,
    parent: object,
    *,
    context_current: bool = True,
) -> TestClient:
    revision = parent
    if context_current:
        command = workflow_router._build_editor_save_command(  # noqa: SLF001
            work_item_id=revision.work_item_id,
            request=ContentDraftRevisionSaveRequest.model_validate(_editor_request(revision)),
            latest_revision=revision,
            draft_package=SimpleNamespace(),
            planning=SimpleNamespace(),
            final_canonical_url=revision.final_canonical_url,
            revision_context_current=True,
        )
        assert command.refresh_preparation_binding == revision.refresh_preparation_binding
        assert command.proposal_metadata is None
        context = ContentDraftRevisionContext.from_command(command)
        assert context is not None
    else:
        context = None
    state = store.load_draft_revision_state(revision.work_item_id)
    workspace = ContentDraftRevisionWorkspace(
        status="needs_changes",
        latest_revision=revision,
        latest_review=state.latest_review,
        revision_count=state.revision_count,
        context_current=context_current,
        editor_title=revision.title,
        editor_sections=revision.sections,
        can_save=True,
        can_review=False,
        safe_next_step="Zapisz poprawioną wersję.",
    )
    snapshot = SimpleNamespace(
        draft_package=SimpleNamespace(
            draft_package_result=SimpleNamespace(draft_package=SimpleNamespace())
        ),
        preflight=SimpleNamespace(
            item=SimpleNamespace(
                final_canonical_url=revision.final_canonical_url,
                intended_final_url=None,
            )
        ),
        revision_workspace=workspace,
        planning_workspace=SimpleNamespace(section_map_current=True),
    )
    monkeypatch.setattr(
        workflow_router,
        "_snapshot_for_work_item_or_404",
        lambda _work_item_id: snapshot,
    )
    monkeypatch.setattr(workflow_router, "_editor_save_context", lambda _snapshot: context)
    monkeypatch.setattr(workflow_router, "content_workflow_store", lambda: store)
    app = FastAPI()
    app.include_router(workflow_router.router)
    return TestClient(app)


def _editor_request(parent: object) -> dict[str, object]:
    revision = parent
    return {
        "base_revision_id": revision.revision_id,
        "title": "BDO — poprawiona wersja związana z refresh",
        "sections": [
            {
                **section.model_dump(mode="json"),
                "body_markdown": "Poprawiona treść ręcznej rewizji po needs changes.",
                "content_html": "<p>Poprawiona treść ręcznej rewizji po needs changes.</p>",
            }
            for section in revision.sections
        ],
        "created_by": "wilku",
    }


def _refresh_run():
    run = exact_public_bdo_run()
    payload = run.rows[0].model_dump(mode="python")
    payload.update(
        {
            "decision": "refresh",
            "retained_work_item_id": None,
            "revision_id": None,
            "revision_digest": None,
            "revision_approved": False,
            "revision_complete": False,
            "retained_binding": None,
            "verified_actions": (),
            "verified_drafts": (),
        }
    )
    row = ContentProductionClassificationRow.model_validate(payload)
    return production_module._build_run(
        input_receipt=run.input,
        counts=classification_counts((row, run.rows[1])),
        freshness=run.freshness,
        source_receipts=run.source_receipts,
        judge_receipt=run.judge_receipt,
        rows=(row, run.rows[1]),
        audit=run.audit,
    )
