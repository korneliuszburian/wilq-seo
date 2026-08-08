from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.planning.dynamic_input import (
    ContentPlanningInputBlockerCode,
    ContentPlanningInputSummary,
)
from wilq.content.regulatory.policy import regulatory_requirement_assertion_errors
from wilq.content.workflow.planning import (
    ContentPlanningConditionalHypothesis,
    ContentPlanningCtaBlock,
    ContentPlanningFaqItem,
    ContentPlanningInternalLink,
    ContentPlanningInventoryDisposition,
    ContentPlanningMeasurementPlan,
    ContentPlanningPageAssets,
    ContentPlanningProposal,
    ContentPlanningWorkspace,
)

ContentPlanningProposalStatus = Literal[
    "not_generated",
    "generating",
    "created",
    "idempotent",
    "ready",
    "stale",
    "blocked",
    "failed",
]
ContentPlanningProposalBlockerCode = Literal[
    ContentPlanningInputBlockerCode,
    "stale_input",
    "runtime_blocked",
    "runtime_failed",
    "generation_claim_stale",
    "invalid_structured_output",
    "quality_gate_failed",
    "lineage_mismatch",
    "persistence_failed",
    "scope_not_current",
]


def regulatory_response_lineage_errors(
    input_summary: ContentPlanningInputSummary,
    proposal: ContentPlanningProposal,
) -> list[str]:
    """Validate persisted/public regulatory lineage, not only model output."""

    if input_summary.regulatory_profile_id is None:
        return []
    coverage = {
        item.requirement_id: set(item.evidence_ids)
        for item in input_summary.regulatory_requirement_coverage
    }
    required_ids = set(input_summary.regulatory_requirement_ids)
    section_requirement_ids = {
        requirement_id
        for section in proposal.sections
        for requirement_id in section.regulatory_requirement_ids
    }
    errors = [
        f"regulatory_requirement_unknown:{requirement_id}"
        for requirement_id in sorted(section_requirement_ids - required_ids)
    ]
    for requirement_id in sorted(required_ids):
        matching_sections = [
            section
            for section in proposal.sections
            if requirement_id in section.regulatory_requirement_ids
        ]
        if not matching_sections:
            errors.append(f"regulatory_requirement:{requirement_id}")
        elif not any(
            set(section.evidence_ids).intersection(coverage[requirement_id])
            for section in matching_sections
        ):
            errors.append(f"regulatory_evidence:{requirement_id}")
        requirement = next(
            (
                item
                for item in input_summary.regulatory_requirements
                if item.id == requirement_id
            ),
            None,
        )
        if requirement is not None:
            text = "\n".join(
                "\n".join((section.heading, section.purpose, section.reader_question))
                for section in matching_sections
            )
            errors.extend(
                regulatory_requirement_assertion_errors(
                    requirement=requirement,
                    text=text,
                )
            )
    return errors


class ContentPlanningProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_card_id: str = Field(min_length=1)
    expected_planning_input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    operator_hint: str = Field(default="", max_length=500)
    requested_by: str = Field(min_length=1)
    regenerate_stale_mapping: bool = False
    regenerate_after_review: bool = False

    @model_validator(mode="after")
    def strip_visible_text(self) -> ContentPlanningProposalRequest:
        self.operator_hint = self.operator_hint.strip()
        self.requested_by = self.requested_by.strip()
        if not self.requested_by:
            raise ValueError("Planning generation requires requester attribution.")
        if self.regenerate_after_review and not self.operator_hint:
            raise ValueError(
                "Planning regeneration after review requires a visible repair instruction."
            )
        return self


class ContentPlanningProposalBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ContentPlanningProposalBlockerCode
    label: str
    reason: str
    next_step: str
    source_codes: list[str] = Field(default_factory=list)


class ContentPlanningModelSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    reader_question: str = Field(min_length=1)
    inventory_disposition: ContentPlanningInventoryDisposition
    # Stable server-assigned inventory identity.  The heading is presentation;
    # this ID is the authoritative link to the WordPress/ACF/the_content row.
    inventory_section_id: str | None = None
    inventory_heading: str | None = None
    query_terms: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(min_length=1)
    claim_ids: list[str] = Field(default_factory=list)
    regulatory_requirement_ids: list[str] = Field(default_factory=list)


class ContentPlanningModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: Literal["pl-PL"] = "pl-PL"
    service_card_id: str = Field(min_length=1)
    target_reader: str = Field(min_length=1)
    buyer_problem: str = Field(min_length=1)
    buyer_trigger: str = Field(min_length=1)
    search_intent: str = Field(min_length=1)
    angle: str = Field(min_length=1)
    value_proposition: str = Field(min_length=1)
    page_assets: ContentPlanningPageAssets
    sections: list[ContentPlanningModelSection] = Field(min_length=1, max_length=12)
    faq: list[ContentPlanningFaqItem] = Field(default_factory=list, max_length=8)
    cta_blocks: list[ContentPlanningCtaBlock] = Field(default_factory=list, max_length=4)
    internal_links: list[ContentPlanningInternalLink] = Field(default_factory=list)
    conditional_hypotheses: list[ContentPlanningConditionalHypothesis] = Field(
        default_factory=list, max_length=4
    )
    measurement_plan: ContentPlanningMeasurementPlan
    publish_ready: Literal[False] = False

    @model_validator(mode="after")
    def require_unique_section_headings(self) -> ContentPlanningModelOutput:
        headings = [section.heading.strip() for section in self.sections]
        if len(headings) != len(set(headings)):
            raise ValueError("Planning output section headings must be unique.")
        allowed_placements = {"after_lead", "after_content", *headings}
        placements = [item.placement for item in self.cta_blocks]
        placements.extend(item.placement for item in self.internal_links)
        if not set(placements).issubset(allowed_placements):
            raise ValueError(
                "CTA and internal-link placement must name after_lead, "
                "after_content, or an exact planned section heading."
            )
        removed_section_headings = {
            section.heading
            for section in self.sections
            if section.inventory_disposition == "remove_review_required"
        }
        if removed_section_headings.intersection(placements):
            raise ValueError(
                "CTA and internal-link placement cannot target a section marked "
                "remove_review_required."
            )
        page_assets = self.page_assets.model_dump()
        if any(not str(value).strip() for value in page_assets.values()):
            raise ValueError("Planning output requires every page asset.")
        if any(not item.evidence_ids for item in self.faq):
            raise ValueError("Every FAQ item requires evidence lineage.")
        if any(not item.evidence_ids for item in self.cta_blocks):
            raise ValueError("Every CTA block requires evidence lineage.")
        if any(not item.evidence_ids for item in self.internal_links):
            raise ValueError("Every internal link requires evidence lineage.")
        link_targets = [item.target_url for item in self.internal_links]
        if len(link_targets) != len(set(link_targets)):
            raise ValueError("Planning output internal-link targets must be unique.")
        if not self.measurement_plan.observation_rule.strip():
            raise ValueError("Planning output requires an observation rule.")
        if not self.measurement_plan.success_claim_rule.strip():
            raise ValueError("Planning output requires a success-claim rule.")
        return self


class ContentPlanningProposalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ContentPlanningProposalStatus
    work_item_id: str = Field(min_length=1)
    service_card_id: str | None = None
    planning_input_digest: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    input_summary: ContentPlanningInputSummary | None = None
    retry_after_seconds: int | None = Field(default=None, ge=0)
    proposal: ContentPlanningProposal | None = None
    planning_workspace: ContentPlanningWorkspace | None = None
    runtime: ContentCodexRuntimeTrace = Field(
        default_factory=lambda: ContentCodexRuntimeTrace(status="not_started")
    )
    blockers: list[ContentPlanningProposalBlocker] = Field(default_factory=list)
    safe_next_step: str
    publish_ready: Literal[False] = False

    @model_validator(mode="after")
    def require_status_payload(self) -> ContentPlanningProposalResponse:
        if (
            self.planning_input_digest is not None
            and self.input_summary is None
            and self.status != "generating"
        ):
            raise ValueError("Planning input digest requires its exact input summary.")
        if self.status in {"created", "idempotent", "ready"}:
            if self.proposal is None or self.blockers:
                raise ValueError("Ready planning response requires a proposal without blockers.")
        elif self.status == "not_generated":
            if self.proposal is not None or self.blockers:
                raise ValueError("Not-generated response cannot expose proposal or blockers.")
        elif self.status == "generating":
            if self.proposal is not None or self.blockers:
                raise ValueError("Generating response cannot expose proposal or blockers.")
        elif not self.blockers:
            raise ValueError("Non-ready planning response requires typed blockers.")
        if self.proposal is not None and (
            self.proposal.work_item_id != self.work_item_id
            or self.proposal.service_card_id != self.service_card_id
            or self.proposal.planning_input_digest != self.planning_input_digest
        ):
            raise ValueError("Planning response must match the nested exact proposal.")
        if (
            self.status in {"created", "idempotent", "ready"}
            and self.proposal is not None
            and self.input_summary is not None
        ):
            lineage_errors = regulatory_response_lineage_errors(self.input_summary, self.proposal)
            if lineage_errors:
                raise ValueError(
                    "Planning response has invalid regulatory lineage: " + ", ".join(lineage_errors)
                )
        if self.planning_workspace is not None:
            if self.status != "ready" or self.proposal is None:
                raise ValueError("Planning workspace is available only for a ready proposal.")
            if self.planning_workspace.proposal != self.proposal:
                raise ValueError("Planning workspace must carry the response exact proposal.")
        return self


__all__ = [
    "ContentPlanningModelOutput",
    "ContentPlanningModelSection",
    "ContentPlanningProposalBlocker",
    "ContentPlanningProposalRequest",
    "ContentPlanningProposalResponse",
    "regulatory_response_lineage_errors",
]
