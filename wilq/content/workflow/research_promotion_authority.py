"""Preview-only ActionObject for future research-fact promotion review."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.audit.trusted_local_confirmation import TrustedLocalPrincipalReceipt
from wilq.content.knowledge.source_facts import ContentSourceFact, SourceFactScope
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.research_promotion_candidate import (
    ResearchPromotionCandidateProjection,
    build_default_research_promotion_candidate,
)
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    AuditEvent,
    OpportunityDomain,
)

_HEX64 = r"^[0-9a-f]{64}$"
_SAFE_IDENTIFIER = r"^[a-z][a-z0-9_-]{0,239}$"
CONTENT_RESEARCH_FACT_PROMOTION_ACTION_TYPE = "content_research_fact_promotion"
CONTENT_RESEARCH_FACT_PROMOTION_PREVIEW_CONTRACT = "content_research_fact_promotion_preview_v1"
CONTENT_RESEARCH_FACT_PROMOTION_MUTATION_ADAPTER = "content_research_fact_promotion_store"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


@dataclass(frozen=True, slots=True)
class ContentResearchFactPromotionExecutionContext:
    """Server-resolved stores and audits for one promotion apply attempt."""

    promotion_store: Any
    persisted_audit_events: tuple[AuditEvent, ...]
    promotion_store_identity: str
    audit_store_identity: str
    context_digest: str
    trusted_principal_receipt: TrustedLocalPrincipalReceipt | None = None


class ContentResearchFactPromotionPreviewCommand(_FrozenModel):
    proposal_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    proposed_scope: SourceFactScope
    proposed_confidence: float = Field(ge=0, le=1)


class ContentResearchFactPromotionPreviewRequest(_FrozenModel):
    proposed_scope: SourceFactScope
    proposed_confidence: float = Field(ge=0, le=1)


class ContentResearchFactPromotionSnapshot(_FrozenModel):
    schema_version: Literal["content_research_fact_promotion_snapshot_v1"] = (
        "content_research_fact_promotion_snapshot_v1"
    )
    proposal_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    proposal_digest: str = Field(pattern=_HEX64)
    acquisition_run_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    acquisition_run_digest: str = Field(pattern=_HEX64)
    observation_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=64)
    source_url: str = Field(min_length=1, max_length=2048)
    source_connectors: tuple[str, ...] = Field(min_length=1, max_length=16)
    identity_binding_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    identity_binding_digest: str = Field(pattern=_HEX64)
    classification_run_digest: str = Field(pattern=_HEX64)
    target_card_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    target_card_type: str = Field(min_length=1)
    target_card_title: str = Field(min_length=1)
    card_evidence_ids: tuple[str, ...] = ()
    card_source_connectors: tuple[str, ...] = ()
    card_freshness: str | None = None
    freshness_date: str = Field(min_length=1, max_length=64)
    registry_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    registry_digest: str = Field(pattern=_HEX64)
    policy_source_digest: str = Field(pattern=_HEX64)
    proposed_claim: str = Field(min_length=1, max_length=1200)
    proposed_scope: SourceFactScope
    proposed_confidence: float = Field(ge=0, le=1)
    allowed_claims: tuple[str, ...] = ()
    blocked_claims: tuple[str, ...] = ()
    evidence_requirements: tuple[str, ...] = ()
    context_digest: str = Field(pattern=_HEX64)
    checked_at: datetime

    @model_validator(mode="after")
    def require_self_authenticating_snapshot(self) -> Self:
        payload = self.model_dump(mode="json")
        payload.pop("context_digest")
        expected = canonical_json_digest(payload)
        if self.context_digest != expected:
            raise ValueError("Research promotion snapshot digest does not match payload.")
        if self.checked_at.tzinfo is None or self.checked_at.utcoffset() is None:
            raise ValueError("Research promotion snapshot time must be timezone-aware.")
        return self


class ContentResearchFactPromotionPreviewResponse(_FrozenModel):
    response_type: Literal["content_research_fact_promotion_preview"] = (
        "content_research_fact_promotion_preview"
    )
    status: Literal["preview_ready", "blocked"]
    proposal_id: str = Field(min_length=1)
    action: ActionObject | None = None
    snapshot: ContentResearchFactPromotionSnapshot | None = None
    blockers: tuple[str, ...] = ()
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_preview_state(self) -> Self:
        if self.status == "preview_ready" and (self.action is None or self.snapshot is None):
            raise ValueError("Ready promotion preview requires action and snapshot.")
        if self.status == "blocked" and (self.action is not None or not self.blockers):
            raise ValueError("Blocked promotion preview cannot expose an action.")
        return self


class ContentResearchFactPromotionProposal(_FrozenModel):
    action_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    proposal_digest: str = Field(pattern=_HEX64)
    snapshot: ContentResearchFactPromotionSnapshot
    prepared_at: datetime

    @model_validator(mode="after")
    def require_identity(self) -> Self:
        expected = canonical_json_digest(self.snapshot.model_dump(mode="json"))
        if self.proposal_digest != expected or self.action_id != (
            f"act_content_research_fact_promotion_{expected[:24]}"
        ):
            raise ValueError("Research promotion proposal identity does not match snapshot.")
        return self


class ContentResearchFactPromotionReceipt(_FrozenModel):
    receipt_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    receipt_digest: str = Field(pattern=_HEX64)
    action_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    action_payload_digest: str = Field(pattern=_HEX64)
    snapshot: ContentResearchFactPromotionSnapshot
    source_fact: ContentSourceFact
    preview_audit_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    review_audit_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    confirmation_audit_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    impact_audit_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    reviewed_by: str = Field(min_length=1, max_length=240)
    confirmed_by: str = Field(min_length=1, max_length=240)
    recorded_at: datetime

    @model_validator(mode="after")
    def require_identity(self) -> Self:
        payload = self.model_dump(mode="json")
        payload.pop("receipt_id")
        payload.pop("receipt_digest")
        expected = canonical_json_digest(payload)
        if self.receipt_digest != expected or self.receipt_id != (
            f"content_research_fact_promotion_{expected[:24]}"
        ):
            raise ValueError("Research promotion receipt identity does not match payload.")
        return self


def prepare_research_fact_promotion_preview(
    command: ContentResearchFactPromotionPreviewCommand,
    *,
    store: Any | None = None,
) -> ContentResearchFactPromotionPreviewResponse:
    candidate = build_default_research_promotion_candidate(command.proposal_id)
    if candidate.status != "ready_for_human_decisions" or candidate.policy is None:
        blockers = tuple(
            blocker.reason for blocker in candidate.blockers
        ) or ("Promotion candidate is not ready for human decisions.",)
        return ContentResearchFactPromotionPreviewResponse(
            status="blocked",
            proposal_id=command.proposal_id,
            blockers=blockers,
            safe_next_step=candidate.safe_next_step,
        )
    if not candidate.proposed_claim or not candidate.proposed_claim.strip():
        return ContentResearchFactPromotionPreviewResponse(
            status="blocked",
            proposal_id=command.proposal_id,
            blockers=("research_claim_missing: Research proposal has no non-blank claim.",),
            safe_next_step="Uzyskaj researcher claim przed przygotowaniem promotion preview.",
        )
    snapshot = _snapshot(candidate, command)
    if store is not None:
        proposal = ContentResearchFactPromotionProposal(
            action_id=_promotion_action_id(snapshot),
            proposal_digest=_promotion_snapshot_digest(snapshot),
            snapshot=snapshot,
            prepared_at=datetime.now(UTC),
        )
        store.record_research_fact_promotion_proposal(proposal)
    action = _action(snapshot)
    return ContentResearchFactPromotionPreviewResponse(
        status="preview_ready",
        proposal_id=command.proposal_id,
        action=action,
        snapshot=snapshot,
        blockers=(),
        safe_next_step=(
            "To jest preview-only; promotion wymaga osobnego review, confirmation, "
            "impact check i przyszłego apply contract."
        ),
    )


def _snapshot(
    candidate: ResearchPromotionCandidateProjection,
    command: ContentResearchFactPromotionPreviewCommand,
) -> ContentResearchFactPromotionSnapshot:
    if candidate.policy is None or candidate.observation_id is None:
        raise ValueError("Research promotion candidate lacks exact policy or observation.")
    payload: dict[str, Any] = {
        "schema_version": "content_research_fact_promotion_snapshot_v1",
        "proposal_id": candidate.proposal_id,
        "proposal_digest": candidate.proposal_digest,
        "acquisition_run_id": candidate.acquisition_run_id,
        "acquisition_run_digest": candidate.acquisition_run_digest,
        "observation_id": candidate.observation_id,
        "evidence_ids": candidate.evidence_ids,
        "source_url": candidate.source_url,
        "source_connectors": candidate.source_connectors,
        "identity_binding_id": candidate.identity_binding_id,
        "identity_binding_digest": candidate.identity_binding_digest,
        "classification_run_digest": candidate.classification_run_digest,
        "target_card_id": candidate.policy.target_card_id,
        "target_card_type": candidate.policy.target_card_type,
        "target_card_title": candidate.policy.target_card_title,
        "card_evidence_ids": candidate.policy.card_evidence_ids,
        "card_source_connectors": candidate.policy.card_source_connectors,
        "card_freshness": candidate.policy.card_freshness,
        "freshness_date": candidate.freshness_date,
        "registry_id": candidate.registry.registry_id,
        "registry_digest": candidate.registry.registry_digest,
        "policy_source_digest": candidate.policy.policy_source_digest,
        "proposed_claim": candidate.proposed_claim,
        "proposed_scope": command.proposed_scope,
        "proposed_confidence": command.proposed_confidence,
        "allowed_claims": candidate.policy.allowed_claims,
        "blocked_claims": candidate.policy.blocked_claims,
        "evidence_requirements": candidate.policy.evidence_requirements,
        "checked_at": datetime.now(UTC),
    }
    digest_payload = {
        **payload,
        "checked_at": payload["checked_at"].astimezone(UTC).isoformat().replace(
            "+00:00", "Z"
        ),
    }
    digest = canonical_json_digest(digest_payload)
    return ContentResearchFactPromotionSnapshot(
        **payload,
        context_digest=digest,
    )


def _action(snapshot: ContentResearchFactPromotionSnapshot) -> ActionObject:
    action_digest = canonical_json_digest(snapshot.model_dump(mode="json"))
    action_id = f"act_content_research_fact_promotion_{action_digest[:24]}"
    payload = {
        "action_type": CONTENT_RESEARCH_FACT_PROMOTION_ACTION_TYPE,
        "connector": "wordpress_ekologus",
        "mode": "apply",
        "preview_contract": CONTENT_RESEARCH_FACT_PROMOTION_PREVIEW_CONTRACT,
        "local_authority_only": True,
        "apply_allowed": True,
        "api_mutation_ready": True,
        "destructive": False,
        "promotion_snapshot": snapshot.model_dump(mode="json"),
        "runtime_blockers": [],
    }
    evidence_ids = sorted(set(snapshot.evidence_ids) | set(snapshot.card_evidence_ids))
    return ActionObject(
        id=action_id,
        title="Przygotuj propozycję factu z research proposal",
        domain=OpportunityDomain.knowledge,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply,
        evidence_ids=evidence_ids,
        human_diagnosis=(
            "Preview wiąże claim researchera z exact observation, Service Profile card "
            "i bieżącym registry; nie zatwierdza ani nie zapisuje factu."
        ),
        recommended_reason="Najpierw wykonaj human review proponowanego scope i confidence.",
        payload=payload,
        validation_status="not_validated",
        created_by="system_core_research_promotion",
    )


def _promotion_snapshot_digest(snapshot: ContentResearchFactPromotionSnapshot) -> str:
    return canonical_json_digest(snapshot.model_dump(mode="json"))


def _promotion_action_id(snapshot: ContentResearchFactPromotionSnapshot) -> str:
    return f"act_content_research_fact_promotion_{_promotion_snapshot_digest(snapshot)[:24]}"


def promotion_action_payload_digest(action: ActionObject) -> str:
    return canonical_json_digest(
        {
            "action_type": action.payload.get("action_type"),
            "preview_contract": action.payload.get("preview_contract"),
            "promotion_snapshot": action.payload.get("promotion_snapshot"),
        }
    )


def validate_research_fact_promotion_action_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("action_type") != CONTENT_RESEARCH_FACT_PROMOTION_ACTION_TYPE:
        errors.append("Research promotion action type is invalid.")
    if payload.get("connector") != "wordpress_ekologus":
        errors.append("Research promotion connector is invalid.")
    if payload.get("local_authority_only") is not True:
        errors.append("Research promotion must remain local-only.")
    if payload.get("mode") != "apply":
        errors.append("Research promotion action must use apply mode.")
    if payload.get("preview_contract") != CONTENT_RESEARCH_FACT_PROMOTION_PREVIEW_CONTRACT:
        errors.append("Research promotion preview contract is missing.")
    if payload.get("apply_allowed") is not True or payload.get("api_mutation_ready") is not True:
        errors.append("Research promotion apply contract is not ready.")
    if payload.get("destructive") is not False:
        errors.append("Research promotion cannot be destructive.")
    if payload.get("runtime_blockers") != []:
        errors.append("Research promotion action has runtime blockers.")
    try:
        ContentResearchFactPromotionSnapshot.model_validate(
            payload.get("promotion_snapshot", {})
        )
    except Exception:
        errors.append("Research promotion snapshot is invalid.")
    return errors


def load_content_research_fact_promotion_action(
    action_id: str, *, store: Any
) -> ActionObject | None:
    proposal = store.load_research_fact_promotion_proposal(action_id)
    if proposal is None:
        return None
    current = build_default_research_promotion_candidate(proposal.snapshot.proposal_id)
    if current.status != "ready_for_human_decisions" or current.policy is None:
        action = _action(proposal.snapshot)
        return action.model_copy(
            update={
                "status": ActionStatus.blocked,
                "payload": {
                    **action.payload,
                    "apply_allowed": False,
                    "api_mutation_ready": False,
                    "runtime_blockers": ["promotion_snapshot_drift"],
                },
            }
        )
    command = ContentResearchFactPromotionPreviewCommand(
        proposal_id=proposal.snapshot.proposal_id,
        proposed_scope=proposal.snapshot.proposed_scope,
        proposed_confidence=proposal.snapshot.proposed_confidence,
    )
    current_response = prepare_research_fact_promotion_preview(command)
    if (
        current_response.snapshot is None
        or _snapshot_content(current_response.snapshot)
        != _snapshot_content(proposal.snapshot)
    ):
        action = _action(proposal.snapshot)
        return action.model_copy(
            update={
                "status": ActionStatus.blocked,
                "payload": {
                    **action.payload,
                    "apply_allowed": False,
                    "api_mutation_ready": False,
                    "runtime_blockers": ["promotion_snapshot_drift"],
                },
            }
        )
    return _action(proposal.snapshot)


def _snapshot_content(snapshot: ContentResearchFactPromotionSnapshot) -> dict[str, Any]:
    return snapshot.model_dump(exclude={"checked_at", "context_digest"})


def execute_research_fact_promotion(
    action: ActionObject,
    *,
    context: ContentResearchFactPromotionExecutionContext,
) -> tuple[dict[str, Any] | None, list[str]]:
    action_errors = _canonical_action_errors(action)
    if action_errors:
        return None, action_errors
    context_errors = _execution_context_errors(action, context)
    if context_errors:
        return None, context_errors
    store = context.promotion_store
    proposal = store.load_research_fact_promotion_proposal(action.id)
    if proposal is None:
        return None, ["Research promotion proposal is missing."]
    try:
        snapshot = ContentResearchFactPromotionSnapshot.model_validate(
            action.payload.get("promotion_snapshot", {})
        )
    except Exception:
        return None, ["Research promotion snapshot is invalid."]
    if snapshot != proposal.snapshot:
        return None, ["Research promotion snapshot changed before apply."]
    payload_digest = promotion_action_payload_digest(action)
    required, audit_errors = _persisted_promotion_audit_chain(
        action.id,
        snapshot,
        payload_digest,
        context.persisted_audit_events,
    )
    if audit_errors:
        return None, audit_errors
    assert required is not None
    if any(
        not _trusted_promotion_audit_event(
            event,
            context.trusted_principal_receipt,
            action_id=action.id,
            payload_digest=payload_digest,
            snapshot_digest=snapshot.context_digest,
        )
        for event in required.values()
    ):
        return None, ["promotion_reviewer_identity_unverified"]
    current = build_default_research_promotion_candidate(snapshot.proposal_id)
    if current.status != "ready_for_human_decisions" or current.policy is None:
        return None, ["Research promotion candidate drifted or became stale."]
    current_snapshot = _snapshot(
        current,
        ContentResearchFactPromotionPreviewCommand(
            proposal_id=snapshot.proposal_id,
            proposed_scope=snapshot.proposed_scope,
            proposed_confidence=snapshot.proposed_confidence,
        ),
    )
    if _snapshot_content(current_snapshot) != _snapshot_content(snapshot):
        return None, ["Research promotion snapshot drifted before apply."]
    preview_event = required["action_preview_generated"]
    review_event = required["human_review_approved_for_prepare"]
    confirmation_event = required["action_apply_confirmed"]
    impact_event = required["action_impact_check_completed"]
    assert (
        preview_event is not None
        and review_event is not None
        and confirmation_event is not None
        and impact_event is not None
    )
    source_fact = ContentSourceFact(
        source_id=f"research_proposal_fact_{snapshot.proposal_id}",
        source_type="public_site",
        privacy_class="commit_safe",
        source_url_or_path=snapshot.source_url,
        extracted_fact=snapshot.proposed_claim,
        scope=snapshot.proposed_scope,
        freshness_date=snapshot.freshness_date,
        confidence=snapshot.proposed_confidence,
        review_status="approved",
        reviewer=review_event.actor,
        evidence_ids=list(snapshot.evidence_ids),
        source_connectors=list(snapshot.source_connectors),
        blocked_claims=list(snapshot.blocked_claims),
        target_card_id=snapshot.target_card_id,
        target_card_type=snapshot.target_card_type,
        target_card_title=snapshot.target_card_title,
        allowed_claims=list(snapshot.allowed_claims),
        evidence_requirements=list(snapshot.evidence_requirements),
        usage_notes=["Promoted from reviewed research proposal via local ActionObject."],
    )
    recorded_at = datetime.now(UTC)
    receipt_payload: dict[str, Any] = {
        "action_id": action.id,
        "action_payload_digest": promotion_action_payload_digest(action),
        "snapshot": snapshot.model_dump(mode="json"),
        "source_fact": source_fact.model_dump(mode="json"),
        "preview_audit_id": preview_event.id,
        "review_audit_id": review_event.id,
        "confirmation_audit_id": confirmation_event.id,
        "impact_audit_id": impact_event.id,
        "reviewed_by": review_event.actor,
        "confirmed_by": confirmation_event.actor,
        "recorded_at": recorded_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
    }
    digest = canonical_json_digest(receipt_payload)
    receipt = ContentResearchFactPromotionReceipt(
        receipt_id=f"content_research_fact_promotion_{digest[:24]}",
        receipt_digest=digest,
        **receipt_payload,
    )
    status, stored = store.record_research_fact_promotion_receipt(receipt)
    if status == "conflict":
        return None, ["Research promotion receipt conflicts with this action."]
    return {
        "receipt_id": stored.receipt_id,
        "status": status,
        "external_write_attempted": False,
    }, []


def _canonical_action_errors(action: ActionObject) -> list[str]:
    errors = validate_research_fact_promotion_action_payload(action.payload)
    if action.id != _promotion_action_id_from_payload(action.payload):
        errors.append("Research promotion action identity is not canonical.")
    if action.status != ActionStatus.ready_to_apply:
        errors.append("Research promotion action is not ready_to_apply.")
    if action.mode != ActionMode.apply:
        errors.append("Research promotion action must use apply mode.")
    return errors


def research_promotion_execution_context_digest(
    action_id: str,
    *,
    promotion_store_identity: str,
    audit_store_identity: str,
) -> str:
    return canonical_json_digest(
        {
            "action_id": action_id,
            "promotion_store_identity": promotion_store_identity,
            "audit_store_identity": audit_store_identity,
        }
    )


def _execution_context_errors(
    action: ActionObject,
    context: ContentResearchFactPromotionExecutionContext,
) -> list[str]:
    if not context.promotion_store_identity or not context.audit_store_identity:
        return ["Research promotion execution stores are not identified."]
    expected = research_promotion_execution_context_digest(
        action.id,
        promotion_store_identity=context.promotion_store_identity,
        audit_store_identity=context.audit_store_identity,
    )
    if context.context_digest != expected:
        return ["Research promotion execution context changed before apply."]
    return []


def _trusted_promotion_audit_event(
    event: AuditEvent,
    principal_receipt: TrustedLocalPrincipalReceipt | None = None,
    *,
    action_id: str | None = None,
    payload_digest: str | None = None,
    snapshot_digest: str | None = None,
) -> bool:
    # A caller label or a hand-written trusted field is never an authority.
    if event.event_type == "action_preview_generated":
        return event.action_id == action_id
    if principal_receipt is None:
        return False
    return (
        event.action_id == action_id
        and event.principal_id == principal_receipt.principal_id
        and event.workspace_id == principal_receipt.workspace_id
        and event.trust_level == principal_receipt.trust_level
        and principal_receipt.action_id == action_id
        and principal_receipt.payload_digest == payload_digest
        and principal_receipt.snapshot_digest == snapshot_digest
        and event.details.get("trusted_local_principal_receipt_id")
        == principal_receipt.receipt_id
        and event.details.get("trusted_local_confirmation_grant_digest")
        == principal_receipt.grant_digest
    )


def _promotion_action_id_from_payload(payload: dict[str, Any]) -> str:
    try:
        snapshot = ContentResearchFactPromotionSnapshot.model_validate(
            payload.get("promotion_snapshot", {})
        )
    except Exception:
        return ""
    return _promotion_action_id(snapshot)


def _persisted_promotion_audit_chain(
    action_id: str,
    snapshot: ContentResearchFactPromotionSnapshot,
    payload_digest: str,
    events: tuple[AuditEvent, ...],
) -> tuple[dict[str, AuditEvent] | None, list[str]]:
    expected_types = (
        "action_preview_generated",
        "human_review_approved_for_prepare",
        "action_apply_confirmed",
        "action_impact_check_completed",
    )
    expected_set = set(expected_types)
    if any(event.action_id != action_id for event in events):
        return None, ["Research promotion audit chain contains a foreign action ID."]
    unexpected = sorted({event.event_type for event in events} - expected_set)
    if unexpected:
        return None, [
            "Research promotion audit chain contains unexpected event types: "
            + ", ".join(unexpected)
            + "."
        ]
    required: dict[str, AuditEvent] = {}
    for event_type in expected_types:
        matches = [event for event in events if event.event_type == event_type]
        if len(matches) == 0:
            return None, [
                "Exact preview, approved review, confirmation and impact check are required."
            ]
        if len(matches) > 1:
            return None, [
                f"Research promotion audit chain has duplicate {event_type} events."
            ]
        required[event_type] = matches[0]
    if len(events) != len(expected_types):
        return None, ["Research promotion audit chain is ambiguous."]
    for event in required.values():
        if not event.actor.strip():
            return None, ["Research promotion audit chain has no persisted actor."]
        if event.created_at.tzinfo is None or event.created_at.utcoffset() is None:
            return None, ["Research promotion audit timestamps must be timezone-aware."]
        snapshot_digest = event.details.get("research_promotion_snapshot_digest")
        if snapshot_digest != snapshot.context_digest:
            snapshot_digest = event.details.get("context_digest")
        if snapshot_digest != snapshot.context_digest:
            return None, ["Research promotion audit chain does not bind current snapshot."]
        action_digest = event.details.get("research_promotion_action_payload_digest")
        if action_digest != payload_digest:
            action_digest = event.details.get("payload_digest")
        if action_digest != payload_digest:
            return None, ["Research promotion audit chain does not bind current action."]
    ordered = [required[event_type] for event_type in expected_types]
    if any(
        earlier.created_at >= later.created_at
        for earlier, later in zip(ordered, ordered[1:], strict=False)
    ):
        return None, ["Research promotion audit chain is not strictly chronological."]
    return required, []


__all__ = [
    "CONTENT_RESEARCH_FACT_PROMOTION_ACTION_TYPE",
    "CONTENT_RESEARCH_FACT_PROMOTION_PREVIEW_CONTRACT",
    "CONTENT_RESEARCH_FACT_PROMOTION_MUTATION_ADAPTER",
    "ContentResearchFactPromotionPreviewCommand",
    "ContentResearchFactPromotionPreviewRequest",
    "ContentResearchFactPromotionPreviewResponse",
    "ContentResearchFactPromotionSnapshot",
    "ContentResearchFactPromotionProposal",
    "ContentResearchFactPromotionReceipt",
    "ContentResearchFactPromotionExecutionContext",
    "execute_research_fact_promotion",
    "load_content_research_fact_promotion_action",
    "promotion_action_payload_digest",
    "research_promotion_execution_context_digest",
    "prepare_research_fact_promotion_preview",
    "validate_research_fact_promotion_action_payload",
]
