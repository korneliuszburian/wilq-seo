from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.briefs.sales import ContentSalesBrief
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
)
from wilq.content.workflow.demand_evidence import ContentSearchDemandEvidence

ContentPlanningStage = Literal["scope", "section_map"]
ContentPlanningDecisionValue = Literal["approved", "needs_changes"]


class ContentPlanningSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)


class ContentPlanningProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_item_id: str = Field(min_length=1)
    planning_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    final_canonical_url: str = Field(min_length=1)
    service_card_id: str | None = None
    service_label: str | None = None
    target_reader: str = Field(min_length=1)
    buyer_problem: str = Field(min_length=1)
    buyer_trigger: str = Field(min_length=1)
    search_intent: str = Field(min_length=1)
    cta_direction: str = Field(min_length=1)
    internal_link_directions: list[str] = Field(default_factory=list)
    sections: list[ContentPlanningSection] = Field(min_length=1)
    search_demand: ContentSearchDemandEvidence
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)


class ContentPlanningDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1)
    decision_number: int = Field(ge=1)
    work_item_id: str = Field(min_length=1)
    stage: ContentPlanningStage
    planning_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: ContentPlanningDecisionValue
    reviewed_by: str = Field(min_length=1)
    checked_items: list[str] = Field(default_factory=list)
    notes: str = ""
    created_at: datetime


class ContentPlanningReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: ContentPlanningStage
    expected_planning_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
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
                "heading": section.heading,
                "purpose": section.purpose,
                "evidence_ids": section.evidence_ids,
            }
            for section in draft.sections
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
    digest = sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return ContentPlanningProposal.model_validate(
        {"planning_digest": digest, **payload}
    )


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
