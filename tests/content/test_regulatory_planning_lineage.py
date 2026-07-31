from __future__ import annotations

from wilq.content.planning.dynamic_input import ContentPlanningInput, ContentPlanningInputSummary
from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningModelOutput,
    ContentPlanningModelSection,
    regulatory_response_lineage_errors,
)
from wilq.content.planning.proposal_lineage import regulatory_planning_lineage_errors
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryRequirement,
    ContentRegulatoryRequirementCoverage,
)
from wilq.content.workflow.planning import ContentPlanningProposal


def _planning_input() -> ContentPlanningInput:
    return ContentPlanningInput.model_construct(
        regulatory_coverage=ContentRegulatoryCoverage(
            profile_id="regulated_service",
            profile_version="2026-07",
            requirements=[
                ContentRegulatoryRequirement(
                    id="regulated_scope",
                    label="zakres obowiązku",
                    reason="Wymaga źródła urzędowego.",
                ),
                ContentRegulatoryRequirement(
                    id="regulated_deadline",
                    label="termin obowiązku",
                    reason="Wymaga źródła urzędowego.",
                ),
            ],
            requirement_coverage=[
                ContentRegulatoryRequirementCoverage(
                    requirement_id="regulated_scope",
                    source_fact_ids=["official_source"],
                    evidence_ids=["ev_scope"],
                ),
                ContentRegulatoryRequirementCoverage(
                    requirement_id="regulated_deadline",
                    source_fact_ids=["official_source"],
                    evidence_ids=["ev_deadline"],
                ),
            ],
        )
    )


def _output(*sections: ContentPlanningModelSection) -> ContentPlanningModelOutput:
    return ContentPlanningModelOutput.model_construct(sections=list(sections))


def _section(*, requirement_ids: list[str], evidence_ids: list[str]) -> ContentPlanningModelSection:
    return ContentPlanningModelSection.model_construct(
        heading="Obowiązki",
        regulatory_requirement_ids=requirement_ids,
        evidence_ids=evidence_ids,
    )


def test_regulatory_requirements_need_a_planned_section_with_exact_evidence() -> None:
    planning_input = _planning_input()

    missing = regulatory_planning_lineage_errors(
        planning_input,
        _output(_section(requirement_ids=["regulated_scope"], evidence_ids=["ev_scope"])),
    )
    wrong_evidence = regulatory_planning_lineage_errors(
        planning_input,
        _output(
            _section(
                requirement_ids=["regulated_scope", "regulated_deadline"],
                evidence_ids=["ev_scope"],
            )
        ),
    )
    complete = regulatory_planning_lineage_errors(
        planning_input,
        _output(
            _section(requirement_ids=["regulated_scope"], evidence_ids=["ev_scope"]),
            _section(requirement_ids=["regulated_deadline"], evidence_ids=["ev_deadline"]),
        ),
    )

    assert missing == ["regulatory_requirement:regulated_deadline"]
    assert wrong_evidence == ["regulatory_evidence:regulated_deadline"]
    assert complete == []


def test_public_response_lineage_rejects_missing_unknown_or_wrong_regulatory_evidence() -> None:
    summary = ContentPlanningInputSummary.model_construct(
        regulatory_profile_id="regulated_service",
        regulatory_requirement_ids=["regulated_scope"],
        regulatory_requirement_coverage=[
            ContentRegulatoryRequirementCoverage(
                requirement_id="regulated_scope",
                source_fact_ids=["official_source"],
                evidence_ids=["ev_scope"],
            )
        ],
    )
    proposal = ContentPlanningProposal.model_construct(
        sections=[
            _section(requirement_ids=["regulated_scope"], evidence_ids=["ev_wrong"]),
            _section(requirement_ids=["unknown_requirement"], evidence_ids=["ev_scope"]),
        ]
    )
    assert regulatory_response_lineage_errors(summary, proposal) == [
        "regulatory_requirement_unknown:unknown_requirement",
        "regulatory_evidence:regulated_scope",
    ]
