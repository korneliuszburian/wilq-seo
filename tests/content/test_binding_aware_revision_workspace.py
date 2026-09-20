from datetime import UTC, datetime
from types import SimpleNamespace

import apps.api.wilq_api.routers.content_workflow as content_workflow
from wilq.content.drafts.package import (
    ContentDraftPackage,
    ContentDraftSection,
)
from wilq.content.workflow.contracts.contracts import (
    ContentDraftRevisionWorkspace,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningWorkspace,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionOfficialSourceReference,
    ContentDraftRevisionSection,
    ContentDraftRevisionState,
    content_draft_package_digest,
)
from wilq.content.workflow.pipeline_steps.snapshot_assembly import _gate_revision_workspace


def _revision(*, official: bool, source_material_ids: list[str]) -> ContentDraftRevision:
    return ContentDraftRevision.model_construct(
        document_kind="refresh_existing",
        content_kind="editorial",
        service_card_id=None,
        refresh_preparation_binding=object(),
        official_source_references=(
            [
                ContentDraftRevisionOfficialSourceReference.model_construct(
                    source_fact_id="regulatory_source_fact",
                    source_url="https://www.gov.pl/web/chemikalia/clp",
                    source_title="CLP",
                    verified_on="2026-09-01",
                    evidence_ids=["ev_regulatory"],
                    regulatory_requirement_ids=["reach_clp_distinct_scope"],
                )
            ]
            if official
            else []
        ),
        source_material_ids=source_material_ids,
        sections=[],
    )


def test_rendered_wordpress_material_stays_blocked_for_mixed_revision() -> None:
    workspace = ContentDraftRevisionWorkspace.model_construct(
        latest_revision=_revision(official=True, source_material_ids=["unreviewed_material"]),
        can_review=True,
        safe_next_step="Przejdź do review.",
    )

    gated = _gate_revision_workspace(
        workspace,
        planning_workspace=None,
        material_confidence="review_required",
    )

    assert gated.can_review is False


def test_independently_grounded_editorial_revision_can_review_rendered_inventory() -> None:
    workspace = ContentDraftRevisionWorkspace.model_construct(
        latest_revision=_revision(official=True, source_material_ids=[]),
        can_review=True,
        safe_next_step="Przejdź do review.",
    )

    gated = _gate_revision_workspace(
        workspace,
        planning_workspace=None,
        material_confidence="review_required",
    )

    assert gated.can_review is True


def test_binding_aware_workspace_uses_resolved_package_and_canonical_plan(
    monkeypatch,
) -> None:
    package = object()
    proposal = SimpleNamespace(
        planning_digest="exact-plan",
        planning_input_digest="exact-input",
        service_card_id=None,
    )
    planning = SimpleNamespace(proposal=proposal)
    resolved = SimpleNamespace(
        draft_package=SimpleNamespace(
            draft_package_result=SimpleNamespace(draft_package=package)
        )
    )
    canonical = SimpleNamespace(
        planning_workspace=planning,
        preflight=SimpleNamespace(
            item=SimpleNamespace(wordpress_content_material_confidence=None)
        ),
        structured_generation=SimpleNamespace(
            structured_generation_result=SimpleNamespace(contract=object())
        ),
        revision_workspace="fallback",
    )
    observed: dict[str, object] = {}
    ungated = object()
    gated = object()
    monkeypatch.setattr(
        content_workflow,
        "build_content_draft_revision_workspace",
        lambda **kwargs: observed.update(kwargs) or ungated,
    )
    monkeypatch.setattr(
        content_workflow,
        "_gate_revision_workspace",
        lambda *_args, **_kwargs: gated,
    )

    result = content_workflow._binding_aware_revision_workspace(
        resolved_snapshot=resolved,
        canonical_snapshot=canonical,
        revision_state="revision-state",
    )

    assert result is gated
    assert observed["item"].wordpress_content_material_confidence is None
    assert observed["draft_package"] is package
    assert observed["planning_digest"] == "exact-plan"
    assert observed["planning_input_digest"] == "exact-input"


