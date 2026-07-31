from __future__ import annotations

from typing import Literal

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
)


class ContentPlanningInputSummary(BaseModel):
    """Public, exact summary of the source set behind one planning input."""

    model_config = ConfigDict(extra="forbid")

    # Historical generated proposals did not carry a work-kind discriminator.
    # They are refresh-existing records by construction.
    goal: Literal["refresh_existing", "new_page"] = "refresh_existing"
    final_canonical_url: str | None = None
    proposed_ia_location: str | None = None
    service_label: str = Field(min_length=1)
    inventory_status: Literal["available", "missing", "not_applicable"]
    content_inventory_status: Literal["available", "missing", "not_applicable"]
    acf_section_inventory_status: Literal["available", "missing", "not_applicable"]
    source_assessments: list[ContentPlanningSourceAssessment] = Field(min_length=10)
    source_fact_count: int = Field(ge=0)
    source_fact_ids: list[str] = Field(default_factory=list)
    source_material_ids: list[str] = Field(default_factory=list)
    source_fact_previews: list[ContentPlanningSourceFact] = Field(default_factory=list)
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
        elif not self.final_canonical_url or not self.final_canonical_url.strip():
            raise ValueError("Refresh planning requires final_canonical_url.")
        elif self.inventory_status == "not_applicable":
            raise ValueError("Refresh planning requires existing-page inventory.")
        _validate_regulatory_summary(self)
        return self


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
