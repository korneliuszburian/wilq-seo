from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

import wilq.content.quality.review_packet_binding as review_packet_binding
from apps.api.wilq_api.routers import content_workflow as content_workflow_router
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generated_proposal_contracts import ContentPlanningProposalRequest
from wilq.content.quality.review_packet_binding import resolve_content_review_inputs
from wilq.content.workflow.contracts.contracts import (
    ContentDraftRevisionWorkspace,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningWorkspace,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevision
from wilq.content.workflow.refresh_preparation import RefreshPreparationRuntimeAuthorized
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationClassificationBinding,
    build_content_refresh_preparation_authorization,
)


def _refresh_context(
    work_item_id: str,
    *,
    base_digest: str = "a" * 64,
    packet_digest: str = "b" * 64,
) -> tuple[Any, Any, ContentDraftRevision, ContentPlanningProposal]:
    classification = ContentRefreshPreparationClassificationBinding(
        classification_run_id=f"classification_run_{work_item_id}",
        classification_run_digest="c" * 64,
        decision_set_digest="d" * 64,
        source_packet_row_digest="e" * 64,
        current_work_item_id=work_item_id,
        canonical_path="/uslugi/operat-wodnoprawny",
        public_url="https://ekologus.pl/uslugi/operat-wodnoprawny",
    )
    authorization = build_content_refresh_preparation_authorization(
        work_item_id=work_item_id,
        classification=classification,
        planning_input_digest=base_digest,
        service_card_id="ekologus_service_operat_wodnoprawny",
        acknowledged_classification_blocker_codes=[],
        authorized_by="wilku",
        authorized_at=datetime.now(UTC),
    )
    packet_binding = authorization.binding.model_copy(
        update={"planning_input_digest": packet_digest}
    )
    revision = ContentDraftRevision.model_construct(
        schema_version="wilq_content_draft_revision_v2",
        work_item_id=work_item_id,
        revision_id=f"revision_{work_item_id}",
        content_digest="f" * 64,
        planning_digest="1" * 64,
        planning_input_digest=packet_digest,
        content_kind="service",
        service_card_id=packet_binding.service_card_id,
        research_packet_id="content_research_packet_refresh",
        research_packet_digest="2" * 64,
        refresh_preparation_binding=packet_binding,
        sections=[],
    )
    proposal = ContentPlanningProposal.model_construct(
        work_item_id=work_item_id,
        planning_digest=revision.planning_digest,
        planning_input_digest=packet_digest,
        content_kind="service",
        service_card_id=packet_binding.service_card_id,
        final_canonical_url=packet_binding.public_url,
        refresh_preparation_binding=packet_binding,
        research_packet_id=revision.research_packet_id,
        research_packet_digest=revision.research_packet_digest,
    )
    return authorization, packet_binding, revision, proposal


def _snapshot(
    revision: ContentDraftRevision,
    proposal: ContentPlanningProposal | None,
    *,
    current_step_id: str = "authority_base",
) -> ContentWorkItemWorkflowSnapshotResponse:
    revision_workspace = ContentDraftRevisionWorkspace.model_construct(
        status="unreviewed",
        latest_revision=revision,
        latest_review=None,
        revision_count=1,
        context_current=True,
        editor_title="Draft",
        editor_sections=[],
        can_save=False,
        can_review=True,
        safe_next_step="Przejdź do review.",
    )
    planning_workspace = (
        None if proposal is None else ContentPlanningWorkspace.model_construct(proposal=proposal)
    )
    return ContentWorkItemWorkflowSnapshotResponse.model_construct(
        preflight=SimpleNamespace(item=SimpleNamespace(id=revision.work_item_id)),
        revision_workspace=revision_workspace,
        planning_workspace=planning_workspace,
        current_step_id=current_step_id,
        operator_steps=SimpleNamespace(),
    )


def _assert_fail_closed(snapshot: ContentWorkItemWorkflowSnapshotResponse) -> None:
    assert snapshot.planning_workspace is None
    assert snapshot.revision_workspace.can_review is False
    assert snapshot.revision_workspace.can_save is False
    assert "autoryzacji" in snapshot.revision_workspace.safe_next_step


