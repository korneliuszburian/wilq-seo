"""Audited local disposition receipts bound to one current semantic page row."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.actions.action_chain import revision_bound_action_chain
from wilq.content.canonical.urls import (
    content_is_safe_public_url,
    content_normalized_path,
)
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.per_url_decision_authority import (
    ContentPerUrlCurrentnessProjection,
    ContentPerUrlDecisionObservation,
    per_url_decision_freshness_blocker,
    project_content_per_url_currentness,
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
PER_URL_DISPOSITION_ACTION_TYPE = "content_per_url_disposition_receipt"
PER_URL_DISPOSITION_MUTATION_ADAPTER = "content_per_url_disposition_store"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PerUrlDispositionCandidate(_FrozenModel):
    """Select one stored, fresh semantic row for a supported page disposition."""

    observation_id: str = Field(min_length=1, max_length=240)
    proposed_final_disposition: Literal["keep", "noindex", "redirect", "remove"] = "keep"


class PerUrlDispositionSnapshot(_FrozenModel):
    """Exact reviewed evidence and stable per-URL semantic identity."""

    schema_version: Literal["wilq_per_url_disposition_snapshot_v1"] = (
        "wilq_per_url_disposition_snapshot_v1"
    )
    observation_id: str = Field(min_length=1, max_length=240)
    semantic_row_digest: str = Field(pattern=_HEX64)
    evidence_digest: str = Field(pattern=_HEX64)
    current_work_item_id: str = Field(min_length=1, max_length=240)
    canonical_path: str = Field(min_length=1, max_length=2048)
    public_url: str = Field(min_length=1, max_length=2048)
    proposed_final_disposition: Literal["keep"] = "keep"
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=512)
    context_digest: str = Field(pattern=_HEX64)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item.strip() for item in value):
            raise ValueError("Per-URL disposition evidence IDs must be sorted and unique.")
        return value

    @model_validator(mode="after")
    def require_self_authenticating_context(self) -> Self:
        if (
            not content_is_safe_public_url(self.public_url)
            or content_normalized_path(self.public_url) != self.canonical_path
        ):
            raise ValueError("Per-URL disposition URL identity does not match.")
        if self.context_digest != per_url_disposition_snapshot_digest(self):
            raise ValueError("Per-URL disposition context digest does not match.")
        return self


class PerUrlDispositionProposal(_FrozenModel):
    action_id: str = Field(min_length=1, max_length=240)
    proposal_digest: str = Field(pattern=_HEX64)
    snapshot: PerUrlDispositionSnapshot
    prepared_at: datetime

    @model_validator(mode="after")
    def require_exact_proposal(self) -> Self:
        expected = per_url_disposition_proposal_digest(self.snapshot)
        if (
            self.proposal_digest != expected
            or self.action_id != f"act_per_url_disposition_{expected[:32]}"
        ):
            raise ValueError("Per-URL disposition proposal ID/digest does not match.")
        if self.prepared_at.tzinfo is None or self.prepared_at.utcoffset() is None:
            raise ValueError("Per-URL disposition prepared_at must be timezone-aware.")
        return self


class PerUrlDispositionReceipt(_FrozenModel):
    receipt_id: str = Field(min_length=1, max_length=240)
    receipt_digest: str = Field(pattern=_HEX64)
    action_id: str = Field(min_length=1, max_length=240)
    action_payload_digest: str = Field(pattern=_HEX64)
    snapshot: PerUrlDispositionSnapshot
    preview_audit_id: str = Field(min_length=1, max_length=240)
    review_audit_id: str = Field(min_length=1, max_length=240)
    confirmation_audit_id: str = Field(min_length=1, max_length=240)
    impact_audit_id: str = Field(min_length=1, max_length=240)
    reviewed_by: str = Field(min_length=1, max_length=240)
    confirmed_by: str = Field(min_length=1, max_length=240)

    @model_validator(mode="after")
    def require_self_authenticating_receipt(self) -> Self:
        expected = per_url_disposition_receipt_digest(self)
        proposal_digest = per_url_disposition_proposal_digest(self.snapshot)
        if self.action_id != f"act_per_url_disposition_{proposal_digest[:32]}":
            raise ValueError("Per-URL disposition receipt action ID does not match snapshot.")
        if self.receipt_digest != expected or self.receipt_id != (
            f"content_per_url_disposition_receipt_{expected[:24]}"
        ):
            raise ValueError("Per-URL disposition receipt digest does not match.")
        return self


class PerUrlDispositionBlocker(_FrozenModel):
    code: str = Field(min_length=1, max_length=160)
    owner: str = Field(min_length=1, max_length=160)
    evidence_ids: tuple[str, ...] = ()
    safe_next_step: str = Field(min_length=1, max_length=600)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item.strip() for item in value):
            raise ValueError("Per-URL disposition blocker evidence must be sorted and unique.")
        return value


class PerUrlDispositionProjection(_FrozenModel):
    status: Literal["missing", "preview_ready", "blocked", "current"]
    action: ActionObject | None = None
    receipt: PerUrlDispositionReceipt | None = None
    blockers: tuple[PerUrlDispositionBlocker, ...] = ()
    safe_next_step: str = "Przygotuj aktualny per-URL disposition preview."

    @model_validator(mode="after")
    def require_typed_state(self) -> Self:
        if self.status == "current" and (self.action is None or self.receipt is None):
            raise ValueError("Current per-URL disposition requires its exact receipt.")
        if (
            self.status == "current"
            and self.action is not None
            and self.action.status == ActionStatus.blocked
        ):
            raise ValueError("Blocked per-URL disposition cannot be reported as current.")
        if self.status == "blocked" and not self.blockers:
            raise ValueError("Blocked per-URL disposition requires a typed blocker.")
        if self.status == "blocked" and self.safe_next_step != self.blockers[0].safe_next_step:
            raise ValueError("Per-URL disposition next step must match its first blocker.")
        if self.status == "missing" and self.receipt is not None:
            raise ValueError("Missing per-URL disposition cannot carry a receipt.")
        if (
            self.receipt is not None
            and self.action is not None
            and self.receipt.action_id != self.action.id
        ):
            raise ValueError("Per-URL disposition receipt and ActionObject do not match.")
        return self


class PerUrlDispositionPreviewResponse(_FrozenModel):
    status: Literal["preview_ready", "blocked"]
    action: ActionObject | None = None
    blockers: tuple[PerUrlDispositionBlocker, ...] = ()

    @model_validator(mode="after")
    def require_preview_state(self) -> Self:
        if self.status == "blocked" and not self.blockers:
            raise ValueError("Blocked per-URL disposition preview requires a typed blocker.")
        if self.status == "preview_ready" and self.action is None:
            raise ValueError("Ready per-URL disposition preview requires an ActionObject.")
        return self


def per_url_disposition_snapshot_digest(
    value: PerUrlDispositionSnapshot | dict[str, Any],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("context_digest", None)
    return canonical_json_digest(payload)


def per_url_disposition_proposal_digest(snapshot: PerUrlDispositionSnapshot) -> str:
    return canonical_json_digest(
        {
            "schema_version": "wilq_per_url_disposition_proposal_v1",
            "observation_id": snapshot.observation_id,
            "semantic_row_digest": snapshot.semantic_row_digest,
            "proposed_final_disposition": snapshot.proposed_final_disposition,
        }
    )


def per_url_disposition_receipt_digest(
    value: PerUrlDispositionReceipt | dict[str, Any],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("receipt_id", None)
    payload.pop("receipt_digest", None)
    return canonical_json_digest(payload)


def per_url_disposition_action_payload_digest(action: ActionObject) -> str:
    return canonical_json_digest(action.payload)


def build_per_url_disposition_proposal(
    observation: ContentPerUrlDecisionObservation,
) -> PerUrlDispositionProposal:
    identity = observation.page_identity
    policy = observation.policy_facts
    evidence_ids = tuple(
        sorted(
            set(identity.current_evidence_ids)
            | set(identity.catalog_evidence_ids)
            | set(policy.freshness_evidence_ids)
            | {evidence_id for fact in policy.source_facts for evidence_id in fact.evidence_ids}
        )
    )
    provisional_snapshot = {
        "schema_version": "wilq_per_url_disposition_snapshot_v1",
        "observation_id": observation.observation_id,
        "semantic_row_digest": observation.semantic_row_digest,
        "evidence_digest": observation.evidence_digest,
        "current_work_item_id": policy.current_work_item_id,
        "canonical_path": policy.canonical_path,
        "public_url": policy.public_url,
        "proposed_final_disposition": "keep",
        "evidence_ids": evidence_ids,
        "context_digest": "0" * 64,
    }
    snapshot = PerUrlDispositionSnapshot.model_validate(
        provisional_snapshot
        | {"context_digest": per_url_disposition_snapshot_digest(provisional_snapshot)}
    )
    proposal_digest = per_url_disposition_proposal_digest(snapshot)
    return PerUrlDispositionProposal(
        action_id=f"act_per_url_disposition_{proposal_digest[:32]}",
        proposal_digest=proposal_digest,
        snapshot=snapshot,
        prepared_at=datetime.now(UTC),
    )


def build_per_url_disposition_action(proposal: PerUrlDispositionProposal) -> ActionObject:
    snapshot = proposal.snapshot
    return ActionObject(
        id=proposal.action_id,
        title="Zatwierdź zachowanie bieżącej strony",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply,
        evidence_ids=list(snapshot.evidence_ids),
        human_diagnosis=(
            f"Propozycja zachowania dokładnego adresu {snapshot.public_url}; "
            "decyzja wiąże się z per-URL semantic row."
        ),
        recommended_reason="Sprawdź bieżące źródła i zatwierdź lokalny receipt dla tego adresu.",
        payload={
            "action_type": PER_URL_DISPOSITION_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "apply",
            "local_authority_only": True,
            "per_url_disposition_authority": snapshot.model_dump(mode="json"),
            "payload_preview": [
                {
                    "id": snapshot.observation_id,
                    "operation_type": "record_per_url_disposition_receipt",
                    "public_url": snapshot.public_url,
                    "canonical_path": snapshot.canonical_path,
                    "proposed_final_disposition": "keep",
                    "semantic_row_digest": snapshot.semantic_row_digest,
                    "generation_allowed": False,
                    "external_write_attempted": False,
                    "mutation_adapter": PER_URL_DISPOSITION_MUTATION_ADAPTER,
                }
            ],
            "apply_allowed": True,
            "api_mutation_ready": True,
            "generation_allowed": False,
            "destructive": False,
        },
        validation_status="not_validated",
        created_by="system_core_per_url_disposition_authority",
        created_at=proposal.prepared_at,
        updated_at=proposal.prepared_at,
    )


def prepare_per_url_disposition_preview(
    store: Any,
    candidate: PerUrlDispositionCandidate,
    *,
    now: datetime | None = None,
) -> PerUrlDispositionPreviewResponse:
    if candidate.proposed_final_disposition != "keep":
        return PerUrlDispositionPreviewResponse(
            status="blocked",
            blockers=(
                PerUrlDispositionBlocker(
                    code="technical_seo_disposition_requires_its_exact_owner",
                    owner="WILQ technical SEO",
                    safe_next_step=(
                        "Przygotuj osobny exact technical-SEO ActionObject z bieżących "
                        "dowodów dla tego URL-a."
                    ),
                ),
            ),
        )
    observation = store.load_content_per_url_decision_observation(candidate.observation_id)
    if observation is None:
        return PerUrlDispositionPreviewResponse(
            status="blocked",
            blockers=(
                _blocker(
                    "per_url_observation_missing", (), "Odczytaj aktualny semantic row URL-a."
                ),
            ),
        )
    blockers = per_url_disposition_blockers(store, observation, now=now)
    if blockers:
        return PerUrlDispositionPreviewResponse(status="blocked", blockers=blockers)
    proposal = store.record_per_url_disposition_proposal(
        build_per_url_disposition_proposal(observation)
    )
    action = build_per_url_disposition_action(proposal)
    return PerUrlDispositionPreviewResponse(status="preview_ready", action=action)


def read_per_url_disposition_authority(
    store: Any,
    *,
    action_id: str,
    now: datetime | None = None,
) -> PerUrlDispositionProjection:
    proposal = store.load_per_url_disposition_proposal(action_id)
    if proposal is None:
        return PerUrlDispositionProjection(status="missing")
    receipt = store.load_per_url_disposition_receipt(action_id)
    action = build_per_url_disposition_action(proposal)
    observation = store.load_content_per_url_decision_observation(proposal.snapshot.observation_id)
    blockers = (
        (_blocker("per_url_observation_missing", (), "Odczytaj aktualny semantic row URL-a."),)
        if observation is None
        else per_url_disposition_blockers(store, observation, now=now)
    )
    if blockers:
        _block_action(action, blockers)
        return PerUrlDispositionProjection(
            status="blocked",
            action=action,
            receipt=receipt,
            blockers=blockers,
            safe_next_step=blockers[0].safe_next_step,
        )
    return PerUrlDispositionProjection(
        status="current" if receipt is not None else "preview_ready",
        action=action,
        receipt=receipt,
    )


def load_per_url_disposition_action(action_id: str) -> ActionObject | None:
    from wilq.content.workflow.store.store import content_workflow_store

    projection = read_per_url_disposition_authority(content_workflow_store(), action_id=action_id)
    return projection.action


def per_url_disposition_blockers(
    store: Any,
    observation: ContentPerUrlDecisionObservation,
    *,
    now: datetime | None = None,
) -> tuple[PerUrlDispositionBlocker, ...]:
    checked_at = now or datetime.now(UTC)
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        return (
            _blocker(
                "per_url_freshness_check_time_invalid",
                observation.policy_facts.freshness_evidence_ids,
                "Odczytaj ponownie freshness wymaganych źródeł.",
            ),
        )
    checked_at = checked_at.astimezone(UTC)
    freshness = per_url_decision_freshness_blocker(observation.policy_facts, checked_at)
    if freshness is not None:
        return (
            _blocker(freshness[0], observation.policy_facts.freshness_evidence_ids, freshness[1]),
        )
    observations = store.list_content_per_url_decision_observations_for_scope(
        canonical_path=observation.policy_facts.canonical_path,
        current_work_item_id=observation.policy_facts.current_work_item_id,
    )
    current = observations[-1] if observations else None
    projection: ContentPerUrlCurrentnessProjection = project_content_per_url_currentness(
        observation, current
    )
    if projection.status == "blocked":
        return (
            _blocker(
                projection.blocker_code or "per_url_currentness_blocked",
                (),
                projection.safe_next_step,
            ),
        )
    if projection.status == "superseded":
        return (_blocker("per_url_semantic_row_superseded", (), projection.safe_next_step),)
    current_freshness = (
        None
        if current is None
        else per_url_decision_freshness_blocker(current.policy_facts, checked_at)
    )
    if current_freshness is not None:
        return (
            _blocker(
                current_freshness[0],
                current.policy_facts.freshness_evidence_ids if current else (),
                current_freshness[1],
            ),
        )
    return ()


def execute_per_url_disposition_authority(
    action: ActionObject,
    *,
    store: Any,
    audit_events: list[AuditEvent],
    confirmed_by: str | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    proposal = store.load_per_url_disposition_proposal(action.id)
    if proposal is None:
        return None, ["Per-URL disposition proposal is missing."]
    expected = build_per_url_disposition_action(proposal)
    if action.payload != expected.payload:
        return None, ["Per-URL disposition ActionObject changed before apply."]
    observation = store.load_content_per_url_decision_observation(proposal.snapshot.observation_id)
    if observation is None or per_url_disposition_blockers(store, observation, now=now):
        return None, ["Per-URL semantic row or required source freshness changed before apply."]
    payload_digest = per_url_disposition_action_payload_digest(action)
    chain, blockers = revision_bound_action_chain(
        [event for event in audit_events if event.action_id == action.id],
        confirmed_by=confirmed_by or _confirmation_actor(audit_events),
        binding_from_event=_audit_binding,
        expected_binding=(proposal.snapshot.context_digest, payload_digest),
    )
    if chain is None:
        return None, [
            blockers[0].reason if blockers else "Per-URL disposition audit chain is invalid."
        ]
    preview, review, confirmation, impact = chain
    receipt = build_per_url_disposition_receipt(
        action=action,
        proposal=proposal,
        preview_audit_id=preview.id,
        review_audit_id=review.id,
        confirmation_audit_id=confirmation.id,
        impact_audit_id=impact.id,
        reviewed_by=review.actor,
        confirmed_by=confirmation.actor,
    )
    status, stored = store.record_per_url_disposition_receipt(receipt)
    if status == "conflict":
        return None, ["Per-URL disposition receipt conflicts with its ActionObject."]
    return {
        "receipt_id": stored.receipt_id,
        "status": status,
        "generation_allowed": False,
        "external_write_attempted": False,
    }, []


def build_per_url_disposition_receipt(
    *,
    action: ActionObject,
    proposal: PerUrlDispositionProposal,
    preview_audit_id: str,
    review_audit_id: str,
    confirmation_audit_id: str,
    impact_audit_id: str,
    reviewed_by: str,
    confirmed_by: str,
) -> PerUrlDispositionReceipt:
    provisional = {
        "receipt_id": "",
        "receipt_digest": "0" * 64,
        "action_id": action.id,
        "action_payload_digest": per_url_disposition_action_payload_digest(action),
        "snapshot": proposal.snapshot.model_dump(mode="json"),
        "preview_audit_id": preview_audit_id,
        "review_audit_id": review_audit_id,
        "confirmation_audit_id": confirmation_audit_id,
        "impact_audit_id": impact_audit_id,
        "reviewed_by": reviewed_by,
        "confirmed_by": confirmed_by,
    }
    digest = per_url_disposition_receipt_digest(provisional)
    return PerUrlDispositionReceipt.model_validate(
        provisional
        | {
            "receipt_id": f"content_per_url_disposition_receipt_{digest[:24]}",
            "receipt_digest": digest,
        }
    )


def validate_per_url_disposition_action_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("action_type") != PER_URL_DISPOSITION_ACTION_TYPE:
        errors.append("Per-URL disposition action type is invalid.")
    if payload.get("local_authority_only") is not True:
        errors.append("Per-URL disposition must remain local-only.")
    try:
        PerUrlDispositionSnapshot.model_validate(payload.get("per_url_disposition_authority", {}))
    except Exception:
        errors.append("Per-URL disposition snapshot is invalid.")
    return errors


def _audit_binding(event: AuditEvent) -> tuple[str, str] | None:
    context = event.details.get("per_url_disposition_snapshot_digest")
    payload = event.details.get("per_url_disposition_action_payload_digest")
    return (context, payload) if isinstance(context, str) and isinstance(payload, str) else None


def _confirmation_actor(events: list[AuditEvent]) -> str:
    confirmations = sorted(
        (event for event in events if event.event_type == "action_apply_confirmed"),
        key=lambda event: (event.created_at, event.id),
        reverse=True,
    )
    return confirmations[0].actor if confirmations else ""


def _blocker(
    code: str,
    evidence_ids: tuple[str, ...],
    safe_next_step: str,
) -> PerUrlDispositionBlocker:
    return PerUrlDispositionBlocker(
        code=code,
        owner="WILQ content workflow",
        evidence_ids=tuple(sorted(set(evidence_ids))),
        safe_next_step=safe_next_step,
    )


def _block_action(action: ActionObject, blockers: tuple[PerUrlDispositionBlocker, ...]) -> None:
    action.status = ActionStatus.blocked
    action.payload["runtime_blockers"] = [item.code for item in blockers]
    action.payload["apply_allowed"] = False
    action.payload["api_mutation_ready"] = False


__all__ = [
    "PER_URL_DISPOSITION_ACTION_TYPE",
    "PER_URL_DISPOSITION_MUTATION_ADAPTER",
    "PerUrlDispositionCandidate",
    "PerUrlDispositionPreviewResponse",
    "PerUrlDispositionProjection",
    "PerUrlDispositionReceipt",
    "PerUrlDispositionSnapshot",
    "build_per_url_disposition_action",
    "build_per_url_disposition_proposal",
    "build_per_url_disposition_receipt",
    "execute_per_url_disposition_authority",
    "load_per_url_disposition_action",
    "per_url_disposition_action_payload_digest",
    "per_url_disposition_blockers",
    "prepare_per_url_disposition_preview",
    "read_per_url_disposition_authority",
    "validate_per_url_disposition_action_payload",
]
