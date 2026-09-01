import json
from types import SimpleNamespace

import pytest

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality import semantic_review_service
from wilq.content.quality.semantic_review_contracts import ContentSemanticReviewRequest
from wilq.content.quality.semantic_review_service import _SemanticInputs
from wilq.content.quality.semantic_review_turn import semantic_review_turn_request
from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionSection,
)


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


def test_semantic_turn_filters_sections_merged_by_editor_child() -> None:
    proposal = ContentPlanningProposal.model_construct(
        sections=[
            {
                "section_id": "retained",
                "heading": "Zakres",
                "inventory_disposition": "rewrite",
                "query_terms": [],
                "evidence_ids": ["ev_source"],
                "regulatory_requirement_ids": [],
            },
            {
                "section_id": "merged_away",
                "heading": "Monitoring",
                "inventory_disposition": "rewrite",
                "query_terms": [],
                "evidence_ids": ["ev_source"],
                "regulatory_requirement_ids": [],
            },
        ]
    )
    revision = ContentDraftRevision.model_construct(
        work_item_id="work",
        revision_id="revision",
        content_digest="a" * 64,
        planning_input_digest="b" * 64,
        sections=[
            ContentDraftRevisionSection(
                section_id="retained",
                heading="Zakres i monitoring",
                body_markdown="Połączona treść.",
                evidence_ids=["ev_source"],
            )
        ],
    )

    request = semantic_review_turn_request(
        revision=revision,
        planning_input=ContentPlanningInput.model_construct(),
        proposal=proposal,
    )

    sections = json.loads(request.untrusted_context)["approved_planning_proposal"]["sections"]
    assert [section["section_id"] for section in sections] == ["retained"]


def test_semantic_turn_rejects_nonempty_plan_compacted_to_no_sections() -> None:
    proposal = ContentPlanningProposal.model_construct(
        sections=[
            {
                "section_id": "removed",
                "heading": "Usunięta sekcja",
                "inventory_disposition": "remove_review_required",
                "query_terms": [],
                "evidence_ids": [],
                "regulatory_requirement_ids": [],
            }
        ]
    )
    revision = ContentDraftRevision.model_construct(
        work_item_id="work",
        revision_id="revision",
        content_digest="a" * 64,
        planning_input_digest="b" * 64,
        sections=[
            ContentDraftRevisionSection(
                section_id="retained",
                heading="Bieżąca sekcja",
                body_markdown="Treść.",
                evidence_ids=["ev_source"],
            )
        ],
    )

    with pytest.raises(ValueError, match="do not bind exactly"):
        semantic_review_turn_request(
            revision=revision,
            planning_input=ContentPlanningInput.model_construct(),
            proposal=proposal,
        )