def test_refresh_bound_semantic_review_snapshot_fails_closed_without_authorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work_item_id = "content_work_item_refresh"
    _authorization, binding, revision, proposal = _refresh_context(work_item_id)
    expected_snapshot = _snapshot(revision, proposal)
    canonical_calls: list[tuple[str, object | None, str | None, bool | None]] = []

    def record_canonical(
        received_work_item_id: str,
        *,
        revision_state_override: object | None = None,
        service_card_id_override: str | None = None,
        prefer_revision_bound_proposal: bool | None = None,
    ) -> object:
        canonical_calls.append(
            (
                received_work_item_id,
                revision_state_override,
                service_card_id_override,
                prefer_revision_bound_proposal,
            )
        )
        return expected_snapshot

    monkeypatch.setattr(
        content_workflow_router,
        "content_workflow_store",
        lambda: SimpleNamespace(
            load_draft_revision_state=lambda received_work_item_id: SimpleNamespace(
                latest_revision=revision if received_work_item_id == work_item_id else None
            ),
            load_refresh_preparation_authorization=lambda _authorization_id: None,
        ),
    )
    authority_calls = 0

    def unexpected_authority_call(*_args: object, **_kwargs: object) -> object:
        nonlocal authority_calls
        authority_calls += 1
        return object()

    monkeypatch.setattr(
        content_workflow_router,
        "content_refresh_preparation_authority",
        lambda: SimpleNamespace(resolve_planning=unexpected_authority_call),
    )
    monkeypatch.setattr(
        content_workflow_router,
        "_snapshot_for_work_item_or_404",
        record_canonical,
    )

    result = content_workflow_router.semantic_review_snapshot_for_work_item_or_404(work_item_id)

    _assert_fail_closed(result)
    assert authority_calls == 0
    assert len(canonical_calls) == 1
    assert canonical_calls[0][0] == work_item_id
    assert canonical_calls[0][1] is not None
    assert canonical_calls[0][2] == binding.service_card_id
    assert canonical_calls[0][3] is True


