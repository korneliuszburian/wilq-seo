from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.workflow.new_page import (
    ContentNewPageBrief,
    ContentNewPagePlanningFoundation,
)
from wilq.content.workflow.planning import (
    ContentPlanningDecision,
    ContentPlanningProposal,
    ContentPlanningReviewRequest,
)


class ContentNewPageDocumentOutlineSection(BaseModel):
    """A reviewed plan section, not generated document text."""

    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    heading: str = Field(min_length=1)
    purpose: str = Field(min_length=1)


class ContentNewPageCanonicalDocumentWorkspace(BaseModel):
    """Read-only bridge from one exact new-page plan to its future revision.

    The workspace deliberately contains no body text and no delivery identity.
    A later immutable revision is the only canonical document record.
    """

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_new_page_canonical_document"] = (
        "content_new_page_canonical_document"
    )
    contract_version: Literal["content_new_page_canonical_document_v1"] = (
        "content_new_page_canonical_document_v1"
    )
    status: Literal["review_required", "ready_for_document", "blocked"]
    work_item_id: str = Field(min_length=1)
    brief_id: str = Field(min_length=1)
    brief_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    foundation_id: str = Field(min_length=1)
    service_card_id: str = Field(min_length=1)
    service_card_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    proposal_id: str | None = None
    planning_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    planning_input_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    plan_review: ContentPlanningDecision | None = None
    title: str = Field(min_length=1)
    proposed_ia_location: str = Field(min_length=3)
    outline: list[ContentNewPageDocumentOutlineSection] = Field(default_factory=list)
    document_status: Literal["not_created"] = "not_created"
    public_source_status: Literal["not_applicable"] = "not_applicable"
    public_source_url: None = None
    public_deployment_status: Literal["not_confirmed"] = "not_confirmed"
    safe_next_step: str = Field(min_length=1)


class ContentNewPagePlanningReviewCommand(BaseModel):
    """Human scope approval tied to one generated new-page proposal."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    expected_proposal_id: str = Field(min_length=1)
    expected_planning_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_planning_input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: Literal["approved", "needs_changes"]
    reviewed_by: str = Field(min_length=1, max_length=160)
    checked_items: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=2_000)

    @model_validator(mode="after")
    def require_human_review_basis(self) -> ContentNewPagePlanningReviewCommand:
        if self.decision == "approved" and not self.checked_items:
            raise ValueError("Planning approval requires checked items.")
        if self.decision == "needs_changes" and not self.notes:
            raise ValueError("Planning changes require an operator note.")
        return self

    def as_planning_review_request(self, service_card_id: str) -> ContentPlanningReviewRequest:
        return ContentPlanningReviewRequest(
            stage="scope",
            expected_planning_digest=self.expected_planning_digest,
            service_card_id=service_card_id,
            decision=self.decision,
            reviewed_by=self.reviewed_by,
            checked_items=self.checked_items,
            notes=self.notes,
        )


def build_new_page_canonical_document_workspace(
    *,
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation | None,
    proposal: ContentPlanningProposal | None,
    decisions: list[ContentPlanningDecision],
) -> ContentNewPageCanonicalDocumentWorkspace | None:
    """Project one exact plan; a missing or mismatched plan remains fail-closed."""

    if foundation is None:
        return None
    if proposal is None or not _proposal_matches_new_page(brief, foundation, proposal):
        return _blocked_workspace(brief, foundation)
    review = _scope_review_for(proposal, decisions)
    approved = review is not None and review.decision == "approved"
    return ContentNewPageCanonicalDocumentWorkspace(
        status="ready_for_document" if approved else "review_required",
        work_item_id=foundation.work_item_id,
        brief_id=brief.brief_id,
        brief_digest=brief.brief_digest,
        foundation_id=foundation.foundation_id,
        service_card_id=foundation.service_card_id,
        service_card_digest=foundation.service_card_digest,
        proposal_id=proposal.proposal_id,
        planning_digest=proposal.planning_digest,
        planning_input_digest=proposal.planning_input_digest,
        plan_review=review,
        title=brief.title,
        proposed_ia_location=brief.proposed_ia_location,
        outline=[
            ContentNewPageDocumentOutlineSection(
                section_id=section.section_id,
                heading=section.heading,
                purpose=section.purpose,
            )
            for section in proposal.sections
        ],
        safe_next_step=(
            "Przygotuj pierwszą immutable rewizję wyłącznie z tego zatwierdzonego planu."
            if approved
            else "Sprawdź plan i zapisz decyzję człowieka przed przygotowaniem dokumentu."
        ),
    )


def _blocked_workspace(
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation,
) -> ContentNewPageCanonicalDocumentWorkspace:
    return ContentNewPageCanonicalDocumentWorkspace(
        status="blocked",
        work_item_id=foundation.work_item_id,
        brief_id=brief.brief_id,
        brief_digest=brief.brief_digest,
        foundation_id=foundation.foundation_id,
        service_card_id=foundation.service_card_id,
        service_card_digest=foundation.service_card_digest,
        title=brief.title,
        proposed_ia_location=brief.proposed_ia_location,
        safe_next_step=(
            "Wygeneruj aktualny plan związany z tym briefem i foundation przed "
            "przygotowaniem dokumentu."
        ),
    )


def _proposal_matches_new_page(
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation,
    proposal: ContentPlanningProposal,
) -> bool:
    identity = proposal.new_page_document_identity
    return bool(
        proposal.goal == "new_page"
        and proposal.generation_status == "codex_generated"
        and proposal.proposal_id
        and proposal.planning_input_digest
        and identity is not None
        and proposal.work_item_id == foundation.work_item_id
        and identity.work_item_id == foundation.work_item_id
        and identity.brief_id == brief.brief_id
        and identity.brief_digest == brief.brief_digest
        and identity.foundation_id == foundation.foundation_id
        and identity.service_card_id == foundation.service_card_id
        and identity.service_card_digest == foundation.service_card_digest
        and proposal.proposed_ia_location == brief.proposed_ia_location
        and identity.proposed_ia_location == brief.proposed_ia_location
    )


def _scope_review_for(
    proposal: ContentPlanningProposal,
    decisions: list[ContentPlanningDecision],
) -> ContentPlanningDecision | None:
    return next(
        (
            decision
            for decision in decisions
            if decision.stage == "scope"
            and decision.planning_digest == proposal.planning_digest
            and decision.service_card_id == proposal.service_card_id
        ),
        None,
    )


__all__ = [
    "ContentNewPageCanonicalDocumentWorkspace",
    "ContentNewPageDocumentOutlineSection",
    "ContentNewPagePlanningReviewCommand",
    "build_new_page_canonical_document_workspace",
]
