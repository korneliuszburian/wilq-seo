from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.measurement.aggregates import MeasurementPeriodComparison
from wilq.content.planning.input_sources import (
    ContentPlanningSourceAssessment,
    ContentPlanningSourceFact,
    validate_source_assessment_membership,
)
from wilq.content.regulatory.policy import (
    ContentRegulatoryRequirement,
    ContentRegulatoryRequirementCoverage,
    ContentRegulatoryReviewCandidate,
    regulatory_review_candidates,
)
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandRow


class ContentPlanningInputSummary(BaseModel):
    """Public, exact summary of the source set behind one planning input."""

    model_config = ConfigDict(extra="forbid")

    # Historical generated proposals did not carry a work-kind discriminator.
    # They are refresh-existing records by construction.
    goal: Literal["refresh_existing", "new_page"] = "refresh_existing"
    final_canonical_url: str | None = None
    proposed_ia_location: str | None = None
    content_kind: Literal["service", "editorial"] = "service"
    service_label: str | None = None
    inventory_status: Literal["available", "missing", "not_applicable"]
    content_inventory_status: Literal["available", "missing", "not_applicable"]
    acf_section_inventory_status: Literal["available", "missing", "not_applicable"]
    source_assessments: list[ContentPlanningSourceAssessment] = Field(min_length=10)
    source_fact_count: int = Field(ge=0)
    source_fact_ids: list[str] = Field(default_factory=list)
    source_material_ids: list[str] = Field(default_factory=list)
    source_fact_previews: list[ContentPlanningSourceFact] = Field(default_factory=list)
    gsc_query_rows: list[ContentSearchDemandRow] = Field(default_factory=list)
    regulatory_profile_id: str | None = None
    regulatory_profile_version: str | None = None
    regulatory_requirements: list[ContentRegulatoryRequirement] = Field(default_factory=list)
    regulatory_requirement_ids: list[str] = Field(default_factory=list)
    regulatory_source_fact_ids: list[str] = Field(default_factory=list)
    regulatory_requirement_coverage: list[ContentRegulatoryRequirementCoverage] = Field(
        default_factory=list
    )
    regulatory_review_candidates: list[ContentRegulatoryReviewCandidate] = Field(
        default_factory=list
    )
    evidence_id_count: int = Field(ge=0)
    knowledge_card_count: int = Field(ge=0)
    measurement_metrics: list[str] = Field(default_factory=list)
    metric_comparisons: list[MeasurementPeriodComparison] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_complete_source_assessments(self) -> ContentPlanningInputSummary:
        validate_source_assessment_membership(self.source_assessments)
        if self.content_kind == "service" and not self.service_label:
            raise ValueError("Service planning summary requires a service label.")
        if self.content_kind == "editorial" and self.service_label is not None:
            raise ValueError("Editorial planning summary cannot carry a service label.")
        if self.goal == "new_page":
            if self.final_canonical_url is not None:
                raise ValueError("New-page planning cannot claim a public canonical URL.")
            if (
                self.proposed_ia_location is None
                or len(self.proposed_ia_location.strip()) < 3
            ):
                raise ValueError("New-page planning requires an IA location.")
            if any(
                status != "not_applicable"
                for status in (
                    self.inventory_status,
                    self.content_inventory_status,
                    self.acf_section_inventory_status,
                )
            ):
                raise ValueError("New-page planning cannot carry existing-page inventory.")
            if self.metric_comparisons:
                raise ValueError("New-page planning cannot carry page metric comparisons.")
            if self.gsc_query_rows:
                raise ValueError("New-page planning cannot carry historic GSC query rows.")
        elif not self.final_canonical_url or not self.final_canonical_url.strip():
            raise ValueError("Refresh planning requires final_canonical_url.")
        elif self.inventory_status == "not_applicable":
            raise ValueError("Refresh planning requires existing-page inventory.")
        _validate_regulatory_summary(self)
        return self


