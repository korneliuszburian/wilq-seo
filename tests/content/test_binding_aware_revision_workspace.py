from types import SimpleNamespace

import apps.api.wilq_api.routers.content_workflow as content_workflow
from wilq.content.workflow.contracts.contracts import ContentDraftRevisionWorkspace
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionOfficialSourceReference,
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
