from types import SimpleNamespace

import pytest

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality import semantic_review_service
from wilq.content.quality.semantic_review_contracts import ContentSemanticReviewRequest
from wilq.content.quality.semantic_review_service import _SemanticInputs
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevision


def test_semantic_inputs_allow_editorial_without_service_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    digest = "a" * 64
    revision = ContentDraftRevision.model_construct(
        schema_version="wilq_content_draft_revision_v2",
        revision_id="content_revision_editorial",
        content_digest="b" * 64,
        planning_digest=digest,
        planning_input_digest=digest,
    )
    proposal = ContentPlanningProposal.model_construct(
        content_kind="editorial",
        service_card_id=None,
        planning_digest=digest,
        planning_input_digest=digest,
    )
    planning_input = ContentPlanningInput.model_construct(planning_input_digest=digest)
    snapshot = SimpleNamespace(
        revision_workspace=SimpleNamespace(latest_revision=revision, context_current=True),
        planning_workspace=SimpleNamespace(proposal=proposal),
    )
    monkeypatch.setattr(
        semantic_review_service,
        "build_content_planning_input",
        lambda *_args, **_kwargs: SimpleNamespace(
            planning_input=planning_input,
            blockers=[],
        ),
    )

    result = semantic_review_service._prepare_inputs(
        snapshot,
        revision.revision_id,
        ContentSemanticReviewRequest(
            expected_revision_digest=revision.content_digest,
            requested_by="wilku",
        ),
        SimpleNamespace(write_ready=lambda: True),
    )

    assert isinstance(result, _SemanticInputs)
    assert result.proposal.content_kind == "editorial"
    assert result.proposal.service_card_id is None
