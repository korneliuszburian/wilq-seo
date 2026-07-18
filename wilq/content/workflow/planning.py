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
from wilq.content.workflow.demand_evidence import ContentSearchDemandEvidence

ContentPlanningStage = Literal["scope", "section_map"]
ContentPlanningDecisionValue = Literal["approved", "needs_changes"]
ContentPlanningInventoryDisposition = Literal[
    "preserve",
    "merge",
    "rewrite",
    "remove_review_required",
    "create",
]


class ContentPlanningPageAssets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = ""
    h1: str = ""
    lead: str = ""
    meta_title: str = ""
    meta_description: str = ""


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
    inventory_heading: str | None = None
    query_terms: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)


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
    final_canonical_url: str = Field(min_length=1)
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
    search_demand: ContentSearchDemandEvidence
    page_assets: ContentPlanningPageAssets = Field(
        default_factory=ContentPlanningPageAssets
    )
    faq: list[ContentPlanningFaqItem] = Field(default_factory=list)
    cta_blocks: list[ContentPlanningCtaBlock] = Field(default_factory=list)
    internal_links: list[ContentPlanningInternalLink] = Field(default_factory=list)
    conditional_hypotheses: list[ContentPlanningConditionalHypothesis] = Field(
        default_factory=list
    )
    measurement_plan: ContentPlanningMeasurementPlan = Field(
        default_factory=ContentPlanningMeasurementPlan
    )
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


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


class ContentPlanningReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: ContentPlanningStage
    expected_planning_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    service_card_id: str | None = None
    decision: ContentPlanningDecisionValue
    reviewed_by: str = Field(min_length=1)
    checked_items: list[str] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def require_review_evidence(self) -> ContentPlanningReviewRequest:
        if self.decision == "approved" and not self.checked_items:
            raise ValueError("Planning approval requires at least one checked item.")
        if self.decision == "needs_changes" and not self.notes.strip():
            raise ValueError("Planning changes require an operator note.")
        return self


class ContentPlanningWorkspace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal: ContentPlanningProposal
    scope_decision: ContentPlanningDecision | None = None
    section_map_decision: ContentPlanningDecision | None = None
    scope_current: bool
    section_map_current: bool


class ContentPlanningReviewResponse(BaseModel):
    status: Literal["recorded", "idempotent"]
    decision: ContentPlanningDecision
    planning_workspace: ContentPlanningWorkspace


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
                "purpose": section.purpose,
                "reader_question": section.purpose,
                "inventory_disposition": _baseline_inventory_disposition(brief),
                "inventory_heading": (
                    section.heading
                    if _baseline_inventory_disposition(brief) != "create"
                    else None
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
            "human_override_review_required": (
                service_profile.human_override_review_required
            ),
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
    return {
        "preserve": "preserve",
        "refresh": "rewrite",
        "merge": "merge",
    }.get(brief.operations_context.recommended_mode, "create")


def _planning_digest(payload: Mapping[str, object]) -> str:
    return sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_content_planning_workspace(
    proposal: ContentPlanningProposal,
    decisions: list[ContentPlanningDecision],
) -> ContentPlanningWorkspace:
    scope = next((item for item in decisions if item.stage == "scope"), None)
    section_map = next((item for item in decisions if item.stage == "section_map"), None)
    return ContentPlanningWorkspace(
        proposal=proposal,
        scope_decision=scope,
        section_map_decision=section_map,
        scope_current=bool(
            scope
            and scope.planning_digest == proposal.planning_digest
            and scope.decision == "approved"
        ),
        section_map_current=bool(
            section_map
            and section_map.planning_digest == proposal.planning_digest
            and section_map.decision == "approved"
        ),
    )