def test_binding_aware_workspace_removes_only_current_material_blocker(
    monkeypatch,
) -> None:
    work_item_id = "content_work_item_material_review_gate"
    revision = _revision(official=False, source_material_ids=["rendered_material"])
    workspace = ContentDraftRevisionWorkspace.model_construct(
        latest_revision=revision,
        can_review=True,
        safe_next_step="Przejdź do review.",
    )
    planning = SimpleNamespace(
        proposal=SimpleNamespace(
            planning_digest="exact-plan",
            planning_input_digest="exact-input",
            service_card_id=None,
        )
    )
    canonical = SimpleNamespace(
        preflight=SimpleNamespace(
            item=SimpleNamespace(
                id=work_item_id,
                wordpress_content_material_confidence="review_required",
            )
        ),
        planning_workspace=planning,
        structured_generation=SimpleNamespace(
            structured_generation_result=SimpleNamespace(contract=object())
        ),
        revision_workspace=workspace,
    )
    resolved = SimpleNamespace(
        draft_package=SimpleNamespace(
            draft_package_result=SimpleNamespace(draft_package=object())
        )
    )
    monkeypatch.setattr(
        content_workflow,
        "build_content_draft_revision_workspace",
        lambda **_kwargs: workspace,
    )
    monkeypatch.setattr(
        content_workflow,
        "content_workflow_store",
        lambda: object(),
    )
    monkeypatch.setattr(
        content_workflow,
        "read_content_material_review",
        lambda **_kwargs: SimpleNamespace(status="stale"),
    )

    blocked = content_workflow._binding_aware_revision_workspace(
        resolved_snapshot=resolved,
        canonical_snapshot=canonical,
        revision_state="revision-state",
    )
    assert blocked.can_review is False

    monkeypatch.setattr(
        content_workflow,
        "read_content_material_review",
        lambda **_kwargs: SimpleNamespace(status="approved_current"),
    )
    approved = content_workflow._binding_aware_revision_workspace(
        resolved_snapshot=resolved,
        canonical_snapshot=canonical,
        revision_state="revision-state",
    )
    assert approved.can_review is True
    assert approved.latest_revision == blocked.latest_revision == revision


def test_normal_semantic_snapshot_recomputes_material_gate(
    monkeypatch,
) -> None:
    work_item_id = "content_work_item_material_review_normal"
    revision = _revision(official=False, source_material_ids=["rendered_material"])
    workspace = ContentDraftRevisionWorkspace.model_construct(
        latest_revision=revision,
        can_review=True,
        safe_next_step="Przejdź do review.",
    )
    planning = SimpleNamespace(
        proposal=SimpleNamespace(
            planning_digest="exact-plan",
            planning_input_digest="exact-input",
            service_card_id=None,
        )
    )
    snapshot = ContentWorkItemWorkflowSnapshotResponse.model_construct(
        preflight=SimpleNamespace(
            item=SimpleNamespace(
                id=work_item_id,
                wordpress_content_material_confidence="review_required",
            )
        ),
        planning_workspace=planning,
        draft_package=SimpleNamespace(
            draft_package_result=SimpleNamespace(draft_package=object())
        ),
        structured_generation=SimpleNamespace(
            structured_generation_result=SimpleNamespace(contract=object())
        ),
        revision_workspace=workspace,
    )
    revision_state = SimpleNamespace(latest_revision=None)
    monkeypatch.setattr(
        content_workflow,
        "content_workflow_store",
        lambda: SimpleNamespace(
            load_draft_revision_state=lambda _work_item_id: revision_state,
        ),
    )
    monkeypatch.setattr(
        content_workflow,
        "_snapshot_for_work_item_or_404",
        lambda _work_item_id: snapshot,
    )
    monkeypatch.setattr(
        content_workflow,
        "build_content_draft_revision_workspace",
        lambda **_kwargs: workspace,
    )
    monkeypatch.setattr(
        content_workflow,
        "read_content_material_review",
        lambda **_kwargs: SimpleNamespace(status="stale"),
    )

    blocked = content_workflow.semantic_review_snapshot_for_work_item_or_404(work_item_id)
    assert blocked.revision_workspace.can_review is False

    monkeypatch.setattr(
        content_workflow,
        "read_content_material_review",
        lambda **_kwargs: SimpleNamespace(status="approved_current"),
    )
    approved = content_workflow.semantic_review_snapshot_for_work_item_or_404(work_item_id)
    assert approved.revision_workspace.can_review is True
    assert approved.planning_workspace is snapshot.planning_workspace


