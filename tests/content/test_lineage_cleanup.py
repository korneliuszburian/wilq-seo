from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers import (
    content_lineage_cleanup_service as cleanup_service,
)
from apps.api.wilq_api.routers import content_workflow
from apps.api.wilq_api.routers.content_lineage_cleanup_service import (
    ContentLineageCleanupConflict,
    execute_content_lineage_cleanup,
)
from apps.api.wilq_api.routers.content_official_source_lineage import (
    register_content_official_source_lineage_route,
)
from tests.content.test_full_document_revision_v2 import (
    _draft_package,
    _full_document_command,
)
from wilq.content.workflow.contracts.contracts import (
    ContentDraftRevisionWorkspace,
    ContentRevisionLineageCleanupRequest,
)
from wilq.content.workflow.documents.codex_revision_commit import (
    ContentDraftRevisionContext,
    current_editor_draft_context_guard,
)
from wilq.content.workflow.documents.lineage_cleanup import (
    LineageCleanupBuildError,
    build_lineage_cleanup_command,
)
from wilq.content.workflow.documents.official_source_lineage_store import (
    ContentOfficialSourceLineageStore,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionOfficialSourceReference,
    ContentDraftRevisionProposalMetadata,
    ContentDraftRevisionProposalSectionLineage,
    ContentDraftRevisionSourceProvenance,
)
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationBinding,
)
from wilq.content.workflow.store.store import ContentWorkflowStore

OBSOLETE_SOURCE_FACT_ID = "regulatory_source_fact_83380d0458dfbc43988311bc"
OBSOLETE_EVIDENCE_ID = "ev_regulatory_source_review_83380d0458dfbc43988311bc"
CURRENT_SOURCE_FACT_ID = "regulatory_source_fact_13b920b86d6ed8e1000e6808"
CURRENT_EVIDENCE_ID = "ev_regulatory_source_review_13b920b86d6ed8e1000e6808"
SHARED_EVIDENCE_ID = "ev_shared_service_profile_source_facts"


def test_cleanup_builds_immutable_child_and_preserves_shared_lineage(
    tmp_path: Path,
) -> None:
    base = _persist_lineage_revision(tmp_path)
    metadata = _proposal_metadata(base)
    command = build_lineage_cleanup_command(
        base_revision=base.model_copy(update={"proposal_metadata": metadata}),
        source_fact_id=f"  {OBSOLETE_SOURCE_FACT_ID}  ",
        requested_by="  wilku  ",
    )
    child = ContentOfficialSourceLineageStore(tmp_path / "wilq.sqlite3").append_cleanup(
        command,
        expected_latest_review_decision_id=None,
    ).revision

    assert child is not None
    assert child.base_revision_id == base.revision_id
    assert child.correction_reason == "lineage_cleanup"
    assert child.created_by == "wilku"
    assert [item.source_fact_id for item in child.source_provenance] == [
        CURRENT_SOURCE_FACT_ID
    ]
    assert [item.source_fact_id for item in child.official_source_references] == [
        CURRENT_SOURCE_FACT_ID
    ]
    assert child.source_provenance[0].evidence_ids == [
        CURRENT_EVIDENCE_ID,
        SHARED_EVIDENCE_ID,
    ]
    assert child.official_source_references[0].evidence_ids == [
        CURRENT_EVIDENCE_ID,
        SHARED_EVIDENCE_ID,
    ]
    for component in [
        *child.sections,
        *child.faq,
        *child.cta_blocks,
        *child.internal_links,
    ]:
        assert OBSOLETE_EVIDENCE_ID not in component.evidence_ids
        assert SHARED_EVIDENCE_ID in component.evidence_ids
    assert child.proposal_metadata is not None
    assert OBSOLETE_EVIDENCE_ID not in child.proposal_metadata.section_lineage[0].evidence_ids
    assert SHARED_EVIDENCE_ID in child.proposal_metadata.section_lineage[0].evidence_ids

    persisted_parent = ContentWorkflowStore(tmp_path / "wilq.sqlite3").list_draft_revisions(
        base.work_item_id
    )[0]
    assert persisted_parent == base


