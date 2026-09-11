"""Resolve one source-backed service selection before every snapshot stage is assembled."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from wilq.content.knowledge.cards import (
    ContentKnowledgeCardMatch,
    match_content_knowledge_cards,
    select_content_knowledge_service_card,
)
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
    build_content_work_item_service_profile_context,
)
from wilq.content.workflow.contracts.models import ContentWorkItem
from wilq.content.workflow.decisions.planning import (
    ContentPlanningDecision,
    ContentPlanningProposal,
)
from wilq.content.workflow.pipeline_steps.queue import (
    ContentWorkItemQueueBlocker,
    ContentWorkItemQueueCandidate,
)


@dataclass(frozen=True)
class SnapshotServiceSelection:
    knowledge_match: ContentKnowledgeCardMatch
    service_profile_context: ContentWorkItemServiceProfileContext
    candidate: ContentWorkItemQueueCandidate


def resolve_snapshot_service_selection(
    *,
    item: ContentWorkItem,
    candidate: ContentWorkItemQueueCandidate,
    planning_decisions: list[ContentPlanningDecision] | None,
    generated_planning_proposal: ContentPlanningProposal | None,
    service_card_id_override: str | None,
    service_profile_builder: Callable[..., ContentWorkItemServiceProfileContext] = (
        build_content_work_item_service_profile_context
    ),
) -> SnapshotServiceSelection:
    knowledge_match = match_content_knowledge_cards(item)
    scope_planning_decision = next(
        (decision for decision in planning_decisions or [] if decision.stage == "scope"),
        None,
    )
    proposal_confirms_service = generated_proposal_confirms_service_selection(
        item,
        generated_planning_proposal,
    )
    selected_service_card_id = _selected_service_card_id(
        service_card_id_override=service_card_id_override,
        scope_planning_decision=scope_planning_decision,
        generated_planning_proposal=generated_planning_proposal,
        proposal_confirms_service=proposal_confirms_service,
    )
    if selected_service_card_id is not None:
        knowledge_match = select_content_knowledge_service_card(
            knowledge_match,
            selected_service_card_id,
        )
    service_profile_context = service_profile_builder(
        item,
        knowledge_match=knowledge_match,
        service_selection_confirmed=bool(
            selected_service_card_id
            and knowledge_match.service_card is not None
            and (
                service_card_id_override is not None
                or scope_planning_decision is not None
                or proposal_confirms_service
            )
        ),
        human_override_review_required=bool(
            (
                scope_planning_decision
                and scope_planning_decision.human_override_review_required
            )
            or (
                service_card_id_override is not None
                and knowledge_match.recommended_service_card_id is not None
                and service_card_id_override != knowledge_match.recommended_service_card_id
            )
        ),
    )
    return SnapshotServiceSelection(
        knowledge_match=knowledge_match,
        service_profile_context=service_profile_context,
        candidate=gate_snapshot_candidate_on_service_binding(
            candidate,
            service_profile_context=service_profile_context,
        ),
    )


def _selected_service_card_id(
    *,
    service_card_id_override: str | None,
    scope_planning_decision: ContentPlanningDecision | None,
    generated_planning_proposal: ContentPlanningProposal | None,
    proposal_confirms_service: bool,
) -> str | None:
    if service_card_id_override is not None:
        return service_card_id_override
    if scope_planning_decision is not None:
        return scope_planning_decision.service_card_id
    if proposal_confirms_service and generated_planning_proposal is not None:
        return generated_planning_proposal.service_card_id
    return None


def generated_proposal_confirms_service_selection(
    item: ContentWorkItem,
    proposal: ContentPlanningProposal | None,
) -> bool:
    return bool(
        proposal
        and proposal.work_item_id == item.id
        and proposal.generation_status == "codex_generated"
        and proposal.proposal_id
        and proposal.planning_input_digest
        and proposal.service_selection_confirmed
        and proposal.service_card_id
        and proposal.final_canonical_url
        == (item.final_canonical_url or item.intended_final_url)
    )


def gate_snapshot_candidate_on_service_binding(
    candidate: ContentWorkItemQueueCandidate,
    *,
    service_profile_context: ContentWorkItemServiceProfileContext,
) -> ContentWorkItemQueueCandidate:
    if service_profile_context.binding_status != "unbound":
        return candidate
    blocker = ContentWorkItemQueueBlocker(
        code="missing_service_binding",
        label="Brakuje karty usługi",
        reason="Nie można przygotować planu bez typed powiązania strony z kartą usługi.",
        next_step=service_profile_context.safe_next_step,
        decision_id=candidate.decision_id,
        evidence_ids=candidate.evidence_ids,
        source_connectors=candidate.source_connectors,
    )
    return candidate.model_copy(
        update={
            "recommended_mode": "block",
            "recommended_mode_label": "wstrzymaj — najpierw sprawdź",
            "status_label": "brakuje karty usługi",
            "reason": blocker.reason,
            "preflight_status": "blocked",
            "preflight_status_label": "zablokowane",
            "safe_next_step": blocker.next_step,
            "blockers": [
                blocker,
                *[
                    existing
                    for existing in candidate.blockers
                    if existing.code != blocker.code
                ],
            ],
        }
    )


__all__ = ["SnapshotServiceSelection", "resolve_snapshot_service_selection"]
