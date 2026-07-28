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
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
    ContentDraftRevisionState,
)


class ContentNewPageDocumentOutlineSection(BaseModel):
    """A reviewed plan section, not generated document text."""

    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    heading: str = Field(min_length=1)
    purpose: str = Field(min_length=1)


class ContentNewPageDocumentReviewPrerequisiteConflict(BaseModel):
    """Typed blocker when a review route cannot resolve a document workspace yet."""

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_new_page_document_review_prerequisite_conflict"] = (
        "content_new_page_document_review_prerequisite_conflict"
    )
    contract_version: Literal["content_new_page_document_review_prerequisite_conflict_v1"] = (
        "content_new_page_document_review_prerequisite_conflict_v1"
    )
    status: Literal["blocked"] = "blocked"
    code: Literal["missing_planning_foundation"] = "missing_planning_foundation"
    brief_id: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)


class ContentNewPageCanonicalDocumentWorkspace(BaseModel):
    """Read-only bridge from one exact new-page plan to its future revision.

    The workspace deliberately contains no body text and no delivery identity.
    A later immutable revision is the only canonical document record.
    """

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_new_page_canonical_document"] = (
        "content_new_page_canonical_document"
    )
    contract_version: Literal["content_new_page_canonical_document_v2"] = (
        "content_new_page_canonical_document_v2"
    )
    status: Literal[
        "review_required",
        "ready_for_document",
        "document_review_required",
        "document_approved",
        "document_needs_changes",
        "document_rejected",
        "document_deferred",
        "blocked",
    ]
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
    document_status: Literal[
        "not_created", "unreviewed", "approved", "needs_changes", "rejected", "deferred"
    ] = "not_created"
    canonical_revision: ContentDraftRevision | None = None
    revision_review: ContentDraftRevisionReview | None = None
    assigned_source_material_ids: list[str] = Field(default_factory=list)
    assigned_knowledge_card_ids: list[str] = Field(default_factory=list)
    public_source_status: Literal["not_applicable"] = "not_applicable"
    public_source_url: None = None
    public_deployment_status: Literal["not_confirmed"] = "not_confirmed"
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_exact_document_lineage(self) -> ContentNewPageCanonicalDocumentWorkspace:
        _validate_plan_review(self)
        if self.canonical_revision is None:
            _validate_workspace_without_revision(self)
        else:
            _validate_workspace_with_revision(self)
        return self


def _validate_plan_review(workspace: ContentNewPageCanonicalDocumentWorkspace) -> None:
    review = workspace.plan_review
    if review is None:
        return
    if not (
        workspace.proposal_id is not None
        and workspace.planning_digest is not None
        and workspace.planning_input_digest is not None
        and review.work_item_id == workspace.work_item_id
        and review.stage == "scope"
        and review.planning_digest == workspace.planning_digest
        and review.service_card_id == workspace.service_card_id
    ):
        raise ValueError("Plan review does not match the exact new-page workspace.")


def _validate_workspace_without_revision(
    workspace: ContentNewPageCanonicalDocumentWorkspace,
) -> None:
    if (
        workspace.revision_review is not None
        or workspace.assigned_source_material_ids
        or workspace.assigned_knowledge_card_ids
        or workspace.document_status != "not_created"
    ):
        raise ValueError("Missing new-page revision cannot carry document lineage.")
    if workspace.status not in {"review_required", "ready_for_document", "blocked"}:
        raise ValueError("Document workspace status requires a canonical revision.")
    has_exact_plan_identity = all(
        value is not None
        for value in (
            workspace.proposal_id,
            workspace.planning_digest,
            workspace.planning_input_digest,
        )
    )
    if workspace.status == "blocked":
        if has_exact_plan_identity or workspace.plan_review is not None:
            raise ValueError("Blocked new-page workspace cannot carry a current plan.")
        return
    if not has_exact_plan_identity:
        raise ValueError("New-page plan state requires exact proposal identity.")
    expected_status = (
        "ready_for_document"
        if workspace.plan_review is not None and workspace.plan_review.decision == "approved"
        else "review_required"
    )
    if workspace.status != expected_status:
        raise ValueError("Workspace status must match the exact plan review state.")


def _validate_workspace_with_revision(
    workspace: ContentNewPageCanonicalDocumentWorkspace,
) -> None:
    revision = workspace.canonical_revision
    assert revision is not None
    identity = revision.new_page_document_identity
    if not (
        revision.document_kind == "new_page"
        and revision.final_canonical_url is None
        and identity is not None
        and revision.work_item_id == workspace.work_item_id
        and revision.planning_digest == workspace.planning_digest
        and revision.planning_input_digest == workspace.planning_input_digest
        and identity.brief_id == workspace.brief_id
        and identity.brief_digest == workspace.brief_digest
        and identity.foundation_id == workspace.foundation_id
        and identity.service_card_id == workspace.service_card_id
        and identity.service_card_digest == workspace.service_card_digest
        and identity.proposed_ia_location == workspace.proposed_ia_location
    ):
        raise ValueError("Canonical revision does not match the exact new-page workspace.")
    if (
        workspace.assigned_source_material_ids != revision.source_material_ids
        or workspace.assigned_knowledge_card_ids != revision.knowledge_card_ids
    ):
        raise ValueError("Workspace lineage must match the canonical new-page revision.")
    _validate_workspace_revision_review(workspace, revision)
    if workspace.plan_review is None or workspace.plan_review.decision != "approved":
        raise ValueError("Canonical new-page revision requires an approved exact plan review.")