def test_cleanup_fails_closed_for_missing_ambiguous_and_required_evidence(
    tmp_path: Path,
) -> None:
    base = _persist_lineage_revision(tmp_path)

    with pytest.raises(LineageCleanupBuildError) as missing:
        build_lineage_cleanup_command(
            base_revision=base,
            source_fact_id="regulatory_source_fact_missing",
            requested_by="wilku",
        )
    assert missing.value.code == "source_fact_not_found"

    ambiguous = base.model_copy(
        update={"source_provenance": [*base.source_provenance, base.source_provenance[0]]}
    )
    with pytest.raises(LineageCleanupBuildError) as duplicate:
        build_lineage_cleanup_command(
            base_revision=ambiguous,
            source_fact_id=OBSOLETE_SOURCE_FACT_ID,
            requested_by="wilku",
        )
    assert duplicate.value.code == "source_fact_ambiguous"

    disagreeing_reference = base.model_copy(
        update={
            "official_source_references": [
                base.official_source_references[0].model_copy(
                    update={"evidence_ids": [OBSOLETE_EVIDENCE_ID]}
                ),
                base.official_source_references[1],
            ]
        }
    )
    with pytest.raises(LineageCleanupBuildError) as disagreement:
        build_lineage_cleanup_command(
            base_revision=disagreeing_reference,
            source_fact_id=OBSOLETE_SOURCE_FACT_ID,
            requested_by="wilku",
        )
    assert disagreement.value.code == "source_fact_ambiguous"

    evidence_required = base.model_copy(
        update={
            "faq": [
                base.faq[0].model_copy(update={"evidence_ids": [OBSOLETE_EVIDENCE_ID]})
            ]
        }
    )
    with pytest.raises(LineageCleanupBuildError) as unavailable:
        build_lineage_cleanup_command(
            base_revision=evidence_required,
            source_fact_id=OBSOLETE_SOURCE_FACT_ID,
            requested_by="wilku",
        )
    assert unavailable.value.code == "lineage_cleanup_unavailable"


def test_cleanup_allows_no_official_reference_and_filters_cta_metadata(
    tmp_path: Path,
) -> None:
    base = _persist_lineage_revision(tmp_path)
    cta_metadata = ContentDraftRevisionProposalMetadata(
        codex_run_id="codex_run_lineage_cleanup_cta",
        selected_cta_ids=[base.cta_blocks[0].cta_id],
        cta_lineage=[
            {
                "cta_id": base.cta_blocks[0].cta_id,
                "evidence_ids": base.cta_blocks[0].evidence_ids,
            }
        ],
        quality_verdict="reviewable",
        review_scope="persisted_selected_components_and_declared_lineage",
    )
    without_target_reference = base.model_copy(
        update={
            "official_source_references": [base.official_source_references[1]],
            "proposal_metadata": cta_metadata,
        }
    )

    child = build_lineage_cleanup_command(
        base_revision=without_target_reference,
        source_fact_id=OBSOLETE_SOURCE_FACT_ID,
        requested_by="wilku",
    )

    assert [item.source_fact_id for item in child.official_source_references] == [
        CURRENT_SOURCE_FACT_ID
    ]
    assert child.proposal_metadata is not None
    assert OBSOLETE_EVIDENCE_ID not in child.proposal_metadata.cta_lineage[0].evidence_ids
    assert SHARED_EVIDENCE_ID in child.proposal_metadata.cta_lineage[0].evidence_ids