def content_planning_input_summary(planning_input: Any) -> ContentPlanningInputSummary:
    return ContentPlanningInputSummary(
        goal=planning_input.goal,
        final_canonical_url=planning_input.final_canonical_url,
        proposed_ia_location=planning_input.proposed_ia_location,
        content_kind=planning_input.content_kind,
        service_label=planning_input.service_label,
        inventory_status=planning_input.inventory.status,
        content_inventory_status=planning_input.inventory.content_status,
        acf_section_inventory_status=planning_input.inventory.acf_section_status,
        source_assessments=planning_input.source_assessments,
        source_fact_count=len(planning_input.source_facts),
        source_fact_ids=sorted(
            source_fact_id
            for fact in planning_input.source_facts
            for source_fact_id in fact.source_fact_ids
        ),
        source_material_ids=sorted(
            source_material_id
            for fact in planning_input.source_facts
            for source_material_id in fact.source_material_ids
        ),
        source_fact_previews=list(planning_input.source_facts),
        gsc_query_rows=list(planning_input.query_portfolio.gsc_query_rows),
        regulatory_profile_id=planning_input.regulatory_coverage.profile_id,
        regulatory_profile_version=planning_input.regulatory_coverage.profile_version,
        regulatory_requirements=planning_input.regulatory_coverage.requirements,
        regulatory_requirement_ids=[
            requirement.id for requirement in planning_input.regulatory_coverage.requirements
        ],
        regulatory_source_fact_ids=planning_input.regulatory_coverage.source_fact_ids,
        regulatory_requirement_coverage=planning_input.regulatory_coverage.requirement_coverage,
        regulatory_review_candidates=(
            []
            if planning_input.confirmed_service_card_id is None
            else regulatory_review_candidates(
                service_card_id=planning_input.confirmed_service_card_id,
                coverage=planning_input.regulatory_coverage,
            )
        ),
        evidence_id_count=len(planning_input.evidence_ids),
        knowledge_card_count=len(planning_input.knowledge_card_ids),
        measurement_metrics=planning_input.measurement_metrics,
        metric_comparisons=planning_input.metric_comparisons,
    )


__all__ = ["ContentPlanningInputSummary", "content_planning_input_summary"]


def _validate_regulatory_summary(summary: ContentPlanningInputSummary) -> None:
    profile_bound = (
        summary.regulatory_profile_id is not None
        or summary.regulatory_profile_version is not None
    )
    if profile_bound:
        if not summary.regulatory_profile_id or not summary.regulatory_profile_version:
            raise ValueError("Regulatory planning summary requires exact profile identity.")
        required_ids = set(summary.regulatory_requirement_ids)
        requirements_by_id = {
            requirement.id: requirement for requirement in summary.regulatory_requirements
        }
        if (
            "regulatory_requirements" in summary.model_fields_set
            and set(requirements_by_id) != required_ids
        ):
            raise ValueError(
                "Regulatory planning summary requires exact requirement definitions."
            )
        coverage_by_requirement = {
            item.requirement_id: item for item in summary.regulatory_requirement_coverage
        }
        if not required_ids or set(coverage_by_requirement) != required_ids:
            raise ValueError(
                "Regulatory planning summary requires exact coverage for every requirement."
            )
        covered_fact_ids = {
            source_fact_id
            for item in coverage_by_requirement.values()
            for source_fact_id in item.source_fact_ids
        }
        if covered_fact_ids != set(summary.regulatory_source_fact_ids):
            raise ValueError("Regulatory planning summary requires exact covered source-fact IDs.")
    elif (
        summary.regulatory_requirement_ids
        or summary.regulatory_requirements
        or summary.regulatory_source_fact_ids
        or summary.regulatory_requirement_coverage
        or summary.regulatory_review_candidates
    ):
        raise ValueError("Unprofiled planning summary cannot carry regulatory coverage.")
