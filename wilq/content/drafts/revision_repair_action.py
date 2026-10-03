"""Exact local ActionObject authority for one reviewed revision component repair."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.drafts.full_draft_generation_v3_contracts import (
    FullDraftGenerationV3Snapshot,
)
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    OpportunityDomain,
)

if TYPE_CHECKING:
    from wilq.content.drafts.full_draft_generation_v3_contracts import (
        FullDraftGenerationV3Receipt,
    )
    from wilq.content.quality.independent_review_contracts import (
        ContentIndependentReviewRole,
        ContentIndependentReviewRun,
    )
    from wilq.content.quality.independent_review_store import ContentIndependentReviewStore
    from wilq.content.quality.semantic_review_contracts import ContentSemanticReview
    from wilq.content.quality.semantic_review_store import ContentSemanticReviewStore
    from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
    from wilq.content.workflow.decisions.planning import ContentPlanningProposal
    from wilq.content.workflow.documents.revisions import (
        ContentDraftRevision,
        ContentDraftRevisionReview,
    )
    from wilq.content.workflow.store.store import ContentWorkflowStore

CONTENT_REVISION_REPAIR_ACTION_TYPE = "content_revision_repair_v1"
CONTENT_REVISION_REPAIR_ADAPTER = "content_revision_repair_local_authority"
REPAIR_REVIEWED_ITEM = "reviewed_exact_content_revision_repair"


class ContentRevisionRepairReviewBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["content_ux", "seo", "factual_regulatory"]
    run_id: str = Field(min_length=1)
    run_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class ContentRevisionRepairSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    work_item_id: str = Field(min_length=1)
    base_revision_id: str = Field(min_length=1)
    base_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    human_review_id: str = Field(min_length=1)
    human_review_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    semantic_review_id: str = Field(min_length=1)
    semantic_review_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    independent_reviews: tuple[ContentRevisionRepairReviewBinding, ...] = Field(
        min_length=3, max_length=3
    )
    selected_section_ids: tuple[str, ...] = ()
    selected_cta_ids: tuple[str, ...] = ()
    parent_generation: FullDraftGenerationV3Snapshot
    parent_generation_receipt_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    requested_by: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_exact_selection(self) -> Self:
        if len(self.selected_section_ids) + len(self.selected_cta_ids) != 1:
            raise ValueError("Repair must select exactly one stable section or CTA ID.")
        if len({item.role for item in self.independent_reviews}) != 3:
            raise ValueError("Repair requires all three independent review roles.")
        if not self.requested_by.strip():
            raise ValueError("Repair requires visible requester attribution.")
        return self

    @property
    def context_digest(self) -> str:
        return canonical_json_digest(self.model_dump(mode="json"))

    @property
    def action_id(self) -> str:
        return f"act_content_revision_repair_{self.context_digest}"


class ContentRevisionRepairReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot: ContentRevisionRepairSnapshot
    action_payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    preview_audit_id: str = Field(min_length=1)
    review_audit_id: str = Field(min_length=1)
    confirmation_audit_id: str = Field(min_length=1)
    impact_audit_id: str = Field(min_length=1)
    reviewed_by: str = Field(min_length=1)
    confirmed_by: str = Field(min_length=1)
    created_at: datetime

    @model_validator(mode="after")
    def aware_timestamp(self) -> Self:
        if self.created_at.tzinfo is None:
            raise ValueError("Repair authorization requires an aware audit timestamp.")
        return self

    @property
    def receipt_digest(self) -> str:
        return canonical_json_digest(self.model_dump(mode="json"))


class ContentRevisionRepairBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str = Field(min_length=1)
    receipt_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    context_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    run_id: str = Field(min_length=1)


class ContentRevisionRepairWorkerStart(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    binding: ContentRevisionRepairBinding
    started_at: datetime


def content_revision_repair_action(snapshot: ContentRevisionRepairSnapshot) -> ActionObject:
    return ActionObject(
        id=snapshot.action_id,
        title="Popraw jeden komponent dokładnej rewizji",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply,
        evidence_ids=list(snapshot.evidence_ids),
        human_diagnosis=(
            "Apply zapisuje lokalną zgodę na jedną poprawkę; "
            "osobny dispatch tworzy immutable child."
        ),
        recommended_reason="Sprawdź exact bazę, decyzję człowieka, źródła i wybrany komponent.",
        created_by="system_core_content_revision_repair_v1",
        validation_status="not_validated",
        payload={
            "action_type": CONTENT_REVISION_REPAIR_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "apply",
            "local_authority_only": True,
            "content_revision_repair_v1": snapshot.model_dump(mode="json"),
            "payload_preview": [
                {
                    "id": snapshot.action_id,
                    "operation_type": "repair_one_exact_component",
                    "apply_allowed": True,
                }
            ],
            "apply_allowed": True,
            "api_mutation_ready": True,
            "destructive": False,
            "model_enqueued_at_apply": False,
            "external_write_attempted": False,
        },
    )


def prepare_content_revision_repair_snapshot(
    *,
    workflow_snapshot: ContentWorkItemWorkflowSnapshotResponse,
    work_item_id: str,
    base_revision_id: str,
    expected_base_digest: str,
    selected_section_ids: list[str],
    selected_cta_ids: list[str],
    requested_by: str,
    workflow_store: ContentWorkflowStore,
    semantic_review_store: ContentSemanticReviewStore,
    independent_review_store: ContentIndependentReviewStore,
) -> ContentRevisionRepairSnapshot:
    """Freeze one current reviewed base and all existing review/source bindings."""
    base, human = _resolve_repair_base(
        workflow_store, work_item_id, base_revision_id, expected_base_digest
    )
    _validate_repair_component(base, selected_section_ids, selected_cta_ids)
    semantic_review, by_role = _resolve_repair_reviews(
        workflow_snapshot=workflow_snapshot,
        work_item_id=work_item_id,
        base_revision_id=base_revision_id,
        expected_base_digest=expected_base_digest,
        independent_review_store=independent_review_store,
        semantic_review_store=semantic_review_store,
    )
    proposal = _current_repair_proposal(workflow_snapshot)
    parent_generation, parent_receipt = _resolve_repair_parent_generation(
        proposal, base, workflow_store
    )
    review_bindings = _repair_review_bindings(by_role)
    evidence_ids = _repair_evidence_ids(base, human, semantic_review, by_role, parent_generation)
    return ContentRevisionRepairSnapshot(
        work_item_id=work_item_id,
        base_revision_id=base_revision_id,
        base_digest=expected_base_digest,
        human_review_id=human.decision_id,
        human_review_digest=canonical_json_digest(human.model_dump(mode="json")),
        semantic_review_id=semantic_review.review_id,
        semantic_review_digest=canonical_json_digest(semantic_review.model_dump(mode="json")),
        independent_reviews=review_bindings,
        selected_section_ids=tuple(selected_section_ids),
        selected_cta_ids=tuple(selected_cta_ids),
        parent_generation=parent_generation,
        parent_generation_receipt_digest=parent_receipt.receipt_digest,
        evidence_ids=evidence_ids,
        requested_by=requested_by,
    )


def _resolve_repair_base(
    workflow_store: ContentWorkflowStore,
    work_item_id: str,
    revision_id: str,
    expected_digest: str,
) -> tuple[ContentDraftRevision, ContentDraftRevisionReview]:
    state = workflow_store.load_draft_revision_state(work_item_id)
    base = state.latest_revision
    human = state.latest_review
    if (
        base is None
        or base.revision_id != revision_id
        or base.content_digest != expected_digest
        or human is None
        or human.decision != "needs_changes"
        or human.revision_id != revision_id
        or human.revision_digest != expected_digest
    ):
        raise ValueError("repair_review_context_missing")
    return base, human


def _validate_repair_component(
    base: ContentDraftRevision,
    selected_section_ids: list[str],
    selected_cta_ids: list[str],
) -> None:
    if len(selected_section_ids) + len(selected_cta_ids) != 1:
        raise ValueError("repair_component_selection_invalid")
    if selected_section_ids and selected_section_ids[0] not in {
        section.section_id for section in base.sections
    }:
        raise ValueError("repair_component_selection_invalid")
    if selected_cta_ids and selected_cta_ids[0] not in {cta.cta_id for cta in base.cta_blocks}:
        raise ValueError("repair_component_selection_invalid")


def _resolve_repair_reviews(
    *,
    workflow_snapshot: ContentWorkItemWorkflowSnapshotResponse,
    work_item_id: str,
    base_revision_id: str,
    expected_base_digest: str,
    independent_review_store: ContentIndependentReviewStore,
    semantic_review_store: ContentSemanticReviewStore,
) -> tuple[ContentSemanticReview, dict[ContentIndependentReviewRole, ContentIndependentReviewRun]]:
    from wilq.content.quality.independent_review_contracts import INDEPENDENT_REVIEW_ROLES
    from wilq.content.quality.review_packet_binding import content_review_snapshot_is_packet_bound
    from wilq.content.quality.semantic_review_service import read_content_semantic_review

    semantic = read_content_semantic_review(
        snapshot=workflow_snapshot,
        revision_id=base_revision_id,
        store=semantic_review_store,
    )
    if (
        semantic.status not in {"ready", "created", "idempotent"}
        or semantic.review is None
        or semantic.review.revision_digest != expected_base_digest
    ):
        raise ValueError("repair_semantic_review_missing_or_stale")
    if not content_review_snapshot_is_packet_bound(workflow_snapshot):
        raise ValueError("repair_source_packet_binding_missing")
    runs = independent_review_store.for_revision(
        work_item_id, base_revision_id, expected_base_digest
    )
    by_role = {run.role: run for run in runs}
    if set(by_role) != set(INDEPENDENT_REVIEW_ROLES):
        raise ValueError("repair_three_perspective_review_missing")
    if any(finding.disposition is None for run in by_role.values() for finding in run.findings):
        raise ValueError("repair_independent_finding_disposition_missing")
    return semantic.review, by_role


def _current_repair_proposal(
    workflow_snapshot: ContentWorkItemWorkflowSnapshotResponse,
) -> ContentPlanningProposal:
    planning = workflow_snapshot.planning_workspace
    proposal = None if planning is None else planning.proposal
    if proposal is None:
        raise ValueError("repair_current_proposal_missing")
    return proposal


def _resolve_repair_parent_generation(
    proposal: ContentPlanningProposal,
    base: ContentDraftRevision,
    workflow_store: ContentWorkflowStore,
) -> tuple[FullDraftGenerationV3Snapshot, FullDraftGenerationV3Receipt]:
    from wilq.content.drafts.full_draft_generation_v3 import full_draft_generation_v3_snapshot

    parent_generation = full_draft_generation_v3_snapshot(proposal, store=workflow_store)
    parent_snapshot = workflow_store.load_full_draft_generation_v3_snapshot(
        parent_generation.action_id
    )
    parent_receipt = workflow_store.load_full_draft_generation_v3_receipt(
        parent_generation.action_id
    )
    authority = base.generation_authorization
    proposal_metadata = base.proposal_metadata
    if (
        parent_snapshot != parent_generation
        or parent_receipt is None
        or parent_receipt.snapshot != parent_generation
        or authority is None
        or authority.action_id != parent_generation.action_id
        or authority.authorization_digest != parent_receipt.receipt_digest
        or proposal_metadata is None
        or authority.run_id != proposal_metadata.codex_run_id
    ):
        raise ValueError("repair_parent_generation_lineage_mismatch")
    return parent_generation, parent_receipt


def _repair_review_bindings(
    by_role: dict[ContentIndependentReviewRole, ContentIndependentReviewRun],
) -> tuple[ContentRevisionRepairReviewBinding, ...]:
    from wilq.content.quality.independent_review_contracts import INDEPENDENT_REVIEW_ROLES

    return tuple(
        ContentRevisionRepairReviewBinding(
            role=role,
            run_id=by_role[role].run_id,
            run_digest=canonical_json_digest(by_role[role].model_dump(mode="json")),
        )
        for role in INDEPENDENT_REVIEW_ROLES
    )


def _repair_evidence_ids(
    base: ContentDraftRevision,
    human: ContentDraftRevisionReview,
    semantic_review: ContentSemanticReview,
    by_role: dict[ContentIndependentReviewRole, ContentIndependentReviewRun],
    parent_generation: FullDraftGenerationV3Snapshot,
) -> tuple[str, ...]:
    from wilq.content.quality.semantic_inputs import revision_evidence_ids

    evidence = set(revision_evidence_ids(base))
    evidence.update(semantic_review.evidence_ids)
    evidence.update(human.evidence_ids)
    evidence.update(parent_generation.evidence_ids)
    for run in by_role.values():
        evidence.update(run.evidence_ids)
    return tuple(sorted(evidence))


def validate_content_revision_repair_payload(payload: dict[str, object]) -> list[str]:
    try:
        snapshot = ContentRevisionRepairSnapshot.model_validate(
            payload["content_revision_repair_v1"]
        )
        if content_revision_repair_action(snapshot).payload == payload:
            return []
    except (ValueError, KeyError, TypeError):
        pass
    return ["Repair ActionObject musi odpowiadać dokładnemu immutable review snapshotowi."]


def execute_content_revision_repair_action(
    action: ActionObject,
    *,
    store: ContentWorkflowStore,
    audit_events: list[AuditEvent],
    confirmed_by: str,
) -> tuple[dict[str, object] | None, list[str]]:
    try:
        snapshot = ContentRevisionRepairSnapshot.model_validate(
            action.payload["content_revision_repair_v1"]
        )
        if action.payload != content_revision_repair_action(snapshot).payload:
            raise ValueError("content_revision_repair_action_changed")
        from apps.api.wilq_api.routers.content_workflow import (
            semantic_review_snapshot_for_work_item_or_404,
        )
        from wilq.content.quality.independent_review_store import (
            content_independent_review_store,
        )
        from wilq.content.quality.semantic_review_store import content_semantic_review_store

        fresh = prepare_content_revision_repair_snapshot(
            workflow_snapshot=semantic_review_snapshot_for_work_item_or_404(snapshot.work_item_id),
            work_item_id=snapshot.work_item_id,
            base_revision_id=snapshot.base_revision_id,
            expected_base_digest=snapshot.base_digest,
            selected_section_ids=list(snapshot.selected_section_ids),
            selected_cta_ids=list(snapshot.selected_cta_ids),
            requested_by=snapshot.requested_by,
            workflow_store=store,
            semantic_review_store=content_semantic_review_store(),
            independent_review_store=content_independent_review_store(),
        )
        if fresh != snapshot:
            raise ValueError("content_revision_repair_review_or_source_changed")
        preview, review, confirmation, impact = content_revision_repair_chain(
            snapshot, audit_events, confirmed_by
        )
        receipt = ContentRevisionRepairReceipt(
            snapshot=snapshot,
            action_payload_digest=canonical_json_digest(action.payload),
            preview_audit_id=preview.id,
            review_audit_id=review.id,
            confirmation_audit_id=confirmation.id,
            impact_audit_id=impact.id,
            reviewed_by=review.actor,
            confirmed_by=confirmation.actor,
            created_at=review.created_at,
        )
        status = store.record_content_revision_repair_receipt(receipt)
        if status == "conflict":
            raise ValueError("content_revision_repair_receipt_conflict")
        return {
            "status": status,
            "repair_receipt_digest": receipt.receipt_digest,
            "model_enqueued": False,
            "external_write_attempted": False,
        }, []
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        return {
            "status": "blocked",
            "blocker": {
                "code": str(error) or "content_revision_repair_blocked",
                "owner": "WILQ content workflow",
                "evidence_ids": action.evidence_ids,
                "safe_next_step": (
                    "Odśwież exact review i źródła, a następnie "
                    "przygotuj nową poprawkę."
                ),
            },
        }, ["Poprawka rewizji nie ma już exact lokalnej authority."]


def content_revision_repair_chain(
    snapshot: ContentRevisionRepairSnapshot,
    events: list[AuditEvent],
    confirmed_by: str,
) -> tuple[AuditEvent, AuditEvent, AuditEvent, AuditEvent]:
    from wilq.actions.action_chain import revision_bound_action_chain

    action = content_revision_repair_action(snapshot)
    chain, _errors = revision_bound_action_chain(
        [event for event in events if event.action_id == action.id],
        confirmed_by=confirmed_by,
        binding_from_event=lambda event: _audit_binding(event),
        expected_binding=(snapshot.context_digest, canonical_json_digest(action.payload)),
    )
    if chain is None or REPAIR_REVIEWED_ITEM not in chain[1].details.get("checked_items", []):
        raise ValueError("content_revision_repair_audit_chain_incomplete")
    return chain


def _audit_binding(event: AuditEvent) -> tuple[str, str] | None:
    context = event.details.get("context_digest")
    payload = event.details.get("payload_digest")
    return (context, payload) if isinstance(context, str) and isinstance(payload, str) else None


__all__ = [
    "CONTENT_REVISION_REPAIR_ACTION_TYPE",
    "CONTENT_REVISION_REPAIR_ADAPTER",
    "ContentRevisionRepairBinding",
    "ContentRevisionRepairReceipt",
    "ContentRevisionRepairReviewBinding",
    "ContentRevisionRepairSnapshot",
    "ContentRevisionRepairWorkerStart",
    "REPAIR_REVIEWED_ITEM",
    "content_revision_repair_action",
    "content_revision_repair_chain",
    "prepare_content_revision_repair_snapshot",
    "validate_content_revision_repair_payload",
]
