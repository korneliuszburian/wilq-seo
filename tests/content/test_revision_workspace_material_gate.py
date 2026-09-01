from wilq.content.workflow.contracts.contracts import ContentDraftRevisionWorkspace
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionOfficialSourceReference,
)
from wilq.content.workflow.pipeline_steps.snapshot_assembly import _gate_revision_workspace


def test_rendered_wordpress_material_blocks_unlineaged_revision_review() -> None:
    workspace = ContentDraftRevisionWorkspace.model_construct(
        latest_revision=ContentDraftRevision.model_construct(official_source_references=[]),
        can_review=True,
        safe_next_step="Przejdź do review.",
    )

    gated = _gate_revision_workspace(
        workspace,
        planning_workspace=None,
        material_confidence="review_required",
    )

    assert gated.can_review is False
    assert "źródłowy materiał WordPress" in gated.safe_next_step


def test_officially_lineaged_revision_can_review_despite_rendered_wordpress_material() -> None:
    workspace = ContentDraftRevisionWorkspace.model_construct(
        latest_revision=ContentDraftRevision.model_construct(
            official_source_references=[
                ContentDraftRevisionOfficialSourceReference.model_construct(
                    source_fact_id="regulatory_source_fact_reach",
                    source_url="https://www.gov.pl/web/chemikalia/clp",
                    source_title="Biuro do spraw Substancji Chemicznych: CLP",
                    verified_on="2026-09-01",
                    evidence_ids=["ev_regulatory_source_review_reach"],
                    regulatory_requirement_ids=["reach_clp_distinct_scope"],
                )
            ]
        ),
        can_review=True,
        safe_next_step="Przejdź do review.",
    )

    gated = _gate_revision_workspace(
        workspace,
        planning_workspace=None,
        material_confidence="review_required",
    )

    assert gated.can_review is True
    assert gated.safe_next_step == "Przejdź do review."