def test_refresh_bound_semantic_review_uses_authority_digest_before_packet_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work_item_id = "content_work_item_refresh_packet"
    authorization, packet_binding, revision, proposal = _refresh_context(work_item_id)
    canonical_snapshot = _snapshot(revision, proposal, current_step_id="canonical")
    authority_snapshot = _snapshot(revision, None, current_step_id="authority_base")
    bound_workspace = canonical_snapshot.revision_workspace.model_copy(
        update={"safe_next_step": "związany workspace"}
    )
    observed: list[ContentPlanningProposalRequest] = []

    def record_authority_request(
        _work_item_id: str,
        request: ContentPlanningProposalRequest,
    ) -> RefreshPreparationRuntimeAuthorized:
        observed.append(request)
        return RefreshPreparationRuntimeAuthorized(
            work_item_id=work_item_id,
            snapshot=authority_snapshot,
            planning_input=ContentPlanningInput.model_construct(
                work_item_id=work_item_id,
                planning_input_digest=authorization.planning_input_digest,
            ),
            classification=authorization.binding,
            service_candidate=None,
            authorization=authorization,
        )

    monkeypatch.setattr(
        content_workflow_router,
        "content_workflow_store",
        lambda: SimpleNamespace(
            load_draft_revision_state=lambda _work_item_id: SimpleNamespace(
                latest_revision=revision
            ),
            load_refresh_preparation_authorization=lambda authorization_id: (
                authorization if authorization_id == authorization.authorization_id else None
            ),
        ),
    )
    monkeypatch.setattr(
        content_workflow_router,
        "content_refresh_preparation_authority",
        lambda: SimpleNamespace(
            resolve_planning=record_authority_request,
        ),
    )
    monkeypatch.setattr(
        content_workflow_router,
        "_snapshot_for_work_item_or_404",
        lambda _work_item_id, **_kwargs: canonical_snapshot,
    )
    monkeypatch.setattr(
        content_workflow_router,
        "_binding_aware_revision_workspace",
        lambda **_kwargs: bound_workspace,
    )

    result = content_workflow_router.semantic_review_snapshot_for_work_item_or_404(work_item_id)

    assert len(observed) == 1
    assert observed[0].expected_planning_input_digest == authorization.planning_input_digest
    assert observed[0].refresh_preparation_authorization_id == authorization.authorization_id
    assert (
        observed[0].expected_refresh_preparation_authorization_digest
        == authorization.authorization_digest
    )
    assert str(result.current_step_id) == "authority_base"
    assert result.planning_workspace is canonical_snapshot.planning_workspace
    assert result.planning_workspace is not None
    assert result.planning_workspace.proposal.refresh_preparation_binding == packet_binding
    assert result.revision_workspace is bound_workspace

    packet: Any = SimpleNamespace(
        packet_id=revision.research_packet_id,
        packet_digest=revision.research_packet_digest,
        current_work_item_id=work_item_id,
        status="exact_current",
    )
    current_packet: Any = SimpleNamespace(
        status="current",
        packet_id=packet.packet_id,
        packet_digest=packet.packet_digest,
        current_work_item_id=work_item_id,
    )
    base_input = SimpleNamespace(
        work_item_id=work_item_id,
        planning_input_digest=authorization.planning_input_digest,
    )
    packet_input = SimpleNamespace(
        work_item_id=work_item_id,
        planning_input_digest=packet_binding.planning_input_digest,
        research_packet_id=packet.packet_id,
        research_packet_digest=packet.packet_digest,
    )

    class ReviewStore:
        def load_content_research_packet(self, _packet_id: str) -> object:
            return packet

    monkeypatch.setattr(
        review_packet_binding,
        "bind_research_packet_to_planning_input",
        lambda _base, _packet: packet_input,
    )
    monkeypatch.setattr(
        review_packet_binding,
        "revalidate_content_research_packet",
        lambda **_kwargs: current_packet,
    )
    resolution = resolve_content_review_inputs(
        snapshot=result,
        revision_id=revision.revision_id,
        expected_revision_digest=revision.content_digest,
        workflow_store=cast(Any, ReviewStore()),
        planning_input_builder=lambda *_args, **_kwargs: SimpleNamespace(
            planning_input=base_input,
            blockers=[],
        ),
    )
    assert resolution.inputs is not None, resolution.blocker
    assert (
        resolution.inputs.planning_input.planning_input_digest
        == packet_binding.planning_input_digest
    )
    assert resolution.inputs.packet is packet
    assert resolution.inputs.current_packet is current_packet


def test_legacy_semantic_review_snapshot_keeps_default_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work_item_id = "content_work_item_legacy"
    expected_snapshot = object()

    monkeypatch.setattr(
        content_workflow_router,
        "content_workflow_store",
        lambda: SimpleNamespace(
            load_draft_revision_state=lambda _work_item_id: SimpleNamespace(
                latest_revision=SimpleNamespace(refresh_preparation_binding=None)
            )
        ),
    )
    monkeypatch.setattr(
        content_workflow_router,
        "_snapshot_for_work_item_or_404",
        lambda received_work_item_id, **_kwargs: (
            expected_snapshot if received_work_item_id == work_item_id else None
        ),
    )

    assert (
        content_workflow_router.semantic_review_snapshot_for_work_item_or_404(work_item_id)
        is expected_snapshot
    )


