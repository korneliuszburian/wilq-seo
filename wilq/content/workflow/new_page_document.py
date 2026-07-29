from __future__ import annotations

from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.workflow.document_lineage import (
    ContentDocumentWorkspaceDocumentLineage,
    build_content_document_lineage,
)
from wilq.content.workflow.new_page import (
    ContentNewPageBrief,
    ContentNewPagePlanningFoundation,
)
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
    ContentDraftRevisionState,
)


class ContentNewPageDocumentOutlineSection(BaseModel):
    """A generated-plan section, not generated document text."""

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
    contract_version: Literal["content_new_page_canonical_document_v3"] = (
        "content_new_page_canonical_document_v3"
    )
    status: Literal[
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
    proposal_id: str | None = Field(default=None, min_length=1)
    planning_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    planning_input_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
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
    document_lineage: ContentDocumentWorkspaceDocumentLineage = Field(
        default_factory=lambda: build_content_document_lineage(None)
    )
    public_source_status: Literal["not_applicable"] = "not_applicable"
    public_source_url: None = None
    public_deployment_status: Literal["not_confirmed"] = "not_confirmed"
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_exact_document_lineage(self) -> ContentNewPageCanonicalDocumentWorkspace:
        if self.canonical_revision is None:
            _validate_workspace_without_revision(self)
        else:
            _validate_workspace_with_revision(self)
        return self

    @field_validator("proposal_id")
    @classmethod
    def require_nonblank_proposal_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        proposal_id = value.strip()
        if not proposal_id:
            raise ValueError("Proposal ID must not be blank.")
        return proposal_id


def _has_exact_plan_identity(workspace: ContentNewPageCanonicalDocumentWorkspace) -> bool:
    return bool(
        workspace.proposal_id
        and workspace.planning_digest
        and workspace.planning_input_digest
    )


def _validate_workspace_without_revision(
    workspace: ContentNewPageCanonicalDocumentWorkspace,
) -> None:
    if (
        workspace.revision_review is not None
        or workspace.assigned_source_material_ids
        or workspace.assigned_knowledge_card_ids
        or workspace.document_status != "not_created"
        or workspace.document_lineage.status != "not_recorded"
        or workspace.document_lineage.source_material_ids
        or workspace.document_lineage.knowledge_cards
        or workspace.document_lineage.unresolved_knowledge_card_ids
    ):
        raise ValueError("Missing new-page revision cannot carry document lineage.")
    if workspace.status not in {"ready_for_document", "blocked"}:
        raise ValueError("Document workspace status requires a canonical revision.")
    has_exact_plan_identity = _has_exact_plan_identity(workspace)
    if workspace.status == "blocked":
        if (
            workspace.proposal_id is not None
            or workspace.planning_digest is not None
            or workspace.planning_input_digest is not None
        ):
            raise ValueError("Blocked new-page workspace cannot carry a current plan.")
        return
    if not has_exact_plan_identity:
        raise ValueError("New-page plan state requires exact proposal identity.")
    if workspace.status != "ready_for_document":
        raise ValueError("Generated new-page plan must be ready for its first document.")


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
    _validate_workspace_document_lineage(workspace, revision)
    _validate_workspace_revision_review(workspace, revision)


def _validate_workspace_document_lineage(
    workspace: ContentNewPageCanonicalDocumentWorkspace,
    revision: ContentDraftRevision,
) -> None:
    lineage = workspace.document_lineage
    expected_lineage = build_content_document_lineage(revision)
    if lineage != expected_lineage:
        raise ValueError("Document lineage must match the canonical revision.")


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
    expected_workspace_status = {
        "unreviewed": "document_review_required",
        "approved": "document_approved",
        "needs_changes": "document_needs_changes",
        "rejected": "document_rejected",
        "deferred": "document_deferred",
    }[workspace.document_status]
    if workspace.status != expected_workspace_status:
        raise ValueError("Workspace status must match the canonical document status.")


def build_new_page_canonical_document_workspace(
    *,
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation | None,
    proposal: ContentPlanningProposal | None,
    revision_state: ContentDraftRevisionState | None = None,
) -> ContentNewPageCanonicalDocumentWorkspace | None:
    """Project one exact plan; a missing or mismatched plan remains fail-closed."""

    if foundation is None:
        return None
    if proposal is None or not _proposal_matches_new_page(brief, foundation, proposal):
        return _blocked_workspace(brief, foundation)
    revision = _current_revision(revision_state, brief, foundation, proposal)
    if (
        revision_state is not None
        and revision_state.latest_revision is not None
        and revision is None
    ):
        return _blocked_workspace(brief, foundation)
    if revision is None:
        document_status: Literal[
            "not_created", "unreviewed", "approved", "needs_changes", "rejected", "deferred"
        ] = "not_created"
        revision_review = None
    else:
        if revision_state is None or revision_state.status == "empty":
            return _blocked_workspace(brief, foundation)
        document_status = revision_state.status
        revision_review = revision_state.latest_review
    return ContentNewPageCanonicalDocumentWorkspace(
        status=_workspace_status(document_status),
        work_item_id=foundation.work_item_id,
        brief_id=brief.brief_id,
        brief_digest=brief.brief_digest,
        foundation_id=foundation.foundation_id,
        service_card_id=foundation.service_card_id,
        service_card_digest=foundation.service_card_digest,
        proposal_id=proposal.proposal_id,
        planning_digest=proposal.planning_digest,
        planning_input_digest=proposal.planning_input_digest,
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
        revision_review=revision_review,
        assigned_source_material_ids=([] if revision is None else revision.source_material_ids),
        assigned_knowledge_card_ids=([] if revision is None else revision.knowledge_card_ids),
        document_lineage=build_content_document_lineage(revision),
        safe_next_step=_next_step(document_status),
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
    document_status: Literal[
        "not_created", "unreviewed", "approved", "needs_changes", "rejected", "deferred"
    ],
) -> Literal[
    "ready_for_document",
    "document_review_required",
    "document_approved",
    "document_needs_changes",
    "document_rejected",
    "document_deferred",
]:
    if document_status == "not_created":
        return "ready_for_document"
    return cast(
        Literal[
            "ready_for_document",
            "document_review_required",
            "document_approved",
            "document_needs_changes",
            "document_rejected",
            "document_deferred",
        ],
        {
        "unreviewed": "document_review_required",
        "approved": "document_approved",
        "needs_changes": "document_needs_changes",
        "rejected": "document_rejected",
        "deferred": "document_deferred",
        }[document_status],
    )


def _next_step(document_status: str) -> str:
    if document_status == "not_created":
        return "Przygotuj pierwszą immutable rewizję wyłącznie z tego wygenerowanego planu."
    if document_status == "unreviewed":
        return "Sprawdź dokładną rewizję dokumentu i zapisz decyzję człowieka."
    if document_status == "approved":
        return "Dokument ma dokładne review; delivery pozostaje osobnym, nieuruchomionym etapem."
    return "Sprawdź uwagi do rewizji przed przygotowaniem kolejnej immutable wersji."


class ContentNewPageDeliveryReadiness(BaseModel):
    """Read-only gate before a new-page ActionObject can be created.

    The gate deliberately records only observed authoring capabilities and the
    exact approved revision. It neither selects a content type nor touches a
    WordPress adapter.
    """

    model_config = ConfigDict(extra="forbid")

    response_type: Literal["content_new_page_delivery_readiness"] = (
        "content_new_page_delivery_readiness"
    )
    contract_version: Literal["content_new_page_delivery_readiness_v1"] = (
        "content_new_page_delivery_readiness_v1"
    )
    status: Literal["ready_for_action", "blocked"]
    work_item_id: str = Field(min_length=1)
    brief_id: str = Field(min_length=1)
    brief_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    foundation_id: str = Field(min_length=1)
    service_card_id: str = Field(min_length=1)
    service_card_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    revision_id: str | None = None
    revision_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    allowed_content_types: list[Literal["page", "post"]] = Field(default_factory=list)
    authoring_profile_digest: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    evidence_ids: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_exact_ready_action(self) -> ContentNewPageDeliveryReadiness:
        if self.status == "ready_for_action":
            if not (
                self.revision_id
                and self.revision_digest
                and self.allowed_content_types
                and self.authoring_profile_digest
                and self.evidence_ids
            ):
                raise ValueError("Ready new-page delivery requires exact revision and capability.")
            if self.blockers:
                raise ValueError("Ready new-page delivery cannot carry blockers.")
        elif self.revision_id is not None or self.revision_digest is not None:
            raise ValueError("Blocked new-page delivery cannot expose an action revision.")
        return self


def build_new_page_delivery_readiness(
    workspace: ContentNewPageCanonicalDocumentWorkspace,
    *,
    allowed_content_types: list[str],
    authoring_profile_digest: str | None,
    evidence_ids: list[str],
) -> ContentNewPageDeliveryReadiness:
    """Expose only a deterministic, non-writing delivery precondition."""

    revision = workspace.canonical_revision
    approved = (
        workspace.status == "document_approved"
        and workspace.document_status == "approved"
        and revision is not None
        and workspace.revision_review is not None
        and workspace.revision_review.decision == "approved"
    )
    types = [
        cast(Literal["page", "post"], value)
        for value in sorted({value for value in allowed_content_types if value in {"page", "post"}})
    ]
    if revision is None:
        return _blocked_delivery_readiness(
            workspace,
            "Brakuje exact rewizji dokumentu przed przygotowaniem ActionObjectu.",
        )
    if not approved:
        return _blocked_delivery_readiness(
            workspace,
            "Dokument wymaga exact human review przed przygotowaniem ActionObjectu.",
        )
    if not types or authoring_profile_digest is None or not evidence_ids:
        return _blocked_delivery_readiness(
            workspace,
            "Brakuje obserwowanej capability WordPress potrzebnej do wyboru typu nowego draftu.",
        )
    return ContentNewPageDeliveryReadiness(
        status="ready_for_action",
        work_item_id=workspace.work_item_id,
        brief_id=workspace.brief_id,
        brief_digest=workspace.brief_digest,
        foundation_id=workspace.foundation_id,
        service_card_id=workspace.service_card_id,
        service_card_digest=workspace.service_card_digest,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        allowed_content_types=types,
        authoring_profile_digest=authoring_profile_digest,
        evidence_ids=sorted(set(evidence_ids)),
        safe_next_step=(
            "Wybierz jawnie page albo post z obserwowanych capability przed utworzeniem "
            "lokalnego ActionObjectu."
        ),
    )


def _blocked_delivery_readiness(
    workspace: ContentNewPageCanonicalDocumentWorkspace, reason: str
) -> ContentNewPageDeliveryReadiness:
    return ContentNewPageDeliveryReadiness(
        status="blocked",
        work_item_id=workspace.work_item_id,
        brief_id=workspace.brief_id,
        brief_digest=workspace.brief_digest,
        foundation_id=workspace.foundation_id,
        service_card_id=workspace.service_card_id,
        service_card_digest=workspace.service_card_digest,
        blockers=[reason],
        safe_next_step=(
            "Usuń blocker i odczytaj gotowość ponownie; "
            "WILQ nie wybiera typu draftu samodzielnie."
        ),
    )


__all__ = [
    "ContentNewPageCanonicalDocumentWorkspace",
    "ContentNewPageDocumentReviewPrerequisiteConflict",
    "ContentNewPageDocumentOutlineSection",
    "ContentNewPageDeliveryReadiness",
    "build_new_page_delivery_readiness",
    "build_new_page_canonical_document_workspace",
]
