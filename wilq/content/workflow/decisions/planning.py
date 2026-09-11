from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.audit.identity import LOCAL_PILOT_AUDIT_IDENTITY, LocalAuditTrustLevel
from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
)
from wilq.content.planning.subject import PlanningContentKind
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationBinding,
    refresh_preparation_binding_matches_content_identity,
)
from wilq.content.workflow.target.new_page import ContentNewPageDocumentIdentity

ContentPlanningStage = Literal["scope", "section_map"]
ContentPlanningDecisionValue = Literal["approved", "needs_changes"]
ContentPlanningInventoryDisposition = Literal[
    "preserve",
    "merge",
    "rewrite",
    "remove_review_required",
    "create",
]
ContentPlanningInventoryMappingStatus = Literal["mapped", "unmapped", "ambiguous", "excluded"]


class ContentPlanningPageAssets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = ""
    h1: str = ""
    lead: str = ""
    meta_title: str = ""
    meta_description: str = ""
    byline: str | None = None


class ContentPlanningFaqItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    query_terms: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)


class ContentPlanningCtaBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    placement: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    copy_direction: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)


class ContentPlanningInternalLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    placement: str = Field(min_length=1)
    target_url: str = Field(min_length=1)
    anchor_direction: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)


class ContentPlanningConditionalHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Literal["google_ads", "social"]
    hypothesis: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    review_required: Literal[True] = True


class ContentPlanningMeasurementPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics_to_watch: list[str] = Field(default_factory=list)
    baseline_evidence_ids: list[str] = Field(default_factory=list)
    observation_rule: str = ""
    success_claim_rule: str = ""


class ContentPlanningSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str = ""
    heading: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    reader_question: str = ""
    inventory_disposition: ContentPlanningInventoryDisposition = "create"
    inventory_section_id: str | None = None
    inventory_heading: str | None = None
    query_terms: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    regulatory_requirement_ids: list[str] = Field(default_factory=list)
    source_material_ids: list[str] = Field(default_factory=list)
    knowledge_card_ids: list[str] = Field(default_factory=list)


class ContentPlanningInventoryMapping(BaseModel):
    """Deterministic coverage row for one existing page section."""

    model_config = ConfigDict(extra="forbid")

    inventory_section_id: str = Field(min_length=1)
    inventory_heading: str = Field(min_length=1)
    status: ContentPlanningInventoryMappingStatus
    mapped_section_id: str | None = None
    mapped_section_heading: str | None = None
    disposition: ContentPlanningInventoryDisposition | None = None
    reason: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class ContentPlanningProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_item_id: str = Field(min_length=1)
    planning_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    proposal_id: str | None = None
    proposal_version: int | None = Field(default=None, ge=1)
    codex_run_id: str | None = None
    generation_status: Literal["baseline", "codex_generated"] = "baseline"
    input_schema_version: str = "wilq_content_planning_input_v1"
    criteria_version: str = "wilq_people_first_planning_v1"
    planning_input_digest: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    goal: Literal["refresh_existing", "new_page"] = "refresh_existing"
    content_kind: PlanningContentKind = "service"
    final_canonical_url: str | None = None
    proposed_ia_location: str | None = None
    new_page_document_identity: ContentNewPageDocumentIdentity | None = None
    service_card_id: str | None = None
    service_label: str | None = None
    service_selection_confirmed: bool = False
    human_override_review_required: bool = False
    target_reader: str = Field(min_length=1)
    buyer_problem: str = Field(min_length=1)
    buyer_trigger: str = Field(min_length=1)
    search_intent: str = Field(min_length=1)
    angle: str = ""
    value_proposition: str = ""
    cta_direction: str = Field(min_length=1)
    internal_link_directions: list[str] = Field(default_factory=list)
    sections: list[ContentPlanningSection] = Field(min_length=1)
    inventory_mapping: list[ContentPlanningInventoryMapping] = Field(default_factory=list)
    search_demand: ContentSearchDemandEvidence
    page_assets: ContentPlanningPageAssets = Field(default_factory=ContentPlanningPageAssets)
    faq: list[ContentPlanningFaqItem] = Field(default_factory=list)
    cta_blocks: list[ContentPlanningCtaBlock] = Field(default_factory=list)
    minimum_cta_blocks: int = Field(default=1, ge=1, le=4)
    required_cta_patterns: list[str] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def require_nonblank_cta_patterns(self) -> ContentPlanningProposal:
        if any(not pattern.strip() for pattern in self.required_cta_patterns):
            raise ValueError("Required CTA patterns must be non-blank")
        return self

    internal_links: list[ContentPlanningInternalLink] = Field(default_factory=list)
    conditional_hypotheses: list[ContentPlanningConditionalHypothesis] = Field(default_factory=list)
    measurement_plan: ContentPlanningMeasurementPlan = Field(
        default_factory=ContentPlanningMeasurementPlan
    )
    measurement_metrics: list[str] = Field(default_factory=list)
    measurement_baseline_evidence_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    source_material_ids: list[str] = Field(default_factory=list)
    knowledge_card_ids: list[str] = Field(default_factory=list)
    refresh_preparation_binding: ContentRefreshPreparationBinding | None = None
    created_at: datetime | None = None

    @model_validator(mode="after")
    def require_goal_identity(self) -> ContentPlanningProposal:
        if self.goal == "refresh_existing":
            if not self.final_canonical_url or not self.final_canonical_url.strip():
                raise ValueError("Refresh proposal requires final_canonical_url.")
            if self.proposed_ia_location is not None or self.new_page_document_identity is not None:
                raise ValueError("Refresh proposal cannot carry new-page identity.")
        else:
            if self.final_canonical_url is not None:
                raise ValueError("New-page proposal cannot claim a public canonical URL.")
            if (
                self.proposed_ia_location is None
                or len(self.proposed_ia_location.strip()) < 3
                or self.new_page_document_identity is None
            ):
                raise ValueError("New-page proposal requires exact IA and document identity.")
            if self.new_page_document_identity.work_item_id != self.work_item_id:
                raise ValueError("New-page proposal identity must match the work item.")
            if self.new_page_document_identity.proposed_ia_location != self.proposed_ia_location:
                raise ValueError("New-page proposal identity must match the IA location.")
            if self.inventory_mapping:
                raise ValueError("New-page proposal cannot carry existing-page inventory mapping.")
            if any(
                section.inventory_disposition != "create"
                or section.inventory_section_id is not None
                or section.inventory_heading is not None
                for section in self.sections
            ):
                raise ValueError(
                    "New-page proposal sections must be created without existing-page inventory."
                )
        if self.refresh_preparation_binding is not None and (
            self.goal != "refresh_existing"
            or not refresh_preparation_binding_matches_content_identity(
                self.refresh_preparation_binding,
                work_item_id=self.work_item_id,
                service_card_id=self.service_card_id,
                planning_input_digest=self.planning_input_digest,
                final_canonical_url=self.final_canonical_url,
            )
        ):
            raise ValueError(
                "Refresh preparation binding requires one exact refresh proposal receipt."
            )
        return self


class ContentPlanningDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1)
    decision_number: int = Field(ge=1)
    work_item_id: str = Field(min_length=1)
    stage: ContentPlanningStage
    planning_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    service_card_id: str | None = None
    human_override_review_required: bool = False
    decision: ContentPlanningDecisionValue
    reviewed_by: str = Field(min_length=1)
    principal_id: str = LOCAL_PILOT_AUDIT_IDENTITY.principal_id
    workspace_id: str = LOCAL_PILOT_AUDIT_IDENTITY.workspace_id
    trust_level: LocalAuditTrustLevel = LOCAL_PILOT_AUDIT_IDENTITY.trust_level
    checked_items: list[str] = Field(default_factory=list)
    notes: str = ""
    created_at: datetime


class ContentPlanningWorkspace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal: ContentPlanningProposal
    scope_decision: ContentPlanningDecision | None = None
    section_map_decision: ContentPlanningDecision | None = None
    scope_current: bool
    section_map_current: bool

    @model_validator(mode="after")
    def require_exact_decision_binding(self) -> ContentPlanningWorkspace:
        for decision in (self.scope_decision, self.section_map_decision):
            if decision is None:
                continue
            if (
                decision.work_item_id != self.proposal.work_item_id
                or decision.planning_digest != self.proposal.planning_digest
                or (
                    decision.service_card_id is not None
                    and decision.service_card_id != self.proposal.service_card_id
                )
            ):
                raise ValueError("Planning decision must bind to the exact proposal.")
        expected_scope_current = bool(
            self.scope_decision is not None
            and self.scope_decision.decision == "approved"
            and self.scope_decision.work_item_id == self.proposal.work_item_id
            and self.scope_decision.planning_digest == self.proposal.planning_digest
            and (
                self.scope_decision.service_card_id is None
                or self.scope_decision.service_card_id == self.proposal.service_card_id
            )
        )
        if self.scope_current != expected_scope_current:
            raise ValueError("scope_current must reflect the exact scope decision.")
        expected_section_map_current = bool(
            self.proposal.generation_status == "codex_generated"
            and self.proposal.proposal_id
            and self.proposal.sections
        )
        if self.section_map_current != expected_section_map_current:
            raise ValueError("section_map_current must reflect the exact generated proposal.")
        return self