def _validate_workspace_revision_review(
    workspace: ContentNewPageCanonicalDocumentWorkspace,
    revision: ContentDraftRevision,
) -> None:
    review = workspace.revision_review
    expected_document_status = "unreviewed" if review is None else review.decision
    if (
        workspace.document_status != expected_document_status
        or (
            review is not None
            and (
                review.revision_id != revision.revision_id
                or review.revision_digest != revision.content_digest
            )
        )
    ):
        raise ValueError("Workspace review must match the canonical revision and status.")
    if workspace.document_status == "not_created":
        raise ValueError("Canonical new-page revision requires a document status.")
    expected_workspace_status = {
        "unreviewed": "document_review_required",
        "approved": "document_approved",
        "needs_changes": "document_needs_changes",
        "rejected": "document_rejected",
        "deferred": "document_deferred",
    }[workspace.document_status]
    if workspace.status != expected_workspace_status:
        raise ValueError("Workspace status must match the canonical document status.")


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
    revision_state: ContentDraftRevisionState | None = None,
) -> ContentNewPageCanonicalDocumentWorkspace | None:
    """Project one exact plan; a missing or mismatched plan remains fail-closed."""

    if foundation is None:
        return None
    if proposal is None or not _proposal_matches_new_page(brief, foundation, proposal):
        return _blocked_workspace(brief, foundation)
    review = _scope_review_for(proposal, decisions)
    approved = review is not None and review.decision == "approved"
    revision = _current_revision(revision_state, brief, foundation, proposal)
    if (
        revision_state is not None
        and revision_state.latest_revision is not None
        and revision is None
    ):
        return _blocked_workspace(brief, foundation)
    document_status = "not_created" if revision is None else revision_state.status
    return ContentNewPageCanonicalDocumentWorkspace(
        status=_workspace_status(approved, document_status),
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
        document_status=document_status,
        canonical_revision=revision,
        revision_review=None if revision is None else revision_state.latest_review,
        assigned_source_material_ids=([] if revision is None else revision.source_material_ids),
        assigned_knowledge_card_ids=([] if revision is None else revision.knowledge_card_ids),
        safe_next_step=_next_step(approved, document_status),
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


def _current_revision(
    state: ContentDraftRevisionState | None,
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation,
    proposal: ContentPlanningProposal,
) -> ContentDraftRevision | None:
    revision = None if state is None else state.latest_revision
    identity = None if revision is None else revision.new_page_document_identity
    if revision is None:
        return None
    if not (
        revision.document_kind == "new_page"
        and revision.final_canonical_url is None
        and identity is not None
        and revision.planning_digest == proposal.planning_digest
        and revision.planning_input_digest == proposal.planning_input_digest
        and identity.work_item_id == foundation.work_item_id
        and identity.brief_id == brief.brief_id
        and identity.brief_digest == brief.brief_digest
        and identity.foundation_id == foundation.foundation_id
        and identity.service_card_id == foundation.service_card_id
        and identity.service_card_digest == foundation.service_card_digest
        and identity.proposed_ia_location == brief.proposed_ia_location
    ):
        return None
    return revision


def _workspace_status(
    plan_approved: bool,
    document_status: str,
) -> str:
    if document_status == "not_created":
        return "ready_for_document" if plan_approved else "review_required"
    return {
        "unreviewed": "document_review_required",
        "approved": "document_approved",
        "needs_changes": "document_needs_changes",
        "rejected": "document_rejected",
        "deferred": "document_deferred",
    }[document_status]


def _next_step(plan_approved: bool, document_status: str) -> str:
    if document_status == "not_created":
        return (
            "Przygotuj pierwszą immutable rewizję wyłącznie z tego zatwierdzonego planu."
            if plan_approved
            else "Sprawdź plan i zapisz decyzję człowieka przed przygotowaniem dokumentu."
        )
    if document_status == "unreviewed":
        return "Sprawdź dokładną rewizję dokumentu i zapisz decyzję człowieka."
    if document_status == "approved":
        return "Dokument ma dokładne review; delivery pozostaje osobnym, nieuruchomionym etapem."
    return "Sprawdź uwagi do rewizji przed przygotowaniem kolejnej immutable wersji."


__all__ = [
    "ContentNewPageCanonicalDocumentWorkspace",
    "ContentNewPageDocumentReviewPrerequisiteConflict",
    "ContentNewPageDocumentOutlineSection",
    "ContentNewPagePlanningReviewCommand",
    "build_new_page_canonical_document_workspace",
]
