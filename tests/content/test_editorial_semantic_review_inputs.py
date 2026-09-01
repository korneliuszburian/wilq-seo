import json
from types import SimpleNamespace

import pytest

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.quality import semantic_review_service
from wilq.content.quality.semantic_review_contracts import ContentSemanticReviewRequest
from wilq.content.quality.semantic_review_guards import regulatory_quality_issues
from wilq.content.quality.semantic_review_service import _SemanticInputs
from wilq.content.quality.semantic_review_turn import semantic_review_turn_request
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)
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
    merged = json.loads(request.untrusted_context)["approved_planning_proposal"][
        "merged_away_sections"
    ]
    assert merged[0]["section_id"] == "merged_away"
    assert merged[0]["review_target"] == "whole_document"


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


def test_regulatory_guard_accepts_editor_child_section_subset() -> None:
    proposal = ContentPlanningProposal.model_construct(
        sections=[
            ContentPlanningSection(
                section_id="retained",
                heading="Zakres",
                purpose="Odpowiedz na pytanie.",
                inventory_disposition="rewrite",
                evidence_ids=["ev_source"],
            ),
            ContentPlanningSection(
                section_id="merged_away",
                heading="Monitoring",
                purpose="Odpowiedz na pytanie.",
                inventory_disposition="rewrite",
                regulatory_requirement_ids=[
                    "covered_requirement",
                    "monitoring_requirement",
                    "second_missing_requirement",
                ],
                evidence_ids=["ev_source", "ev_second"],
            ),
        ]
    )
    revision = ContentDraftRevision.model_construct(
        sections=[
            ContentDraftRevisionSection(
                section_id="retained",
                heading="Zakres i monitoring",
                body_markdown="Połączona treść dokumentacji instalacji.",
                evidence_ids=["ev_source", "ev_second"],
            )
        ]
    )
    planning_input = ContentPlanningInput.model_construct(
        regulatory_coverage=SimpleNamespace(
            source_facts=[
                SimpleNamespace(
                    source_id="fact_covered",
                    extracted_fact="połączona treść dokumentacji instalacji",
                ),
                SimpleNamespace(
                    source_id="fact_monitoring",
                    extracted_fact="wymagany monitoring gleby wód gruntowych instalacji",
                ),
                SimpleNamespace(
                    source_id="fact_second_missing",
                    extracted_fact="obowiązkowa analiza emisji hałasu przemysłowego",
                ),
            ],
            requirement_coverage=[
                SimpleNamespace(
                    requirement_id="covered_requirement",
                    source_fact_ids=["fact_covered"],
                    evidence_ids=["ev_source"],
                ),
                SimpleNamespace(
                    requirement_id="monitoring_requirement",
                    source_fact_ids=["fact_monitoring"],
                    evidence_ids=["ev_source"],
                ),
                SimpleNamespace(
                    requirement_id="second_missing_requirement",
                    source_fact_ids=["fact_second_missing"],
                    evidence_ids=["ev_second"],
                ),
            ],
        )
    )

    issues = regulatory_quality_issues(
        revision=revision,
        planning_input=planning_input,
        proposal=proposal,
    )
    credibility = next(
        issue for issue in issues if issue[0] == "credibility" and issue[1] == "whole_document"
    )
    assert "monitoring_requirement" in credibility[2]
    assert "second_missing_requirement" in credibility[2]
    assert credibility[3] == ["ev_source", "ev_second"]