@pytest.mark.parametrize("authorization_state", ["missing", "foreign", "digest_drift"])
def test_refresh_bound_semantic_review_fails_closed_for_invalid_authorization(
    monkeypatch: pytest.MonkeyPatch,
    authorization_state: str,
) -> None:
    work_item_id = "content_work_item_invalid_authorization"
    authorization, _binding, revision, proposal = _refresh_context(work_item_id)
    canonical_snapshot = _snapshot(revision, proposal)
    if authorization_state == "missing":
        persisted_authorization = None
    elif authorization_state == "foreign":
        persisted_authorization, _foreign_binding, _foreign_revision, _foreign_proposal = (
            _refresh_context("content_work_item_foreign_authorization")
        )
    else:
        (
            persisted_authorization,
            _drift_binding,
            _drift_revision,
            _drift_proposal,
        ) = _refresh_context(
            work_item_id,
            base_digest="9" * 64,
            packet_digest="8" * 64,
        )
    authority_calls = 0

    def unexpected_authority_call(*_args: object, **_kwargs: object) -> object:
        nonlocal authority_calls
        authority_calls += 1
        return object()

    monkeypatch.setattr(
        content_workflow_router,
        "content_workflow_store",
        lambda: SimpleNamespace(
            load_draft_revision_state=lambda _work_item_id: SimpleNamespace(
                latest_revision=revision
            ),
            load_refresh_preparation_authorization=lambda _authorization_id: (
                persisted_authorization
            ),
        ),
    )
    monkeypatch.setattr(
        content_workflow_router,
        "content_refresh_preparation_authority",
        lambda: SimpleNamespace(resolve_planning=unexpected_authority_call),
    )
    monkeypatch.setattr(
        content_workflow_router,
        "_snapshot_for_work_item_or_404",
        lambda _work_item_id, **_kwargs: canonical_snapshot,
    )

    result = content_workflow_router.semantic_review_snapshot_for_work_item_or_404(work_item_id)

    _assert_fail_closed(result)
    assert authority_calls == 0


def test_refresh_bound_semantic_review_fails_closed_when_authority_resolution_is_not_authorized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work_item_id = "content_work_item_stale_authority"
    authorization, _binding, revision, proposal = _refresh_context(work_item_id)
    canonical_snapshot = _snapshot(revision, proposal)
    monkeypatch.setattr(
        content_workflow_router,
        "content_workflow_store",
        lambda: SimpleNamespace(
            load_draft_revision_state=lambda _work_item_id: SimpleNamespace(
                latest_revision=revision
            ),
            load_refresh_preparation_authorization=lambda _authorization_id: authorization,
        ),
    )
    monkeypatch.setattr(
        content_workflow_router,
        "content_refresh_preparation_authority",
        lambda: SimpleNamespace(resolve_planning=lambda *_args: SimpleNamespace(status="blocked")),
    )
    monkeypatch.setattr(
        content_workflow_router,
        "_snapshot_for_work_item_or_404",
        lambda _work_item_id, **_kwargs: canonical_snapshot,
    )

    result = content_workflow_router.semantic_review_snapshot_for_work_item_or_404(work_item_id)

    _assert_fail_closed(result)


def test_refresh_bound_semantic_review_fails_closed_on_proposal_binding_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work_item_id = "content_work_item_proposal_mismatch"
    authorization, packet_binding, revision, proposal = _refresh_context(work_item_id)
    mismatched_proposal = proposal.model_copy(
        update={
            "refresh_preparation_binding": packet_binding.model_copy(
                update={"planning_input_digest": "9" * 64}
            )
        }
    )
    canonical_snapshot = _snapshot(revision, mismatched_proposal)
    authority_calls = 0

    def unexpected_authority_call(*_args: object, **_kwargs: object) -> object:
        nonlocal authority_calls
        authority_calls += 1
        return object()

    monkeypatch.setattr(
        content_workflow_router,
        "content_workflow_store",
        lambda: SimpleNamespace(
            load_draft_revision_state=lambda _work_item_id: SimpleNamespace(
                latest_revision=revision
            ),
            load_refresh_preparation_authorization=lambda _authorization_id: authorization,
        ),
    )
    monkeypatch.setattr(
        content_workflow_router,
        "content_refresh_preparation_authority",
        lambda: SimpleNamespace(resolve_planning=unexpected_authority_call),
    )
    monkeypatch.setattr(
        content_workflow_router,
        "_snapshot_for_work_item_or_404",
        lambda _work_item_id, **_kwargs: canonical_snapshot,
    )

    result = content_workflow_router.semantic_review_snapshot_for_work_item_or_404(work_item_id)

    _assert_fail_closed(result)
    assert authority_calls == 0
