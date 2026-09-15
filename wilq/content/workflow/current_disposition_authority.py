"""Server-owned candidate context for a current content disposition decision."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.actions.action_chain import revision_bound_action_chain
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.store.store_production_classification import (
    HISTORICAL_PRODUCTION_POLICY_IDS,
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
CURRENT_DISPOSITION_ACTION_TYPE = "content_current_disposition_receipt"
CURRENT_DISPOSITION_MUTATION_ADAPTER = "content_current_disposition_store"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentCurrentDispositionCandidate(_FrozenModel):
    """A proposed decision; it is deliberately not an approval or receipt."""

    current_work_item_id: str = Field(min_length=1, max_length=240)
    proposed_final_disposition: Literal["keep", "noindex", "redirect", "remove"]
    attempt: int = Field(default=0, ge=0, le=1000)


class ContentCurrentDispositionSnapshot(_FrozenModel):
    """Exact current classification context reviewed by the later ActionObject."""

    schema_version: Literal["wilq_current_disposition_snapshot_v1"] = (
        "wilq_current_disposition_snapshot_v1"
    )
    current_work_item_id: str = Field(min_length=1, max_length=240)
    canonical_path: str = Field(min_length=1, max_length=2048)
    public_url: str = Field(min_length=1, max_length=2048)
    classification_run_id: str = Field(min_length=1, max_length=240)
    classification_run_digest: str = Field(pattern=_HEX64)
    classification_decision_set_digest: str = Field(pattern=_HEX64)
    classification_source_row_digest: str = Field(pattern=_HEX64)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    proposed_final_disposition: Literal["keep", "noindex", "redirect", "remove"]
    context_digest: str = Field(pattern=_HEX64)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item.strip() for item in value):
            raise ValueError("Disposition evidence IDs must be sorted, unique and non-blank.")
        return value

    @model_validator(mode="after")
    def require_self_authenticating_context(self) -> Self:
        if self.context_digest == "0" * 64 or (
            self.context_digest != current_disposition_snapshot_digest(self)
        ):
            raise ValueError("Current disposition context digest does not match.")
        return self


class ContentCurrentDispositionProposal(_FrozenModel):
    action_id: str = Field(min_length=1, max_length=240)
    proposal_digest: str = Field(pattern=_HEX64)
    current_work_item_id: str = Field(min_length=1, max_length=240)
    proposed_final_disposition: Literal["keep", "noindex", "redirect", "remove"]
    attempt: int = Field(default=0, ge=0, le=1000)
    prepared_snapshot_digest: str = Field(pattern=_HEX64)
    prepared_at: datetime

    @model_validator(mode="after")
    def require_exact_proposal(self) -> Self:
        expected = current_disposition_proposal_digest(
            self.current_work_item_id, self.proposed_final_disposition, self.attempt
        )
        if self.proposal_digest != expected or self.action_id != current_disposition_action_id(
            self.current_work_item_id, self.proposed_final_disposition, self.attempt
        ):
            raise ValueError("Current disposition proposal ID/digest does not match.")
        if self.prepared_at.tzinfo is None or self.prepared_at.utcoffset() is None:
            raise ValueError("prepared_at must be timezone-aware.")
        return self


class ContentCurrentDispositionReceipt(_FrozenModel):
    receipt_id: str = Field(min_length=1, max_length=240)
    receipt_digest: str = Field(pattern=_HEX64)
    action_id: str = Field(min_length=1, max_length=240)
    action_payload_digest: str = Field(pattern=_HEX64)
    authority_snapshot: ContentCurrentDispositionSnapshot
    preview_audit_id: str = Field(min_length=1, max_length=240)
    review_audit_id: str = Field(min_length=1, max_length=240)
    confirmation_audit_id: str = Field(min_length=1, max_length=240)
    impact_audit_id: str = Field(min_length=1, max_length=240)
    reviewed_by: str = Field(min_length=1, max_length=240)
    confirmed_by: str = Field(min_length=1, max_length=240)

    @model_validator(mode="after")
    def require_self_authenticating_receipt(self) -> Self:
        if self.receipt_digest != current_disposition_receipt_digest(self):
            raise ValueError("Current disposition receipt digest does not match.")
        if self.receipt_id != f"content_current_disposition_{self.receipt_digest[:24]}":
            raise ValueError("Current disposition receipt ID does not match.")
        return self

    @classmethod
    def create(
        cls,
        *,
        action: ActionObject,
        snapshot: ContentCurrentDispositionSnapshot,
        preview_audit_id: str,
        review_audit_id: str,
        confirmation_audit_id: str,
        impact_audit_id: str,
        reviewed_by: str,
        confirmed_by: str,
    ) -> Self:
        payload_digest = canonical_json_digest(action.payload)
        provisional = {
            "receipt_id": "",
            "receipt_digest": "0" * 64,
            "action_id": action.id,
            "action_payload_digest": payload_digest,
            "authority_snapshot": snapshot.model_dump(mode="json"),
            "preview_audit_id": preview_audit_id,
            "review_audit_id": review_audit_id,
            "confirmation_audit_id": confirmation_audit_id,
            "impact_audit_id": impact_audit_id,
            "reviewed_by": reviewed_by,
            "confirmed_by": confirmed_by,
        }
        digest = current_disposition_receipt_digest(provisional)
        return cls.model_validate(
            provisional
            | {
                "receipt_id": f"content_current_disposition_{digest[:24]}",
                "receipt_digest": digest,
            }
        )


class ContentCurrentDispositionBlocker(_FrozenModel):
    """Typed, non-authoritative reason a proposal is no longer current."""

    seam: Literal["classification", "current_context", "receipt"]
    reason: str = Field(min_length=1, max_length=160)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    next_step: str = Field(min_length=1, max_length=600)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item.strip() for item in value):
            raise ValueError("Disposition blocker evidence IDs must be sorted and non-blank.")
        return value


class ContentCurrentDispositionPreviewResponse(_FrozenModel):
    """Server-built, non-authoritative preview of one proposed disposition."""

    status: Literal["preview_ready", "blocked"]
    action: ActionObject | None = None
    blockers: tuple[ContentCurrentDispositionBlocker, ...] = ()

    @model_validator(mode="after")
    def require_preview_state(self) -> Self:
        runtime_blockers: tuple[str, ...] = ()
        if self.action is not None:
            runtime_blockers = tuple(
                item
                for item in self.action.payload.get("runtime_blockers", [])
                if isinstance(item, str)
            )
        blocked = bool(self.blockers) or bool(runtime_blockers)
        if (self.status == "blocked") != blocked:
            raise ValueError("Current disposition preview status does not match its blockers.")
        if self.status == "preview_ready" and self.action is None:
            raise ValueError("A ready current disposition preview requires an ActionObject.")
        return self


class ContentCurrentDispositionReadProjection(_FrozenModel):
    """Read model that distinguishes a proposal from a persisted receipt."""

    status: Literal["missing", "preview_ready", "blocked", "current"]
    action: ActionObject | None = None
    receipt: ContentCurrentDispositionReceipt | None = None
    blockers: tuple[ContentCurrentDispositionBlocker, ...] = ()
    safe_next_step: str = "Odśwież exact current disposition i wykonaj nowy lifecycle."

    @model_validator(mode="after")
    def require_read_state(self) -> Self:
        if self.status == "current":
            if (
                self.receipt is None
                or self.action is None
                or self.action.status == ActionStatus.blocked
            ):
                raise ValueError(
                    "Current disposition read requires a current ActionObject and receipt."
                )
            if self.blockers or self.action.payload.get("runtime_blockers"):
                raise ValueError("Blocked current disposition cannot be reported as current.")
        if self.status == "preview_ready" and self.action is None:
            raise ValueError("A ready current disposition read requires an ActionObject.")
        if self.status == "blocked" and not self.blockers:
            raise ValueError("Blocked current disposition read requires a typed blocker.")
        if self.status == "blocked" and self.safe_next_step != self.blockers[0].next_step:
            raise ValueError("Current disposition safe next step must match its blocker.")
        if self.status == "missing" and self.receipt is not None:
            raise ValueError("Missing current disposition read cannot carry a receipt.")
        return self


def current_disposition_snapshot_digest(
    value: ContentCurrentDispositionSnapshot | dict[str, Any],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("context_digest", None)
    return canonical_json_digest(payload)


def current_disposition_receipt_digest(
    value: ContentCurrentDispositionReceipt | dict[str, Any],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("receipt_id", None)
    payload.pop("receipt_digest", None)
    return canonical_json_digest(payload)


def current_disposition_action_payload_digest(action: ActionObject) -> str:
    return canonical_json_digest(action.payload)


def execute_current_disposition_authority(
    action: ActionObject,
    *,
    store: Any,
    audit_events: list[AuditEvent],
    confirmed_by: str | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    proposal = store.load_content_current_disposition_proposal(action.id)
    if proposal is None:
        return None, ["Current disposition proposal is missing."]
    expected, blockers = _rebuild_current_disposition_action(store, proposal)
    if expected is None or blockers or action.payload != expected.payload:
        return None, ["Current disposition context changed before apply."]
    snapshot = ContentCurrentDispositionSnapshot.model_validate(
        action.payload["current_disposition_authority"]
    )
    payload_digest = current_disposition_action_payload_digest(action)
    scoped_events = [event for event in audit_events if event.action_id == action.id]
    chain, chain_blockers = revision_bound_action_chain(
        scoped_events,
        confirmed_by=confirmed_by or _confirmation_actor(scoped_events),
        binding_from_event=_current_disposition_audit_binding,
        expected_binding=(snapshot.context_digest, payload_digest),
    )
    if chain is None:
        return None, [_current_disposition_chain_error(chain_blockers)]
    preview, review, confirmation, impact = chain
    receipt = ContentCurrentDispositionReceipt.create(
        action=action,
        snapshot=snapshot,
        preview_audit_id=preview.id,
        review_audit_id=review.id,
        confirmation_audit_id=confirmation.id,
        impact_audit_id=impact.id,
        reviewed_by=review.actor,
        confirmed_by=confirmation.actor,
    )
    status, stored = store.record_content_current_disposition_receipt(receipt)
    if status == "conflict":
        return None, ["Current disposition receipt conflicts with this action."]
    return (
        {
            "receipt_id": stored.receipt_id,
            "status": status,
            "external_write_attempted": False,
        },
        [],
    )


def _current_disposition_audit_binding(
    event: AuditEvent,
) -> tuple[str, str] | None:
    snapshot = event.details.get("current_disposition_snapshot_digest")
    payload = event.details.get("current_disposition_action_payload_digest")
    if not isinstance(snapshot, str) or not isinstance(payload, str):
        return None
    return snapshot, payload


def _confirmation_actor(events: list[AuditEvent]) -> str:
    confirmations = sorted(
        (
            event
            for event in events
            if event.event_type
            in {
                "action_apply_confirmed",
                "action_confirmation_blocked",
                "action_apply_confirmation_blocked",
            }
        ),
        key=lambda event: (event.created_at, event.id),
        reverse=True,
    )
    return confirmations[0].actor if confirmations else ""


def _current_disposition_chain_error(blockers: list[Any]) -> str:
    code = blockers[0].code if blockers else ""
    if code == "wordpress_action_chain_order_invalid":
        return "Current disposition audit chain is out of order."
    if code == "wordpress_action_chain_binding_mismatch":
        return "Audit chain does not bind the exact current disposition snapshot."
    return "Current disposition audit chain is not valid."


def build_current_disposition_snapshot(
    store: Any,
    candidate: ContentCurrentDispositionCandidate,
) -> ContentCurrentDispositionSnapshot:
    """Reload one exact nonhistorical row; never infer a disposition from it."""

    run = store.load_latest_production_classification()
    if run is None or run.input.policy_id in HISTORICAL_PRODUCTION_POLICY_IDS:
        raise ValueError("Current production classification is unavailable.")
    matches = [
        row
        for row in run.rows
        if row.current_work_item_id == candidate.current_work_item_id
    ]
    if len(matches) != 1:
        raise ValueError("Current disposition requires one exact current classification row.")
    row = matches[0]
    evidence_ids = tuple(sorted(set(row.primary_evidence_ids) | set(row.lineage_evidence_ids)))
    provisional = {
        "schema_version": "wilq_current_disposition_snapshot_v1",
        "current_work_item_id": row.current_work_item_id,
        "canonical_path": row.canonical_path,
        "public_url": row.public_url,
        "classification_run_id": run.run_id,
        "classification_run_digest": run.run_digest,
        "classification_decision_set_digest": run.input.decision_set_digest,
        "classification_source_row_digest": row.source_packet_row_digest,
        "evidence_ids": evidence_ids,
        "proposed_final_disposition": candidate.proposed_final_disposition,
        "context_digest": "0" * 64,
    }
    return ContentCurrentDispositionSnapshot.model_validate(
        provisional | {"context_digest": current_disposition_snapshot_digest(provisional)}
    )


def build_current_disposition_action(
    snapshot: ContentCurrentDispositionSnapshot,
    *,
    attempt: int = 0,
) -> ActionObject:
    """Build a local-only ActionObject; later persistence owns lifecycle recovery."""

    action_id = current_disposition_action_id(
        snapshot.current_work_item_id, snapshot.proposed_final_disposition, attempt
    )
    preview = {
        "id": f"current_disposition_{snapshot.current_work_item_id}",
        "operation_type": "record_current_disposition_receipt",
        "current_work_item_id": snapshot.current_work_item_id,
        "proposed_final_disposition": snapshot.proposed_final_disposition,
        "apply_allowed": True,
        "api_mutation_ready": True,
    }
    payload = {
        "action_type": CURRENT_DISPOSITION_ACTION_TYPE,
        "connector": "wordpress_ekologus",
        "mode": "apply",
        "local_authority_only": True,
        "current_disposition_authority": snapshot.model_dump(mode="json"),
        "payload_preview": [preview],
        "apply_allowed": True,
        "api_mutation_ready": True,
        "destructive": False,
    }
    if attempt:
        payload["attempt"] = attempt
    return ActionObject(
        id=action_id,
        title="Zatwierdź bieżącą disposition exact URL-a",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply,
        evidence_ids=list(snapshot.evidence_ids),
        human_diagnosis="To jest propozycja disposition; nie wynika automatycznie z klasyfikacji.",
        recommended_reason="Zweryfikuj exact snapshot przed canonical review i potwierdzeniem.",
        payload=payload,
        validation_status="not_validated",
        created_by="system_core_current_disposition_authority",
    )


def current_disposition_action_id(
    current_work_item_id: str,
    proposed_final_disposition: Literal["keep", "noindex", "redirect", "remove"],
    attempt: int = 0,
) -> str:
    _validate_attempt(attempt)
    digest = canonical_json_digest(
        {
            "current_work_item_id": current_work_item_id,
            "proposed_final_disposition": proposed_final_disposition,
        }
    )
    base_id = f"act_current_disposition_{digest[:24]}"
    return base_id if attempt == 0 else f"{base_id}_attempt_{attempt}"


def current_disposition_proposal_digest(
    current_work_item_id: str,
    proposed_final_disposition: Literal["keep", "noindex", "redirect", "remove"],
    attempt: int = 0,
) -> str:
    _validate_attempt(attempt)
    payload: dict[str, Any] = {
        "current_work_item_id": current_work_item_id,
        "proposed_final_disposition": proposed_final_disposition,
    }
    if attempt:
        payload["attempt"] = attempt
    return canonical_json_digest(payload)


def build_current_disposition_proposal(
    snapshot: ContentCurrentDispositionSnapshot,
    *,
    attempt: int = 0,
) -> ContentCurrentDispositionProposal:
    return ContentCurrentDispositionProposal(
        action_id=current_disposition_action_id(
            snapshot.current_work_item_id, snapshot.proposed_final_disposition, attempt
        ),
        proposal_digest=current_disposition_proposal_digest(
            snapshot.current_work_item_id, snapshot.proposed_final_disposition, attempt
        ),
        current_work_item_id=snapshot.current_work_item_id,
        proposed_final_disposition=snapshot.proposed_final_disposition,
        attempt=attempt,
        prepared_snapshot_digest=snapshot.context_digest,
        prepared_at=datetime.now(UTC),
    )


def _rebuild_current_disposition_action(
    store: Any, proposal: ContentCurrentDispositionProposal
) -> tuple[ActionObject | None, tuple[ContentCurrentDispositionBlocker, ...]]:
    try:
        snapshot = build_current_disposition_snapshot(
            store,
            ContentCurrentDispositionCandidate(
                current_work_item_id=proposal.current_work_item_id,
                proposed_final_disposition=proposal.proposed_final_disposition,
                attempt=proposal.attempt,
            ),
        )
    except ValueError as error:
        blocker = _current_disposition_rebuild_blocker(str(error))
        return None, (blocker,)

    action = build_current_disposition_action(snapshot, attempt=proposal.attempt)
    # The persisted proposal is the immutable identity of this ActionObject;
    # rebuilding a read projection must not manufacture a new timestamp.
    action.created_at = proposal.prepared_at
    action.updated_at = proposal.prepared_at
    blockers: tuple[ContentCurrentDispositionBlocker, ...] = ()
    if snapshot.context_digest != proposal.prepared_snapshot_digest:
        blockers = (
            _current_disposition_blocker(
                "current_context",
                "current_disposition_snapshot_drift",
                snapshot.evidence_ids,
                "Odśwież preview dla bieżącej klasyfikacji i wykonaj nowy pełny lifecycle.",
            ),
        )
    action.payload["runtime_blockers"] = [item.reason for item in blockers]
    if blockers:
        action.status = ActionStatus.blocked
        action.payload["apply_allowed"] = False
        action.payload["api_mutation_ready"] = False
    return action, blockers


def _current_disposition_blocker(
    seam: Literal["classification", "current_context", "receipt"],
    reason: str,
    evidence_ids: tuple[str, ...] = (),
    next_step: str = "Odśwież exact current disposition i wykonaj nowy lifecycle.",
) -> ContentCurrentDispositionBlocker:
    return ContentCurrentDispositionBlocker(
        seam=seam,
        reason=reason,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        next_step=next_step,
    )


def _current_disposition_rebuild_blocker(
    error_message: str,
) -> ContentCurrentDispositionBlocker:
    if "one exact current classification row" in error_message:
        return _current_disposition_blocker(
            "classification",
            "current_disposition_row_missing",
            next_step=(
                "Nie ma już jednego bieżącego wiersza klasyfikacji; odczytaj aktualny inventory "
                "i przygotuj nowy preview."
            ),
        )
    if "production classification is unavailable" in error_message:
        return _current_disposition_blocker(
            "classification",
            "current_disposition_classification_unavailable",
            next_step=(
                "Najpierw udostępnij bieżącą, niehistoryczną klasyfikację, potem przygotuj nowy "
                "preview."
            ),
        )
    return _current_disposition_blocker(
        "classification",
        "current_disposition_context_unavailable",
        next_step="Sprawdź bieżącą klasyfikację i przygotuj nowy preview.",
    )


def current_disposition_action_for_proposal(
    store: Any, proposal: ContentCurrentDispositionProposal
) -> ActionObject:
    action, blockers = _rebuild_current_disposition_action(store, proposal)
    if action is None:
        raise ValueError(
            blockers[0].reason if blockers else "Current disposition action unavailable."
        )
    return action


def prepare_current_disposition_preview(
    store: Any,
    candidate: ContentCurrentDispositionCandidate,
) -> ContentCurrentDispositionPreviewResponse:
    """Persist a candidate and rebuild its exact action preview server-side."""

    proposal = store.record_content_current_disposition_proposal(candidate)
    action, blockers = _rebuild_current_disposition_action(store, proposal)
    return ContentCurrentDispositionPreviewResponse(
        status="blocked" if blockers else "preview_ready",
        action=action,
        blockers=blockers,
    )


def read_current_disposition_authority(
    store: Any, *, action_id: str
) -> ContentCurrentDispositionReadProjection:
    proposal = store.load_content_current_disposition_proposal(action_id)
    if proposal is None:
        return ContentCurrentDispositionReadProjection(status="missing")
    receipt = store.load_content_current_disposition_receipt(action_id)
    action, blockers = _rebuild_current_disposition_action(store, proposal)
    if blockers:
        return ContentCurrentDispositionReadProjection(
            status="blocked",
            action=action,
            receipt=receipt,
            blockers=blockers,
            safe_next_step=blockers[0].next_step,
        )
    return ContentCurrentDispositionReadProjection(
        status="current" if receipt is not None else "preview_ready",
        action=action,
        receipt=receipt,
    )


def load_current_disposition_action(action_id: str) -> ActionObject | None:
    from wilq.content.workflow.store.store import content_workflow_store

    store = content_workflow_store()
    proposal = store.load_content_current_disposition_proposal(action_id)
    if proposal is None:
        return None
    action, _blockers = _rebuild_current_disposition_action(store, proposal)
    return action


def validate_current_disposition_action_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("action_type") != CURRENT_DISPOSITION_ACTION_TYPE:
        errors.append("Current disposition action type is invalid.")
    if payload.get("local_authority_only") is not True:
        errors.append("Current disposition authority must remain local-only.")
    snapshot_payload = payload.get("current_disposition_authority")
    if snapshot_payload is None and payload.get("runtime_blockers"):
        return errors
    try:
        ContentCurrentDispositionSnapshot.model_validate_json(
            json.dumps(
                snapshot_payload if snapshot_payload is not None else {},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ),
            strict=True,
        )
    except Exception:
        errors.append("Current disposition authority snapshot is invalid.")
    return errors


def _validate_attempt(attempt: int) -> None:
    if isinstance(attempt, bool) or not isinstance(attempt, int) or not 0 <= attempt <= 1000:
        raise ValueError("Current disposition attempt must be an integer from 0 to 1000.")


__all__ = [
    "ContentCurrentDispositionCandidate",
    "ContentCurrentDispositionBlocker",
    "ContentCurrentDispositionProposal",
    "ContentCurrentDispositionPreviewResponse",
    "ContentCurrentDispositionReadProjection",
    "ContentCurrentDispositionReceipt",
    "ContentCurrentDispositionSnapshot",
    "CURRENT_DISPOSITION_ACTION_TYPE",
    "CURRENT_DISPOSITION_MUTATION_ADAPTER",
    "build_current_disposition_action",
    "build_current_disposition_proposal",
    "build_current_disposition_snapshot",
    "current_disposition_action_id",
    "current_disposition_action_payload_digest",
    "current_disposition_action_for_proposal",
    "current_disposition_proposal_digest",
    "current_disposition_receipt_digest",
    "execute_current_disposition_authority",
    "load_current_disposition_action",
    "prepare_current_disposition_preview",
    "read_current_disposition_authority",
    "validate_current_disposition_action_payload",
    "current_disposition_snapshot_digest",
]