def test_cleanup_store_rechecks_context_inside_the_atomic_append(tmp_path: Path) -> None:
    path = tmp_path / "wilq.sqlite3"
    base = _persist_lineage_revision(tmp_path)
    command = build_lineage_cleanup_command(
        base_revision=base,
        source_fact_id=OBSOLETE_SOURCE_FACT_ID,
        requested_by="wilku",
    )
    expected = ContentDraftRevisionContext.from_command(command)
    assert expected is not None

    with current_editor_draft_context_guard(
        lambda: replace(expected, planning_digest="0" * 64)
    ):
        result = ContentOfficialSourceLineageStore(path).append_cleanup(
            command,
            expected_latest_review_decision_id=None,
        )

    assert result.status == "conflict"
    assert result.conflict is not None
    assert result.conflict.code == "stale_context"
    state = ContentWorkflowStore(path).load_draft_revision_state(base.work_item_id)
    assert state.revision_count == 1


def test_cleanup_service_returns_a_named_typed_digest_conflict(tmp_path: Path) -> None:
    base = _persist_lineage_revision(tmp_path)
    snapshot = SimpleNamespace(
        revision_workspace=_workspace(base, context_current=True)
    )

    result = execute_content_lineage_cleanup(
        work_item_id=base.work_item_id,
        revision_id=base.revision_id,
        request=ContentRevisionLineageCleanupRequest(
            expected_revision_digest="0" * 64,
            source_fact_id=OBSOLETE_SOURCE_FACT_ID,
            requested_by="wilku",
        ),
        snapshot_loader=lambda _work_item_id: snapshot,
    )

    assert isinstance(result, ContentLineageCleanupConflict)
    assert result.status == "conflict"
    assert result.code == "digest_mismatch"
    assert result.snapshot is snapshot


def test_cleanup_route_requires_current_context_and_returns_typed_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _persist_lineage_revision(tmp_path)
    current_context = False
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    specialized_store = ContentOfficialSourceLineageStore(tmp_path / "wilq.sqlite3")

    def snapshot_loader(work_item_id: str) -> SimpleNamespace:
        assert work_item_id == base.work_item_id
        latest = store.load_draft_revision_state(work_item_id).latest_revision
        assert latest is not None
        if latest.revision_id == base.revision_id:
            latest = latest.model_copy(update={"proposal_metadata": _proposal_metadata(latest)})
        return SimpleNamespace(
            revision_workspace=_workspace(latest, context_current=current_context)
        )

    router = APIRouter()
    register_content_official_source_lineage_route(router, snapshot_loader=snapshot_loader)
    app = FastAPI()
    app.include_router(router)
    monkeypatch.setattr(
        cleanup_service,
        "content_official_source_lineage_store",
        lambda: specialized_store,
    )
    client = TestClient(app)
    endpoint = (
        f"/api/content/work-items/{base.work_item_id}/draft-revisions/"
        f"{base.revision_id}/lineage-cleanup"
    )
    payload = {
        "expected_revision_digest": base.content_digest,
        "source_fact_id": f"  {OBSOLETE_SOURCE_FACT_ID}  ",
        "requested_by": "  wilku  ",
    }

    stale = client.post(endpoint, json=payload)
    assert stale.status_code == 409
    assert stale.json()["code"] == "lineage_cleanup_unavailable"
    assert store.load_draft_revision_state(base.work_item_id).revision_count == 1

    current_context = True
    created = client.post(endpoint, json=payload)
    assert created.status_code == 200
    body = created.json()
    assert body["revision"]["base_revision_id"] == base.revision_id
    assert body["revision"]["correction_reason"] == "lineage_cleanup"
    assert body["revision"]["created_by"] == "wilku"
    assert body["workspace"]["latest_revision"]["revision_id"] == body["revision"]["revision_id"]