def test_real_revision_workspace_preserves_section_map_gate_during_material_recheck(
    monkeypatch,
) -> None:
    work_item_id = "content_work_item_material_review_section_map"
    page_url = "https://www.ekologus.pl/wiedza/section-map-material/"
    draft_package = ContentDraftPackage(
        id="draft_package_section_map_material",
        work_item_id=work_item_id,
        brief_id="brief_section_map_material",
        claim_ledger_id="claim_ledger_section_map_material",
        title="Materiał sekcji",
        sections=[
            ContentDraftSection(
                heading="Zakres",
                purpose="Wyjaśnij zakres.",
                evidence_ids=["ev_material"],
            )
        ],
    )
    revision = ContentDraftRevision(
        schema_version="wilq_content_draft_revision_v1",
        revision_id="content_revision_section_map_material",
        work_item_id=work_item_id,
        revision_number=1,
        content_digest="a" * 64,
        draft_package_id=draft_package.id,
        draft_package_digest=content_draft_package_digest(draft_package),
        planning_digest="b" * 64,
        planning_input_digest="c" * 64,
        content_kind="editorial",
        document_kind="refresh_existing",
        final_canonical_url=page_url,
        title="Materiał sekcji",
        sections=[
            ContentDraftRevisionSection(
                heading="Zakres",
                body_markdown="Treść zakresu.",
                evidence_ids=["ev_material"],
                source_material_ids=["rendered_material"],
            )
        ],
        created_by="wilku",
        created_at=datetime(2026, 9, 20, tzinfo=UTC),
    )
    state = ContentDraftRevisionState(
        status="unreviewed",
        latest_revision=revision,
        revision_count=1,
    )
    item = ContentWorkItem(
        id=work_item_id,
        topic="Materiał sekcji",
        content_kind="editorial",
        source_public_url=page_url,
        intended_final_url=page_url,
        final_canonical_url=page_url,
        wordpress_content_material_confidence="review_required",
    )
    proposal = ContentPlanningProposal.model_construct(
        work_item_id=work_item_id,
        planning_digest="b" * 64,
        planning_input_digest="c" * 64,
        content_kind="editorial",
        service_card_id=None,
        final_canonical_url=page_url,
        sections=[SimpleNamespace(heading="Zakres")],
    )
    structured = SimpleNamespace(
        structured_generation_result=SimpleNamespace(contract=object())
    )
    canonical = SimpleNamespace(
        preflight=SimpleNamespace(item=item),
        planning_workspace=None,
        structured_generation=structured,
        revision_workspace=ContentDraftRevisionWorkspace.model_construct(
            latest_revision=revision,
            can_review=True,
        ),
    )
    resolved = SimpleNamespace(
        draft_package=SimpleNamespace(
            draft_package_result=SimpleNamespace(draft_package=draft_package)
        )
    )

    def workspace_for(section_map_current: bool) -> SimpleNamespace:
        planning = ContentPlanningWorkspace.model_construct(
            proposal=proposal,
            section_map_current=section_map_current,
            scope_current=False,
        )
        return SimpleNamespace(
            preflight=SimpleNamespace(item=item),
            planning_workspace=planning,
            structured_generation=structured,
            revision_workspace=canonical.revision_workspace,
        )

    monkeypatch.setattr(
        content_workflow,
        "content_workflow_store",
        lambda: object(),
    )
    monkeypatch.setattr(
        content_workflow,
        "read_content_material_review",
        lambda **_kwargs: SimpleNamespace(status="approved_current"),
    )

    not_current = content_workflow._binding_aware_revision_workspace(
        resolved_snapshot=resolved,
        canonical_snapshot=workspace_for(False),
        revision_state=state,
    )
    assert not_current.context_current is False
    assert not_current.can_review is False

    current = content_workflow._binding_aware_revision_workspace(
        resolved_snapshot=resolved,
        canonical_snapshot=workspace_for(True),
        revision_state=state,
    )
    assert current.context_current is True
    assert current.can_review is True

    monkeypatch.setattr(
        content_workflow,
        "read_content_material_review",
        lambda **_kwargs: SimpleNamespace(status="stale"),
    )
    material_blocked = content_workflow._binding_aware_revision_workspace(
        resolved_snapshot=resolved,
        canonical_snapshot=workspace_for(True),
        revision_state=state,
    )
    assert material_blocked.context_current is True
    assert material_blocked.can_review is False
