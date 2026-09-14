"""Server-owned ActionObject lifecycle from two exact receipts to one identity."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.workflow.current_disposition_authority import (
    ContentCurrentDispositionReceipt,
    ContentCurrentDispositionSnapshot,
)
from wilq.content.workflow.decisions.production import (
    ContentProductionRegisteredInventoryReceipt,
    canonical_json_digest,
)
from wilq.content.workflow.delivery_identity import (
    ContentDeliveryIdentityCommand,
    ContentDeliveryIdentityRecordResult,
    inventory_evidence_digest,
)
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
DELIVERY_IDENTITY_AUTHORITY_ACTION_TYPE = "content_delivery_identity_binding"
DELIVERY_IDENTITY_AUTHORITY_MUTATION_ADAPTER = "content_delivery_identity_store"
DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT: Literal[
    "delivery-identity:exact-registered-receipt-authority"
] = (
    "delivery-identity:exact-registered-receipt-authority"
)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentDeliveryIdentityAuthorityCandidate(_FrozenModel):
    """Only receipt identifiers are accepted from a caller; never URL or disposition."""

    current_disposition_receipt_id: str = Field(min_length=1, max_length=240)
    inventory_receipt_id: str = Field(min_length=1, max_length=240)


class ContentDeliveryIdentityAuthoritySnapshot(_FrozenModel):
    schema_version: Literal["wilq_delivery_identity_authority_snapshot_v1"] = (
        "wilq_delivery_identity_authority_snapshot_v1"
    )
    authority_mapping: Literal["delivery-identity:exact-registered-receipt-authority"] = (
        DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT
    )
    current_disposition_receipt_id: str = Field(min_length=1, max_length=240)
    current_disposition_receipt_digest: str = Field(pattern=_HEX64)
    inventory_receipt_id: str = Field(min_length=1, max_length=240)
    inventory_receipt_digest: str = Field(pattern=_HEX64)
    inventory_catalog_item_digest: str = Field(pattern=_HEX64)
    inventory_catalog_snapshot_digest: str = Field(pattern=_HEX64)
    inventory_receipt: ContentProductionRegisteredInventoryReceipt
    authority_snapshot: ContentCurrentDispositionSnapshot
    inventory_evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    context_digest: str = Field(pattern=_HEX64)

    @property
    def registered_inventory_receipt(self) -> ContentProductionRegisteredInventoryReceipt:
        """Name the receipt authority explicitly for callers reading the snapshot."""

        return self.inventory_receipt

    @field_validator("inventory_evidence_ids")
    @classmethod
    def require_sorted_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item.strip() for item in value):
            raise ValueError(
                "Identity authority evidence IDs must be sorted, unique and non-blank."
            )
        return value

    @model_validator(mode="after")
    def require_self_authenticating_context(self) -> Self:
        receipt = self.inventory_receipt
        if (
            self.inventory_receipt_id != receipt.receipt_id
            or self.inventory_receipt_digest != receipt.receipt_digest
            or self.inventory_catalog_item_digest != receipt.catalog_item_digest
            or self.inventory_catalog_snapshot_digest != receipt.catalog_snapshot_digest
            or self.inventory_evidence_ids != receipt.catalog_snapshot_evidence_ids
            or receipt.current_work_item_id != self.authority_snapshot.current_work_item_id
            or receipt.canonical_path != self.authority_snapshot.canonical_path
            or receipt.public_url != self.authority_snapshot.public_url
            or not set(receipt.catalog_snapshot_evidence_ids).issubset(
                set(self.authority_snapshot.evidence_ids)
            )
        ):
            raise ValueError(
                "Delivery identity authority must carry the exact registered inventory receipt."
            )
        if self.context_digest == "0" * 64 or (
            self.context_digest != delivery_identity_authority_snapshot_digest(self)
        ):
            raise ValueError("Delivery identity authority context digest does not match.")
        return self


class ContentDeliveryIdentityAuthorityProposal(_FrozenModel):
    action_id: str = Field(min_length=1, max_length=240)
    proposal_digest: str = Field(pattern=_HEX64)
    current_disposition_receipt_id: str = Field(min_length=1, max_length=240)
    inventory_receipt_id: str = Field(min_length=1, max_length=240)
    prepared_snapshot_digest: str = Field(pattern=_HEX64)
    prepared_at: datetime

    @model_validator(mode="after")
    def require_exact_proposal(self) -> Self:
        expected = delivery_identity_authority_proposal_digest(
            self.current_disposition_receipt_id, self.inventory_receipt_id
        )
        if self.proposal_digest != expected or (
            self.action_id
            != delivery_identity_authority_action_id(
                self.current_disposition_receipt_id, self.inventory_receipt_id
            )
        ):
            raise ValueError("Delivery identity authority proposal ID/digest does not match.")
        if self.prepared_at.tzinfo is None or self.prepared_at.utcoffset() is None:
            raise ValueError("prepared_at must be timezone-aware.")
        return self


def delivery_identity_authority_snapshot_digest(
    value: ContentDeliveryIdentityAuthoritySnapshot | dict[str, Any],
) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("context_digest", None)
    return canonical_json_digest(payload)


def delivery_identity_authority_action_id(
    current_disposition_receipt_id: str, inventory_receipt_id: str
) -> str:
    return (
        "act_delivery_identity_"
        + canonical_json_digest(
            {
                "current_disposition_receipt_id": current_disposition_receipt_id,
                "inventory_receipt_id": inventory_receipt_id,
            }
        )[:24]
    )


def delivery_identity_authority_proposal_digest(
    current_disposition_receipt_id: str, inventory_receipt_id: str
) -> str:
    return canonical_json_digest(
        {
            "current_disposition_receipt_id": current_disposition_receipt_id,
            "inventory_receipt_id": inventory_receipt_id,
        }
    )


def delivery_identity_authority_action_payload_digest(action: ActionObject) -> str:
    return canonical_json_digest(action.payload)


def build_delivery_identity_authority_snapshot(
    store: Any, candidate: ContentDeliveryIdentityAuthorityCandidate
) -> ContentDeliveryIdentityAuthoritySnapshot:
    disposition = store.load_content_current_disposition_receipt_by_id(
        candidate.current_disposition_receipt_id
    )
    if disposition is None:
        raise ValueError("Current disposition receipt is unavailable.")
    current = _revalidate_disposition_receipt(store, disposition)
    classification = store.load_latest_production_classification()
    if classification is None or classification.input.policy_id in HISTORICAL_PRODUCTION_POLICY_IDS:
        raise ValueError("Current production classification is unavailable.")
    row = classification.for_work_item(current.current_work_item_id)
    if row is None or row.current_work_item_id != current.current_work_item_id:
        raise ValueError("Current classification row is unavailable.")
    if (
        classification.run_id != current.classification_run_id
        or classification.run_digest != current.classification_run_digest
        or classification.input.decision_set_digest != current.classification_decision_set_digest
        or row.source_packet_row_digest != current.classification_source_row_digest
        or row.canonical_path != current.canonical_path
        or row.public_url != current.public_url
    ):
        raise ValueError("Current classification row no longer matches the disposition receipt.")
    inventory = row.source_receipt
    if not isinstance(inventory, ContentProductionRegisteredInventoryReceipt):
        raise ValueError("Current classification row has no registered inventory receipt.")
    if (
        row.decision != "blocked"
        or row.generation_allowed is not False
        or row.retained_work_item_id is not None
        or row.retained_binding is not None
        or row.revision_id is not None
        or row.verified_actions
        or row.verified_drafts
    ):
        raise ValueError("Current classification row retains delivery lineage.")
    if candidate.inventory_receipt_id != inventory.receipt_id:
        raise ValueError("Inventory receipt ID does not match the current classification row.")
    if (
        inventory.current_work_item_id != current.current_work_item_id
        or inventory.canonical_path != current.canonical_path
        or inventory.public_url != current.public_url
        or not set(inventory.catalog_snapshot_evidence_ids).issubset(
            set(current.evidence_ids)
        )
    ):
        raise ValueError(
            "Inventory receipt evidence does not exactly match current disposition context."
        )
    values = {
        "schema_version": "wilq_delivery_identity_authority_snapshot_v1",
        "authority_mapping": DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT,
        "current_disposition_receipt_id": disposition.receipt_id,
        "current_disposition_receipt_digest": disposition.receipt_digest,
        "inventory_receipt_id": inventory.receipt_id,
        "inventory_receipt_digest": inventory.receipt_digest,
        "inventory_catalog_item_digest": inventory.catalog_item_digest,
        "inventory_catalog_snapshot_digest": inventory.catalog_snapshot_digest,
        "inventory_receipt": inventory.model_dump(mode="json"),
        "authority_snapshot": current.model_dump(mode="json"),
        "inventory_evidence_ids": inventory.catalog_snapshot_evidence_ids,
        "context_digest": "0" * 64,
    }
    return ContentDeliveryIdentityAuthoritySnapshot.model_validate(
        values | {"context_digest": delivery_identity_authority_snapshot_digest(values)}
    )


def _revalidate_disposition_receipt(
    store: Any, receipt: ContentCurrentDispositionReceipt
) -> ContentCurrentDispositionSnapshot:
    from wilq.content.workflow.current_disposition_authority import (
        ContentCurrentDispositionCandidate,
        build_current_disposition_snapshot,
    )

    current = build_current_disposition_snapshot(
        store,
        ContentCurrentDispositionCandidate(
            current_work_item_id=receipt.authority_snapshot.current_work_item_id,
            proposed_final_disposition=receipt.authority_snapshot.proposed_final_disposition,
        ),
    )
    if current != receipt.authority_snapshot:
        raise ValueError("Current disposition receipt no longer matches current classification.")
    return current


def build_delivery_identity_authority_action(
    snapshot: ContentDeliveryIdentityAuthoritySnapshot,
) -> ActionObject:
    action_id = delivery_identity_authority_action_id(
        snapshot.current_disposition_receipt_id, snapshot.inventory_receipt_id
    )
    preview = {
        "id": f"delivery_identity_{snapshot.authority_snapshot.current_work_item_id}",
        "operation_type": "record_content_delivery_identity_binding",
        "preview_contract": DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT,
        "current_work_item_id": snapshot.authority_snapshot.current_work_item_id,
        "canonical_path": snapshot.authority_snapshot.canonical_path,
        "proposed_final_disposition": snapshot.authority_snapshot.proposed_final_disposition,
        "apply_allowed": True,
        "api_mutation_ready": True,
    }
    return ActionObject(
        id=action_id,
        title="Zapisz exact identity URL-a z dwóch bieżących receiptów",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply,
        evidence_ids=list(
            sorted(
                set(snapshot.authority_snapshot.evidence_ids) | set(snapshot.inventory_evidence_ids)
            )
        ),
        human_diagnosis=(
            "Identity powstaje wyłącznie z potwierdzonej disposition i exact inventory receipt."
        ),
        recommended_reason=(
            "Sprawdź oba receipt-y i ich bieżące powiązanie, potem wykonaj canonical lifecycle."
        ),
        payload={
            "action_type": DELIVERY_IDENTITY_AUTHORITY_ACTION_TYPE,
            "authority_mapping": DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT,
            "preview_contract": DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT,
            "connector": "wordpress_ekologus",
            "mode": "apply",
            "local_authority_only": True,
            "delivery_identity_authority": snapshot.model_dump(mode="json"),
            "payload_preview": [preview],
            "apply_allowed": True,
            "api_mutation_ready": True,
            "destructive": False,
            "runtime_blockers": [],
        },
        validation_status="not_validated",
        created_by="system_core_delivery_identity_authority",
    )


def build_delivery_identity_authority_proposal(
    snapshot: ContentDeliveryIdentityAuthoritySnapshot,
) -> ContentDeliveryIdentityAuthorityProposal:
    return ContentDeliveryIdentityAuthorityProposal(
        action_id=delivery_identity_authority_action_id(
            snapshot.current_disposition_receipt_id, snapshot.inventory_receipt_id
        ),
        proposal_digest=delivery_identity_authority_proposal_digest(
            snapshot.current_disposition_receipt_id, snapshot.inventory_receipt_id
        ),
        current_disposition_receipt_id=snapshot.current_disposition_receipt_id,
        inventory_receipt_id=snapshot.inventory_receipt_id,
        prepared_snapshot_digest=snapshot.context_digest,
        prepared_at=datetime.now(UTC),
    )


def delivery_identity_authority_action_for_proposal(
    store: Any, proposal: ContentDeliveryIdentityAuthorityProposal
) -> ActionObject:
    candidate = ContentDeliveryIdentityAuthorityCandidate(
        current_disposition_receipt_id=proposal.current_disposition_receipt_id,
        inventory_receipt_id=proposal.inventory_receipt_id,
    )
    try:
        snapshot = build_delivery_identity_authority_snapshot(store, candidate)
    except ValueError as error:
        return _blocked_delivery_identity_authority_action(
            proposal,
            _delivery_identity_authority_blocker_code(str(error)),
            store=store,
        )
    action = build_delivery_identity_authority_action(snapshot)
    if snapshot.context_digest != proposal.prepared_snapshot_digest:
        return _blocked_delivery_identity_authority_action(
            proposal,
            "delivery_identity_authority_snapshot_drift",
            store=store,
            snapshot=snapshot,
        )
    return action


def _blocked_delivery_identity_authority_action(
    proposal: ContentDeliveryIdentityAuthorityProposal,
    blocker_code: str,
    *,
    store: Any,
    snapshot: ContentDeliveryIdentityAuthoritySnapshot | None = None,
) -> ActionObject:
    evidence_ids = ["delivery_identity_authority_blocked"]
    disposition = store.load_content_current_disposition_receipt_by_id(
        proposal.current_disposition_receipt_id
    )
    if disposition is not None:
        evidence_ids = list(disposition.authority_snapshot.evidence_ids)
    work_item_id = (
        snapshot.authority_snapshot.current_work_item_id
        if snapshot is not None
        else "delivery_identity_authority_blocked"
    )
    preview = {
        "id": f"delivery_identity_{work_item_id}",
        "operation_type": "record_content_delivery_identity_binding",
        "preview_contract": DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT,
        "current_work_item_id": work_item_id,
        "apply_allowed": False,
        "api_mutation_ready": False,
        "blocker": blocker_code,
    }
    payload: dict[str, Any] = {
        "action_type": DELIVERY_IDENTITY_AUTHORITY_ACTION_TYPE,
        "authority_mapping": DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT,
        "preview_contract": DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT,
        "connector": "wordpress_ekologus",
        "mode": "apply",
        "local_authority_only": True,
        "payload_preview": [preview],
        "apply_allowed": False,
        "api_mutation_ready": False,
        "destructive": False,
        "runtime_blockers": [blocker_code],
    }
    if snapshot is not None:
        payload["delivery_identity_authority"] = snapshot.model_dump(mode="json")
    return ActionObject(
        id=proposal.action_id,
        title="Zapisz exact identity URL-a z dwóch bieżących receiptów",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.blocked,
        evidence_ids=evidence_ids,
        human_diagnosis=(
            "Identity nie może zostać zapisana, dopóki oba bieżące receipt-y nie tworzą "
            "jednego exact kontekstu."
        ),
        recommended_reason="Odśwież klasyfikację i przygotuj nowy preview po usunięciu blokady.",
        payload=payload,
        validation_status="not_validated",
        created_by="system_core_delivery_identity_authority",
    )


def _delivery_identity_authority_blocker_code(error_message: str) -> str:
    if "Current disposition receipt is unavailable" in error_message:
        return "delivery_identity_authority_disposition_receipt_missing"
    if "Current production classification" in error_message:
        return "delivery_identity_authority_classification_not_current"
    if (
        "Current classification row is unavailable" in error_message
        or "requires one exact current classification row" in error_message
    ):
        return "delivery_identity_authority_classification_row_missing"
    if "no registered inventory receipt" in error_message:
        return "delivery_identity_authority_registered_inventory_receipt_missing"
    if "retains delivery lineage" in error_message:
        return "delivery_identity_authority_registered_inventory_receipt_state_invalid"
    if "Inventory receipt ID" in error_message:
        return "delivery_identity_authority_registered_inventory_receipt_mismatch"
    if (
        "classification row no longer matches" in error_message
        or "receipt no longer matches current classification" in error_message
    ):
        return "delivery_identity_authority_classification_drift"
    if "Inventory receipt" in error_message:
        return "delivery_identity_authority_inventory_context_mismatch"
    return "delivery_identity_authority_context_unavailable"


def build_delivery_identity_authority_blocked_proposal(
    candidate: ContentDeliveryIdentityAuthorityCandidate,
) -> ContentDeliveryIdentityAuthorityProposal:
    """Persist a typed blocked candidate when current classification is unavailable."""

    return ContentDeliveryIdentityAuthorityProposal(
        action_id=delivery_identity_authority_action_id(
            candidate.current_disposition_receipt_id, candidate.inventory_receipt_id
        ),
        proposal_digest=delivery_identity_authority_proposal_digest(
            candidate.current_disposition_receipt_id, candidate.inventory_receipt_id
        ),
        current_disposition_receipt_id=candidate.current_disposition_receipt_id,
        inventory_receipt_id=candidate.inventory_receipt_id,
        prepared_snapshot_digest=canonical_json_digest(
            {"blocked_candidate": candidate.model_dump(mode="json")}
        ),
        prepared_at=datetime.now(UTC),
    )


def load_delivery_identity_authority_action(action_id: str) -> ActionObject | None:
    from wilq.content.workflow.store.store import content_workflow_store

    store = content_workflow_store()
    proposal = store.load_content_delivery_identity_authority_proposal(action_id)
    return (
        None
        if proposal is None
        else delivery_identity_authority_action_for_proposal(store, proposal)
    )


def execute_delivery_identity_authority(
    action: ActionObject, *, store: Any, audit_events: list[AuditEvent]
) -> tuple[dict[str, Any] | None, list[str]]:
    proposal = store.load_content_delivery_identity_authority_proposal(action.id)
    if proposal is None:
        return None, ["Delivery identity authority proposal is missing."]
    expected = delivery_identity_authority_action_for_proposal(store, proposal)
    if expected.payload.get("runtime_blockers") or action.payload != expected.payload:
        return None, ["Delivery identity authority context changed before apply."]
    required = (
        "action_preview_generated",
        "human_review_approved_for_prepare",
        "action_apply_confirmed",
        "action_impact_check_completed",
    )
    events = {event.event_type: event for event in audit_events if event.action_id == action.id}
    if any(event_type not in events for event_type in required):
        return None, ["Exact preview, approved review, confirmation and impact check are required."]
    chain = [events[event_type] for event_type in required]
    if [event.event_type for event in sorted(chain, key=lambda event: event.created_at)] != list(
        required
    ):
        return None, ["Delivery identity authority audit chain is out of order."]
    snapshot = ContentDeliveryIdentityAuthoritySnapshot.model_validate(
        action.payload.get("delivery_identity_authority", {})
    )
    payload_digest = delivery_identity_authority_action_payload_digest(action)
    if any(
        event.details.get("delivery_identity_authority_snapshot_digest") != snapshot.context_digest
        or event.details.get("delivery_identity_authority_action_payload_digest") != payload_digest
        for event in chain
    ):
        return None, ["Audit chain does not bind the exact delivery identity authority snapshot."]
    command = ContentDeliveryIdentityCommand(
        canonical_path=snapshot.authority_snapshot.canonical_path,
        public_url=snapshot.authority_snapshot.public_url,
        current_work_item_id=snapshot.authority_snapshot.current_work_item_id,
        classification_run_id=snapshot.authority_snapshot.classification_run_id,
        classification_run_digest=snapshot.authority_snapshot.classification_run_digest,
        classification_decision_set_digest=snapshot.authority_snapshot.classification_decision_set_digest,
        classification_source_row_digest=snapshot.authority_snapshot.classification_source_row_digest,
        inventory_evidence_ids=snapshot.inventory_evidence_ids,
        inventory_evidence_digest=inventory_evidence_digest(snapshot.inventory_evidence_ids),
        final_disposition=snapshot.authority_snapshot.proposed_final_disposition,
        inventory_receipt_id=snapshot.inventory_receipt.receipt_id,
        inventory_receipt_digest=snapshot.inventory_receipt.receipt_digest,
        inventory_catalog_id=snapshot.inventory_receipt.catalog_id,
        inventory_catalog_item_digest=snapshot.inventory_receipt.catalog_item_digest,
        inventory_catalog_snapshot_digest=snapshot.inventory_receipt.catalog_snapshot_digest,
        inventory_catalog_snapshot_evidence_ids=(
            snapshot.inventory_receipt.catalog_snapshot_evidence_ids
        ),
        inventory_receipt=snapshot.inventory_receipt,
        recorded_by="wilq_local_action_executor",
        recorded_at=datetime.now(UTC),
    )
    result: ContentDeliveryIdentityRecordResult = store.record_content_delivery_identity(command)
    if result.status == "conflict":
        return None, ["Delivery identity binding conflicts with an existing append-only identity."]
    if result.binding.status != "exact_current" or result.current.current_status != "exact_current":
        return None, ["Delivery identity did not remain exact-current during apply."]
    return {
        "binding_id": result.binding.binding_id,
        "status": result.status,
        "external_write_attempted": False,
    }, []


def validate_delivery_identity_authority_action_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("action_type") != DELIVERY_IDENTITY_AUTHORITY_ACTION_TYPE:
        errors.append("Delivery identity authority action type is invalid.")
    if payload.get("local_authority_only") is not True:
        errors.append("Delivery identity authority must remain local-only.")
    if payload.get("authority_mapping") != DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT:
        errors.append("Delivery identity authority mapping is invalid.")
    if payload.get("preview_contract") != DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT:
        errors.append("Delivery identity authority preview contract is invalid.")
    runtime_blockers = payload.get("runtime_blockers")
    if isinstance(runtime_blockers, list) and runtime_blockers:
        if payload.get("apply_allowed") is not False:
            errors.append("Blocked delivery identity authority must disable apply.")
        if payload.get("api_mutation_ready") is not False:
            errors.append("Blocked delivery identity authority must disable API mutation.")
        if "delivery_identity_authority" not in payload:
            return errors
    try:
        ContentDeliveryIdentityAuthoritySnapshot.model_validate_json(
            json.dumps(
                payload.get("delivery_identity_authority", {}),
                sort_keys=True,
                separators=(",", ":"),
            ),
            strict=True,
        )
    except Exception:
        errors.append("Delivery identity authority snapshot is invalid.")
    return errors


__all__ = [
    "ContentDeliveryIdentityAuthorityCandidate",
    "build_delivery_identity_authority_blocked_proposal",
    "ContentDeliveryIdentityAuthorityProposal",
    "ContentDeliveryIdentityAuthoritySnapshot",
    "DELIVERY_IDENTITY_AUTHORITY_ACTION_TYPE",
    "DELIVERY_IDENTITY_AUTHORITY_MUTATION_ADAPTER",
    "DELIVERY_IDENTITY_AUTHORITY_PREVIEW_CONTRACT",
    "build_delivery_identity_authority_action",
    "build_delivery_identity_authority_proposal",
    "build_delivery_identity_authority_snapshot",
    "delivery_identity_authority_action_for_proposal",
    "delivery_identity_authority_action_id",
    "delivery_identity_authority_action_payload_digest",
    "delivery_identity_authority_proposal_digest",
    "delivery_identity_authority_snapshot_digest",
    "execute_delivery_identity_authority",
    "load_delivery_identity_authority_action",
    "validate_delivery_identity_authority_action_payload",
]