def test_refresh_bound_cleanup_uses_current_semantic_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _persist_lineage_revision(tmp_path)
    bound_parent = _refresh_bound_revision(base)
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    specialized_store = ContentOfficialSourceLineageStore(tmp_path / "wilq.sqlite3")
    semantic_calls: list[str] = []

    def generic_snapshot(work_item_id: str) -> SimpleNamespace:
        assert work_item_id == base.work_item_id
        return SimpleNamespace(
            revision_workspace=_workspace(bound_parent, context_current=False)
        )

    def semantic_snapshot(work_item_id: str) -> SimpleNamespace:
        assert work_item_id == base.work_item_id
        semantic_calls.append(work_item_id)
        latest = store.load_draft_revision_state(work_item_id).latest_revision
        assert latest is not None
        revision = bound_parent if latest.revision_id == base.revision_id else latest
        return SimpleNamespace(
            revision_workspace=_workspace(revision, context_current=True)
        )

    monkeypatch.setattr(
        content_workflow,
        "semantic_review_snapshot_for_work_item_or_404",
        semantic_snapshot,
    )
    monkeypatch.setattr(
        cleanup_service,
        "content_official_source_lineage_store",
        lambda: specialized_store,
    )
    client = _cleanup_client(generic_snapshot)

    response = client.post(_cleanup_endpoint(base), json=_cleanup_payload(base))

    assert response.status_code == 200, response.text
    assert response.json()["revision"]["correction_reason"] == "lineage_cleanup"
    assert semantic_calls == [base.work_item_id] * 3
    assert store.load_draft_revision_state(base.work_item_id).revision_count == 2


