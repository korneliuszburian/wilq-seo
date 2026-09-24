"""Audited delivery identity receipts bound to one current per-URL semantic row."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.actions.action_chain import revision_bound_action_chain
from wilq.content.canonical.urls import content_is_safe_public_url, content_normalized_path
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.per_url_decision_authority import (
    per_url_decision_freshness_blocker,
    project_content_per_url_currentness,
)
from wilq.content.workflow.per_url_disposition_authority import (
    PerUrlDispositionReceipt,
    read_per_url_disposition_authority,
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
PER_URL_DELIVERY_IDENTITY_ACTION_TYPE = "content_per_url_delivery_identity_binding"
PER_URL_DELIVERY_IDENTITY_MUTATION_ADAPTER = "content_per_url_delivery_identity_store"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PerUrlDeliveryIdentityCandidate(_FrozenModel):
    """Select a persisted per-URL KEEP receipt without claiming URL or row data."""

    disposition_action_id: str = Field(min_length=1, max_length=240)


class PerUrlDeliveryIdentitySnapshot(_FrozenModel):
    """Exact reviewed evidence plus stable page semantics, never a batch-run key."""

    schema_version: Literal["wilq_per_url_delivery_identity_snapshot_v1"] = (
        "wilq_per_url_delivery_identity_snapshot_v1"
    )
    disposition_action_id: str = Field(min_length=1, max_length=240)
    disposition_receipt_id: str = Field(min_length=1, max_length=240)
    disposition_receipt_digest: str = Field(pattern=_HEX64)
    observation_id: str = Field(min_length=1, max_length=240)
    semantic_row_digest: str = Field(pattern=_HEX64)
    evidence_digest: str = Field(pattern=_HEX64)
    current_work_item_id: str = Field(min_length=1, max_length=240)
    canonical_path: str = Field(min_length=1, max_length=2048)
    public_url: str = Field(min_length=1, max_length=2048)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=512)
    context_digest: str = Field(pattern=_HEX64)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item.strip() for item in value):
            raise ValueError("Per-URL delivery identity evidence must be sorted and unique.")
        return value

    @model_validator(mode="after")
    def require_exact_page_and_digest(self) -> Self:
        if (
            not content_is_safe_public_url(self.public_url)
            or content_normalized_path(self.public_url) != self.canonical_path
        ):
            raise ValueError("Per-URL delivery identity URL/path does not match.")
        if self.context_digest != per_url_delivery_identity_snapshot_digest(self):
            raise ValueError("Per-URL delivery identity context digest does not match.")
        return self


class PerUrlDeliveryIdentityProposal(_FrozenModel):
    action_id: str = Field(min_length=1, max_length=240)
    proposal_digest: str = Field(pattern=_HEX64)
    snapshot: PerUrlDeliveryIdentitySnapshot
    prepared_at: datetime

    @model_validator(mode="after")
    def require_exact_proposal(self) -> Self:
        expected = per_url_delivery_identity_proposal_digest(self.snapshot)
        if (
            self.proposal_digest != expected
            or self.action_id != f"act_per_url_delivery_identity_{expected[:32]}"
        ):
            raise ValueError("Per-URL delivery identity proposal ID/digest does not match.")
        if self.prepared_at.tzinfo is None or self.prepared_at.utcoffset() is None:
            raise ValueError("Per-URL delivery identity prepared_at must be timezone-aware.")
        return self


class PerUrlDeliveryIdentityBinding(_FrozenModel):
    """Immutable current identity receipt consumed by the next per-URL stage."""

    schema_version: Literal["wilq_per_url_delivery_identity_binding_v1"] = (
        "wilq_per_url_delivery_identity_binding_v1"
    )
    status: Literal["exact_current"] = "exact_current"
    binding_id: str = Field(min_length=1, max_length=240)
    binding_digest: str = Field(pattern=_HEX64)
    action_id: str = Field(min_length=1, max_length=240)
    action_payload_digest: str = Field(pattern=_HEX64)
    snapshot: PerUrlDeliveryIdentitySnapshot
    preview_audit_id: str = Field(min_length=1, max_length=240)
    review_audit_id: str = Field(min_length=1, max_length=240)
    confirmation_audit_id: str = Field(min_length=1, max_length=240)
    impact_audit_id: str = Field(min_length=1, max_length=240)
    reviewed_by: str = Field(min_length=1, max_length=240)
    confirmed_by: str = Field(min_length=1, max_length=240)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def require_aware_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Per-URL delivery identity time must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_self_authenticating_binding(self) -> Self:
        proposal_digest = per_url_delivery_identity_proposal_digest(self.snapshot)
        if self.action_id != f"act_per_url_delivery_identity_{proposal_digest[:32]}":
            raise ValueError("Per-URL delivery identity action ID does not match its snapshot.")
        expected_digest = per_url_delivery_identity_binding_digest(self)
        expected_id = f"content_per_url_delivery_identity_{expected_digest[:24]}"
        if self.binding_digest != expected_digest or self.binding_id != expected_id:
            raise ValueError("Per-URL delivery identity binding ID/digest does not match.")
        return self


class PerUrlDeliveryIdentityBlocker(_FrozenModel):
    code: str = Field(min_length=1, max_length=160)
    owner: str = Field(min_length=1, max_length=160)
    evidence_ids: tuple[str, ...] = ()
    safe_next_step: str = Field(min_length=1, max_length=600)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item.strip() for item in value):
            raise ValueError("Per-URL identity blocker evidence must be sorted and unique.")
        return value


class PerUrlDeliveryIdentityProjection(_FrozenModel):
    status: Literal["missing", "preview_ready", "blocked", "current"]
    action: ActionObject | None = None
    binding: PerUrlDeliveryIdentityBinding | None = None
    blockers: tuple[PerUrlDeliveryIdentityBlocker, ...] = ()
    safe_next_step: str = "Przygotuj bieżące identity exact URL-a."

    @model_validator(mode="after")
    def require_typed_projection(self) -> Self:
        if self.status == "current" and (self.action is None or self.binding is None):
            raise ValueError("Current per-URL identity requires its exact binding.")
        if (
            self.status == "current"
            and self.action is not None
            and self.action.status == ActionStatus.blocked
        ):
            raise ValueError("Blocked per-URL identity cannot be reported as current.")
        if self.status == "blocked" and not self.blockers:
            raise ValueError("Blocked per-URL identity requires a typed blocker.")
        if self.status == "blocked" and self.safe_next_step != self.blockers[0].safe_next_step:
            raise ValueError("Per-URL identity next step must match its first blocker.")
        if (
            self.binding is not None
            and self.action is not None
            and self.binding.action_id != self.action.id
        ):
            raise ValueError("Per-URL identity binding and ActionObject do not match.")
        return self


class PerUrlDeliveryIdentityPreviewResponse(_FrozenModel):
    status: Literal["preview_ready", "blocked"]
    action: ActionObject | None = None
    blockers: tuple[PerUrlDeliveryIdentityBlocker, ...] = ()

    @model_validator(mode="after")
    def require_preview_state(self) -> Self:
        if self.status == "blocked" and not self.blockers:
            raise ValueError("Blocked per-URL identity preview requires a typed blocker.")
        if self.status == "preview_ready" and self.action is None:
            raise ValueError("Ready per-URL identity preview requires an ActionObject.")
        return self


class PerUrlDeliveryIdentityAuthorityBlocked(ValueError):
    def __init__(
        self,
        code: str,
        owner: str,
        evidence_ids: tuple[str, ...],
        safe_next_step: str,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.owner = owner
        self.evidence_ids = tuple(sorted(set(evidence_ids)))
        self.safe_next_step = safe_next_step


def per_url_delivery_identity_snapshot_digest(
    value: PerUrlDeliveryIdentitySnapshot | dict[str, Any],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("context_digest", None)
    return canonical_json_digest(payload)


def per_url_delivery_identity_proposal_digest(
    snapshot: PerUrlDeliveryIdentitySnapshot,
) -> str:
    return canonical_json_digest(
        {
            "schema_version": "wilq_per_url_delivery_identity_proposal_v1",
            "context_digest": snapshot.context_digest,
        }
    )


def per_url_delivery_identity_binding_digest(
    value: PerUrlDeliveryIdentityBinding | dict[str, Any],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("binding_id", None)
    payload.pop("binding_digest", None)
    return canonical_json_digest(payload)


def per_url_delivery_identity_action_payload_digest(action: ActionObject) -> str:
    return canonical_json_digest(action.payload)


def build_per_url_delivery_identity_snapshot(
    store: Any,
    candidate: PerUrlDeliveryIdentityCandidate,
    *,
    now: datetime | None = None,
) -> PerUrlDeliveryIdentitySnapshot:
    projection = read_per_url_disposition_authority(
        store, action_id=candidate.disposition_action_id, now=now
    )
    if projection.status != "current" or projection.receipt is None:
        blocker = projection.blockers[0] if projection.blockers else None
        if blocker is None:
            raise PerUrlDeliveryIdentityAuthorityBlocked(
                "per_url_disposition_not_approved",
                "Wilku",
                (),
                "Zatwierdź dokładny per-URL receipt KEEP przed utworzeniem identity.",
            )
        raise PerUrlDeliveryIdentityAuthorityBlocked(
            blocker.code,
            blocker.owner,
            blocker.evidence_ids,
            blocker.safe_next_step,
        )
    disposition: PerUrlDispositionReceipt = projection.receipt
    observations = store.list_content_per_url_decision_observations_for_scope(
        canonical_path=disposition.snapshot.canonical_path,
        current_work_item_id=disposition.snapshot.current_work_item_id,
    )
    observation = observations[-1] if observations else None
    if observation is None:
        raise _observation_blocker(disposition.snapshot.evidence_ids)
    disposition_observation = store.load_content_per_url_decision_observation(
        disposition.snapshot.observation_id
    )
    if disposition_observation is None:
        raise _observation_blocker(disposition.snapshot.evidence_ids)
    projection_current = project_content_per_url_currentness(
        disposition_observation, observation
    )
    if projection_current.status != "current":
        raise PerUrlDeliveryIdentityAuthorityBlocked(
            projection_current.blocker_code or "per_url_semantic_row_superseded",
            projection_current.blocker_owner or "WILQ content workflow",
            (),
            projection_current.safe_next_step,
        )
    freshness = per_url_decision_freshness_blocker(
        observation.policy_facts, now or datetime.now(UTC)
    )
    if freshness is not None:
        raise PerUrlDeliveryIdentityAuthorityBlocked(
            freshness[0],
            "WILQ content workflow",
            observation.policy_facts.freshness_evidence_ids,
            freshness[1],
        )
    if (
        observation.semantic_row_digest != disposition.snapshot.semantic_row_digest
        or disposition.snapshot.proposed_final_disposition != "keep"
    ):
        raise PerUrlDeliveryIdentityAuthorityBlocked(
            "per_url_semantic_row_superseded",
            "WILQ content workflow",
            observation.policy_facts.freshness_evidence_ids,
            "Odczytaj bieżący semantic row i przygotuj nowy per-URL receipt KEEP.",
        )
    evidence_ids = tuple(
        sorted(
            set(observation.page_identity.current_evidence_ids)
            | set(observation.page_identity.catalog_evidence_ids)
            | set(observation.policy_facts.freshness_evidence_ids)
            | {
                evidence_id
                for fact in observation.policy_facts.source_facts
                for evidence_id in fact.evidence_ids
            }
        )
    )
    values: dict[str, object] = {
        "schema_version": "wilq_per_url_delivery_identity_snapshot_v1",
        "disposition_action_id": disposition.action_id,
        "disposition_receipt_id": disposition.receipt_id,
        "disposition_receipt_digest": disposition.receipt_digest,
        "observation_id": observation.observation_id,
        "semantic_row_digest": observation.semantic_row_digest,
        "evidence_digest": observation.evidence_digest,
        "current_work_item_id": observation.policy_facts.current_work_item_id,
        "canonical_path": observation.policy_facts.canonical_path,
        "public_url": observation.policy_facts.public_url,
        "evidence_ids": evidence_ids,
        "context_digest": "0" * 64,
    }
    return PerUrlDeliveryIdentitySnapshot.model_validate(
        values | {"context_digest": per_url_delivery_identity_snapshot_digest(values)}
    )


def build_per_url_delivery_identity_proposal(
    snapshot: PerUrlDeliveryIdentitySnapshot,
) -> PerUrlDeliveryIdentityProposal:
    proposal_digest = per_url_delivery_identity_proposal_digest(snapshot)
    return PerUrlDeliveryIdentityProposal(
        action_id=f"act_per_url_delivery_identity_{proposal_digest[:32]}",
        proposal_digest=proposal_digest,
        snapshot=snapshot,
        prepared_at=datetime.now(UTC),
    )


def build_per_url_delivery_identity_action(
    proposal: PerUrlDeliveryIdentityProposal,
) -> ActionObject:
    snapshot = proposal.snapshot
    return ActionObject(
        id=proposal.action_id,
        title="Zapisz identity bieżącej strony",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply,
        evidence_ids=list(snapshot.evidence_ids),
        human_diagnosis=(
            f"Identity wiąże exact adres {snapshot.public_url} z bieżącym per-URL semantic row."
        ),
        recommended_reason=(
            "Sprawdź keep receipt i świeżość dowodów dokładnej strony, potem "
            "zapisz lokalne identity."
        ),
        payload={
            "action_type": PER_URL_DELIVERY_IDENTITY_ACTION_TYPE,
            "connector": "wordpress_ekologus",
            "mode": "apply",
            "local_authority_only": True,
            "per_url_delivery_identity_authority": snapshot.model_dump(mode="json"),
            "payload_preview": [
                {
                    "id": snapshot.observation_id,
                    "operation_type": "record_per_url_delivery_identity_binding",
                    "current_work_item_id": snapshot.current_work_item_id,
                    "canonical_path": snapshot.canonical_path,
                    "public_url": snapshot.public_url,
                    "disposition_receipt_id": snapshot.disposition_receipt_id,
                    "semantic_row_digest": snapshot.semantic_row_digest,
                    "generation_allowed": False,
                    "external_write_attempted": False,
                    "mutation_adapter": PER_URL_DELIVERY_IDENTITY_MUTATION_ADAPTER,
                }
            ],
            "apply_allowed": True,
            "api_mutation_ready": True,
            "generation_allowed": False,
            "external_write_attempted": False,
            "destructive": False,
        },
        validation_status="not_validated",
        created_by="system_core_per_url_delivery_identity_authority",
        created_at=proposal.prepared_at,
        updated_at=proposal.prepared_at,
    )


def prepare_per_url_delivery_identity_preview(
    store: Any,
    candidate: PerUrlDeliveryIdentityCandidate,
    *,
    now: datetime | None = None,
) -> PerUrlDeliveryIdentityPreviewResponse:
    try:
        snapshot = build_per_url_delivery_identity_snapshot(store, candidate, now=now)
    except PerUrlDeliveryIdentityAuthorityBlocked as error:
        return PerUrlDeliveryIdentityPreviewResponse(
            status="blocked",
            blockers=(
                _blocker(error.code, error.owner, error.evidence_ids, error.safe_next_step),
            ),
        )
    try:
        proposal = store.record_per_url_delivery_identity_proposal(
            build_per_url_delivery_identity_proposal(snapshot)
        )
    except ValueError:
        return PerUrlDeliveryIdentityPreviewResponse(
            status="blocked",
            blockers=(
                _blocker(
                    "per_url_delivery_identity_proposal_conflict",
                    "WILQ content workflow",
                    snapshot.evidence_ids,
                    "Odczytaj ponownie bieżący per-URL receipt i przygotuj nowe identity preview.",
                ),
            ),
        )
    action = per_url_delivery_identity_action_for_proposal(store, proposal, now=now)
    blockers = _action_blockers(action)
    return PerUrlDeliveryIdentityPreviewResponse(
        status="blocked" if blockers else "preview_ready",
        action=action,
        blockers=blockers,
    )


def read_per_url_delivery_identity_authority(
    store: Any,
    *,
    action_id: str,
    now: datetime | None = None,
) -> PerUrlDeliveryIdentityProjection:
    proposal = store.load_per_url_delivery_identity_proposal(action_id)
    if proposal is None:
        return PerUrlDeliveryIdentityProjection(status="missing")
    binding = store.load_per_url_delivery_identity_binding_by_action(action_id)
    if binding is not None:
        action = build_per_url_delivery_identity_action(proposal)
        blockers = per_url_delivery_identity_blockers(store, binding, now=now)
        if blockers:
            _block_action(action, blockers[0])
        else:
            return PerUrlDeliveryIdentityProjection(
                status="current", action=action, binding=binding
            )
    else:
        action = per_url_delivery_identity_action_for_proposal(store, proposal, now=now)
        blockers = _action_blockers(action)
    if blockers:
        return PerUrlDeliveryIdentityProjection(
            status="blocked",
            action=action,
            binding=binding,
            blockers=blockers,
            safe_next_step=blockers[0].safe_next_step,
        )
    return PerUrlDeliveryIdentityProjection(
        status="current" if binding is not None else "preview_ready",
        action=action,
        binding=binding,
    )


def per_url_delivery_identity_blockers(
    store: Any,
    binding: PerUrlDeliveryIdentityBinding,
    *,
    now: datetime | None = None,
) -> tuple[PerUrlDeliveryIdentityBlocker, ...]:
    checked_at = datetime.now(UTC) if now is None else now
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        return (
            _blocker(
                "per_url_freshness_check_time_invalid",
                "WILQ content workflow",
                binding.snapshot.evidence_ids,
                "Odczytaj ponownie freshness wymaganych źródeł.",
            ),
        )
    checked_at = checked_at.astimezone(UTC)
    for blocker in (
        _current_disposition_blocker(store, binding, checked_at),
        _current_semantic_row_blocker(store, binding, checked_at),
    ):
        if blocker is not None:
            return (blocker,)
    return ()


def _current_disposition_blocker(
    store: Any,
    binding: PerUrlDeliveryIdentityBinding,
    checked_at: datetime,
) -> PerUrlDeliveryIdentityBlocker | None:
    disposition = store.load_per_url_disposition_receipt(
        binding.snapshot.disposition_action_id
    )
    if (
        disposition is None
        or disposition.receipt_id != binding.snapshot.disposition_receipt_id
        or disposition.receipt_digest != binding.snapshot.disposition_receipt_digest
    ):
        return _blocker(
            "per_url_disposition_receipt_changed",
            "WILQ content workflow",
            binding.snapshot.evidence_ids,
            "Odczytaj ponownie zatwierdzony per-URL receipt KEEP.",
        )
    if (
        disposition.snapshot.semantic_row_digest != binding.snapshot.semantic_row_digest
        or disposition.snapshot.current_work_item_id
        != binding.snapshot.current_work_item_id
        or disposition.snapshot.canonical_path != binding.snapshot.canonical_path
        or disposition.snapshot.public_url != binding.snapshot.public_url
    ):
        return _blocker(
            "per_url_identity_disposition_mismatch",
            "WILQ content workflow",
            binding.snapshot.evidence_ids,
            "Odtwórz identity z exact KEEP receipt i tym samym per-URL semantic row.",
        )
    disposition_current = read_per_url_disposition_authority(
        store, action_id=disposition.action_id, now=checked_at
    )
    if disposition_current.status != "current":
        blocker = disposition_current.blockers[0] if disposition_current.blockers else None
        return _blocker(
            "per_url_disposition_not_current" if blocker is None else blocker.code,
            "WILQ content workflow" if blocker is None else blocker.owner,
            binding.snapshot.evidence_ids if blocker is None else blocker.evidence_ids,
            "Odczytaj bieżący per-URL receipt KEEP przed kolejnym krokiem."
            if blocker is None
            else blocker.safe_next_step,
        )
    return None


def _current_semantic_row_blocker(
    store: Any,
    binding: PerUrlDeliveryIdentityBinding,
    checked_at: datetime,
) -> PerUrlDeliveryIdentityBlocker | None:
    bound = store.load_content_per_url_decision_observation(binding.snapshot.observation_id)
    if bound is None:
        return _blocker(
            "per_url_observation_missing",
            "WILQ content workflow",
            binding.snapshot.evidence_ids,
            "Odczytaj ponownie świeży semantic row dokładnego URL-a.",
        )
    if bound.semantic_row_digest != binding.snapshot.semantic_row_digest:
        return _blocker(
            "per_url_identity_binding_invalid",
            "WILQ content workflow",
            binding.snapshot.evidence_ids,
            "Odtwórz exact identity na podstawie bieżącego semantic row.",
        )
    observations = store.list_content_per_url_decision_observations_for_scope(
        canonical_path=binding.snapshot.canonical_path,
        current_work_item_id=binding.snapshot.current_work_item_id,
    )
    current = observations[-1] if observations else None
    projection = project_content_per_url_currentness(bound, current)
    if projection.status != "current":
        return _blocker(
            projection.blocker_code or "per_url_semantic_row_superseded",
            projection.blocker_owner or "WILQ content workflow",
            (),
            projection.safe_next_step,
        )
    assert current is not None
    freshness = per_url_decision_freshness_blocker(current.policy_facts, checked_at)
    if freshness is not None:
        return _blocker(
            freshness[0],
            "WILQ content workflow",
            current.policy_facts.freshness_evidence_ids,
            freshness[1],
        )
    return None


def per_url_delivery_identity_action_for_proposal(
    store: Any,
    proposal: PerUrlDeliveryIdentityProposal,
    *,
    now: datetime | None = None,
) -> ActionObject:
    candidate = PerUrlDeliveryIdentityCandidate(
        disposition_action_id=proposal.snapshot.disposition_action_id
    )
    try:
        current = build_per_url_delivery_identity_snapshot(store, candidate, now=now)
    except PerUrlDeliveryIdentityAuthorityBlocked as error:
        return _blocked_action(
            proposal,
            error.code,
            error.owner,
            error.evidence_ids,
            error.safe_next_step,
        )
    action = build_per_url_delivery_identity_action(proposal)
    if current.context_digest != proposal.snapshot.context_digest:
        _block_action(
            action,
            _blocker(
                "per_url_delivery_identity_context_drift",
                "WILQ content workflow",
                current.evidence_ids,
                "Odśwież preview identity dla bieżącego per-URL semantic row.",
            ),
        )
    return action


def load_per_url_delivery_identity_action(action_id: str) -> ActionObject | None:
    from wilq.content.workflow.store.store import content_workflow_store

    projection = read_per_url_delivery_identity_authority(
        content_workflow_store(), action_id=action_id
    )
    return projection.action


def execute_per_url_delivery_identity_authority(
    action: ActionObject,
    *,
    store: Any,
    audit_events: list[AuditEvent],
    confirmed_by: str | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    proposal = store.load_per_url_delivery_identity_proposal(action.id)
    if proposal is None:
        return None, ["Per-URL delivery identity proposal is missing."]
    expected = per_url_delivery_identity_action_for_proposal(store, proposal, now=now)
    if expected.payload.get("runtime_blockers") or action.payload != expected.payload:
        return None, ["Per-URL delivery identity context changed before apply."]
    payload_digest = per_url_delivery_identity_action_payload_digest(action)
    chain, blockers = revision_bound_action_chain(
        [event for event in audit_events if event.action_id == action.id],
        confirmed_by=confirmed_by or _confirmation_actor(audit_events),
        binding_from_event=_audit_binding,
        expected_binding=(proposal.snapshot.context_digest, payload_digest),
    )
    if chain is None:
        return None, [
            blockers[0].reason if blockers else "Per-URL delivery identity audit chain is invalid."
        ]
    preview, review, confirmation, impact = chain
    provisional = PerUrlDeliveryIdentityBinding.model_construct(
        schema_version="wilq_per_url_delivery_identity_binding_v1",
        status="exact_current",
        binding_id="",
        binding_digest="0" * 64,
        action_id=action.id,
        action_payload_digest=payload_digest,
        snapshot=proposal.snapshot,
        preview_audit_id=preview.id,
        review_audit_id=review.id,
        confirmation_audit_id=confirmation.id,
        impact_audit_id=impact.id,
        reviewed_by=review.actor,
        confirmed_by=confirmation.actor,
        recorded_at=_aware_now(now),
    )
    binding_digest = per_url_delivery_identity_binding_digest(provisional)
    binding = PerUrlDeliveryIdentityBinding.model_validate(
        provisional.model_dump(mode="json")
        | {
            "binding_id": f"content_per_url_delivery_identity_{binding_digest[:24]}",
            "binding_digest": binding_digest,
        }
    )
    status, stored = store.record_per_url_delivery_identity_binding(binding)
    if status == "conflict":
        return None, ["Per-URL delivery identity conflicts with an existing immutable binding."]
    return {
        "binding_id": stored.binding_id,
        "status": status,
        "generation_allowed": False,
        "external_write_attempted": False,
    }, []


def validate_per_url_delivery_identity_action_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("action_type") != PER_URL_DELIVERY_IDENTITY_ACTION_TYPE:
        errors.append("Per-URL delivery identity action type is invalid.")
    if payload.get("local_authority_only") is not True:
        errors.append("Per-URL delivery identity must remain local-only.")
    try:
        PerUrlDeliveryIdentitySnapshot.model_validate(
            payload.get("per_url_delivery_identity_authority", {})
        )
    except Exception:
        errors.append("Per-URL delivery identity snapshot is invalid.")
    return errors


def _action_blockers(action: ActionObject) -> tuple[PerUrlDeliveryIdentityBlocker, ...]:
    values = action.payload.get("runtime_blockers", [])
    return tuple(
        _blocker(
            value,
            "WILQ content workflow",
            tuple(action.evidence_ids),
            "Odczytaj świeży per-URL semantic row i przygotuj nowe identity preview.",
        )
        for value in values
        if isinstance(value, str)
    )


def _blocked_action(
    proposal: PerUrlDeliveryIdentityProposal,
    code: str,
    owner: str,
    evidence_ids: tuple[str, ...],
    safe_next_step: str,
) -> ActionObject:
    action = build_per_url_delivery_identity_action(proposal)
    _block_action(action, _blocker(code, owner, evidence_ids, safe_next_step))
    return action


def _block_action(action: ActionObject, blocker: PerUrlDeliveryIdentityBlocker) -> None:
    action.status = ActionStatus.blocked
    action.payload["runtime_blockers"] = [blocker.code]
    action.payload["apply_allowed"] = False
    action.payload["api_mutation_ready"] = False


def _blocker(
    code: str,
    owner: str,
    evidence_ids: tuple[str, ...],
    safe_next_step: str,
) -> PerUrlDeliveryIdentityBlocker:
    return PerUrlDeliveryIdentityBlocker(
        code=code,
        owner=owner,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        safe_next_step=safe_next_step,
    )


def _observation_blocker(evidence_ids: tuple[str, ...]) -> PerUrlDeliveryIdentityAuthorityBlocked:
    return PerUrlDeliveryIdentityAuthorityBlocked(
        "per_url_observation_missing",
        "WILQ content workflow",
        evidence_ids,
        "Odczytaj ponownie świeży semantic row dokładnego URL-a.",
    )


def _audit_binding(event: AuditEvent) -> tuple[str, str] | None:
    context = event.details.get("per_url_delivery_identity_snapshot_digest")
    payload = event.details.get("per_url_delivery_identity_action_payload_digest")
    return (context, payload) if isinstance(context, str) and isinstance(payload, str) else None


def _confirmation_actor(events: list[AuditEvent]) -> str:
    confirmations = sorted(
        (event for event in events if event.event_type == "action_apply_confirmed"),
        key=lambda event: (event.created_at, event.id),
        reverse=True,
    )
    return confirmations[0].actor if confirmations else ""


def _aware_now(now: datetime | None) -> datetime:
    value = datetime.now(UTC) if now is None else now
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Per-URL identity execution time must be timezone-aware.")
    return value.astimezone(UTC)


__all__ = [
    "PER_URL_DELIVERY_IDENTITY_ACTION_TYPE",
    "PER_URL_DELIVERY_IDENTITY_MUTATION_ADAPTER",
    "PerUrlDeliveryIdentityBinding",
    "PerUrlDeliveryIdentityCandidate",
    "PerUrlDeliveryIdentityPreviewResponse",
    "PerUrlDeliveryIdentityProjection",
    "PerUrlDeliveryIdentitySnapshot",
    "build_per_url_delivery_identity_snapshot",
    "execute_per_url_delivery_identity_authority",
    "load_per_url_delivery_identity_action",
    "per_url_delivery_identity_action_payload_digest",
    "per_url_delivery_identity_action_for_proposal",
    "per_url_delivery_identity_binding_digest",
    "per_url_delivery_identity_proposal_digest",
    "per_url_delivery_identity_snapshot_digest",
    "prepare_per_url_delivery_identity_preview",
    "read_per_url_delivery_identity_authority",
    "validate_per_url_delivery_identity_action_payload",
]