def build_content_planning_proposal(
    *,
    brief: ContentSalesBrief,
    draft: ContentDraftPackage,
    service_profile: ContentWorkItemServiceProfileContext,
    search_demand: ContentSearchDemandEvidence,
) -> ContentPlanningProposal:
    payload = {
        "work_item_id": brief.work_item_id,
        "final_canonical_url": brief.final_canonical_url,
        "service_card_id": service_profile.service_card_id,
        "service_label": service_profile.service_label,
        "target_reader": brief.target_reader,
        "buyer_problem": brief.buyer_problem,
        "buyer_trigger": brief.buyer_trigger,
        "search_intent": brief.search_intent,
        "cta_direction": brief.cta_direction,
        "internal_link_directions": brief.internal_link_direction,
        "sections": [
            {
                "section_id": f"planning_section_{index:02d}",
                "heading": section.heading,
                "purpose": _planning_section_purpose(section.heading, section.purpose),
                "reader_question": _planning_reader_question(section.heading),
                "inventory_disposition": _baseline_inventory_disposition(brief),
                "inventory_heading": (
                    section.heading if _baseline_inventory_disposition(brief) != "create" else None
                ),
                "query_terms": [],
                "evidence_ids": section.evidence_ids,
                "claim_ids": [],
            }
            for index, section in enumerate(draft.sections, start=1)
        ],
        "search_demand": search_demand.model_dump(mode="json"),
        "evidence_ids": list(
            dict.fromkeys(
                [
                    *brief.evidence_ids,
                    *(
                        evidence_id
                        for section in draft.sections
                        for evidence_id in section.evidence_ids
                    ),
                ]
            )
        ),
        "source_connectors": brief.source_connectors,
    }
    digest = _planning_digest(payload)
    return ContentPlanningProposal.model_validate(
        {
            "planning_digest": digest,
            "service_selection_confirmed": service_profile.service_selection_confirmed,
            "human_override_review_required": (service_profile.human_override_review_required),
            **payload,
        }
    )


def _baseline_inventory_disposition(
    brief: ContentSalesBrief,
) -> ContentPlanningInventoryDisposition:
    """Keep the baseline honest about an already-existing page.

    The baseline is only a review starting point, but it must not present
    existing headings as newly created sections. Generated proposals may later
    choose a different disposition after human review.
    """
    dispositions: dict[str, ContentPlanningInventoryDisposition] = {
        "preserve": "preserve",
        "refresh": "rewrite",
        "merge": "merge",
    }
    return dispositions.get(brief.operations_context.recommended_mode, "create")


def _planning_section_purpose(heading: str, fallback: str) -> str:
    """Keep the baseline plan faithful to the inventory source.

    ``the_content`` is a container for the page's existing body, not a topic
    that a writer should explain.  A generic purpose here would leak an
    invented section into the marketer view before the generated proposal is
    even available.
    """
    if heading == "Treść główna (the_content)":
        return (
            "Pracuj na istniejącej treści głównej: zachowaj użyteczne informacje, "
            "uzupełnij braki i przepisz tylko to, co wynika z aktualnych dowodów."
        )
    return fallback


def _planning_reader_question(heading: str) -> str:
    if heading == "Treść główna (the_content)":
        return "Co z obecnej treści odpowiada czytelnikowi, a co wymaga poprawy?"
    return f"Jaką odpowiedź powinien dostać czytelnik w sekcji „{heading}”?"


def _planning_digest(payload: Mapping[str, object]) -> str:
    return sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_content_planning_workspace(
    proposal: ContentPlanningProposal,
    decisions: list[ContentPlanningDecision],
) -> ContentPlanningWorkspace:
    # Historical decisions may belong to an earlier generated plan while this
    # projection still holds a baseline proposal. They are not this proposal's
    # decision and must never enter its typed workspace as if they were.
    scope = next(
        (
            item
            for item in decisions
            if item.stage == "scope" and item.planning_digest == proposal.planning_digest
        ),
        None,
    )
    section_map = next(
        (
            item
            for item in decisions
            if item.stage == "section_map" and item.planning_digest == proposal.planning_digest
        ),
        None,
    )
    return ContentPlanningWorkspace(
        proposal=proposal,
        scope_decision=scope,
        section_map_decision=section_map,
        scope_current=bool(
            scope
            and scope.planning_digest == proposal.planning_digest
            and scope.decision == "approved"
        ),
        # Preserve-first baseline sections are only a preview.  The section
        # map becomes current after the API-owned proposal has actually been
        # generated from the selected service, inventory and evidence.  This
        # keeps the operator on scope with a visible Generate plan action
        # instead of unlocking the draft editor on a baseline projection.
        section_map_current=bool(
            proposal.generation_status == "codex_generated"
            and proposal.proposal_id
            and proposal.sections
        ),
    )