def test_refresh_bound_cleanup_rejects_a_stale_semantic_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _persist_lineage_revision(tmp_path)
    bound_parent = _refresh_bound_revision(base)
    store = ContentWorkflowStore(tmp_path / "wilq.sqlite3")
    semantic_calls: list[str] = []

    def generic_snapshot(work_item_id: str) -> SimpleNamespace:
        assert work_item_id == base.work_item_id
        return SimpleNamespace(
            revision_workspace=_workspace(bound_parent, context_current=False)
        )

    def stale_semantic_snapshot(work_item_id: str) -> SimpleNamespace:
        assert work_item_id == base.work_item_id
        semantic_calls.append(work_item_id)
        return SimpleNamespace(
            revision_workspace=_workspace(bound_parent, context_current=False)
        )

    monkeypatch.setattr(
        content_workflow,
        "semantic_review_snapshot_for_work_item_or_404",
        stale_semantic_snapshot,
    )
    response = _cleanup_client(generic_snapshot).post(
        _cleanup_endpoint(base),
        json=_cleanup_payload(base),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "lineage_cleanup_unavailable"
    assert semantic_calls == [base.work_item_id]
    assert store.load_draft_revision_state(base.work_item_id).revision_count == 1


def _persist_lineage_revision(tmp_path: Path) -> ContentDraftRevision:
    target_provenance = ContentDraftRevisionSourceProvenance(
        source_fact_id=OBSOLETE_SOURCE_FACT_ID,
        source_url_or_path="https://commission.europa.eu/obsolete-green-deal.pdf",
        freshness_date="2026-09-01",
        evidence_ids=[OBSOLETE_EVIDENCE_ID, SHARED_EVIDENCE_ID],
    )
    current_provenance = ContentDraftRevisionSourceProvenance(
        source_fact_id=CURRENT_SOURCE_FACT_ID,
        source_url_or_path="https://commission.europa.eu/current-green-deal.pdf",
        freshness_date="2026-09-02",
        evidence_ids=[CURRENT_EVIDENCE_ID, SHARED_EVIDENCE_ID],
    )
    target_reference = _official_reference(
        source_fact_id=OBSOLETE_SOURCE_FACT_ID,
        source_url="https://commission.europa.eu/obsolete-green-deal.pdf",
        evidence_ids=[OBSOLETE_EVIDENCE_ID, SHARED_EVIDENCE_ID],
    )
    current_reference = _official_reference(
        source_fact_id=CURRENT_SOURCE_FACT_ID,
        source_url="https://commission.europa.eu/current-green-deal.pdf",
        evidence_ids=[CURRENT_EVIDENCE_ID, SHARED_EVIDENCE_ID],
    )
    base_command = _full_document_command(_draft_package(), base_revision_id=None)
    command = base_command.model_copy(
        update={
            "sections": _with_lineage_evidence(base_command.sections),
            "faq": _with_lineage_evidence(base_command.faq),
            "cta_blocks": _with_lineage_evidence(base_command.cta_blocks),
            "internal_links": _with_lineage_evidence(base_command.internal_links),
            "source_provenance": [target_provenance, current_provenance],
            "official_source_references": [target_reference, current_reference],
        }
    )
    revision = ContentWorkflowStore(tmp_path / "wilq.sqlite3").append_draft_revision(
        command
    ).revision
    assert revision is not None
    return revision


def _with_lineage_evidence(components: list) -> list:
    return [
        component.model_copy(
            update={
                "evidence_ids": [
                    *component.evidence_ids,
                    OBSOLETE_EVIDENCE_ID,
                    SHARED_EVIDENCE_ID,
                ]
            }
        )
        for component in components
    ]


def _official_reference(
    *,
    source_fact_id: str,
    source_url: str,
    evidence_ids: list[str],
) -> ContentDraftRevisionOfficialSourceReference:
    return ContentDraftRevisionOfficialSourceReference(
        source_fact_id=source_fact_id,
        source_url=source_url,
        source_title="Komisja Europejska — Zielony Ład",
        verified_on="2026-09-02",
        evidence_ids=evidence_ids,
        regulatory_requirement_ids=["green_deal"],
    )


def _proposal_metadata(base: ContentDraftRevision) -> ContentDraftRevisionProposalMetadata:
    return ContentDraftRevisionProposalMetadata(
        codex_run_id="codex_run_lineage_cleanup",
        selected_section_headings=[base.sections[0].heading],
        section_lineage=[
            ContentDraftRevisionProposalSectionLineage(
                heading=base.sections[0].heading,
                evidence_ids=base.sections[0].evidence_ids,
            )
        ],
        quality_verdict="reviewable",
    )


def _refresh_bound_revision(base: ContentDraftRevision) -> ContentDraftRevision:
    binding = ContentRefreshPreparationBinding(
        authorization_id="content_refresh_preparation_authorization_aaaaaaaaaaaaaaaaaaaaaaaa",
        authorization_digest="a" * 64,
        classification_run_id="content_production_classification_lineage_cleanup",
        classification_run_digest="b" * 64,
        decision_set_digest="c" * 64,
        source_packet_row_digest="d" * 64,
        current_work_item_id=base.work_item_id,
        canonical_path="/oferta/doradztwo",
        public_url=base.final_canonical_url or "",
        service_card_id=base.service_card_id,
        planning_input_digest=base.planning_input_digest or "",
    )
    metadata = _proposal_metadata(base).model_copy(
        update={"refresh_preparation_binding": binding}
    )
    return base.model_copy(
        update={
            "proposal_metadata": metadata,
            "refresh_preparation_binding": binding,
        }
    )


def _cleanup_client(snapshot_loader) -> TestClient:
    router = APIRouter()
    register_content_official_source_lineage_route(router, snapshot_loader=snapshot_loader)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _cleanup_endpoint(base: ContentDraftRevision) -> str:
    return (
        f"/api/content/work-items/{base.work_item_id}/draft-revisions/"
        f"{base.revision_id}/lineage-cleanup"
    )


def _cleanup_payload(base: ContentDraftRevision) -> dict[str, str]:
    return {
        "expected_revision_digest": base.content_digest,
        "source_fact_id": OBSOLETE_SOURCE_FACT_ID,
        "requested_by": "wilku",
    }


def _workspace(
    revision: ContentDraftRevision,
    *,
    context_current: bool,
) -> ContentDraftRevisionWorkspace:
    return ContentDraftRevisionWorkspace(
        status="unreviewed",
        latest_revision=revision,
        latest_review=None,
        revision_count=revision.revision_number,
        context_current=context_current,
        editor_title=revision.title,
        editor_sections=revision.sections,
        can_save=False,
        can_review=context_current,
        safe_next_step="Odśwież dokument.",
    )
