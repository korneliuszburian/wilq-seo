"""Typed read-only operator recovery for a drifted delivery identity binding."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.delivery_identity import (
    ContentDeliveryClassificationLookup,
    ContentDeliveryIdentityBinding,
    ContentDeliveryIdentityCommand,
    build_content_delivery_identity_current_projection,
    inventory_evidence_digest,
)
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    OpportunityDomain,
)
from wilq.schemas.core import utc_now

_HEX64 = r"^[0-9a-f]{64}$"
CONTENT_DELIVERY_IDENTITY_REBIND_ACTION_TYPE = "content_delivery_identity_rebind"
REBIND_BLOCKER_CODE = "delivery_identity_rebind_requires_drift"
CONTENT_DELIVERY_IDENTITY_REBIND_ADAPTER = (
    "content_delivery_identity_rebind_local_authority"
)
CURRENT_SAFE_NEXT_STEP = "Exact current identity jest dostępna dla następnego kroku."
DRIFT_SAFE_NEXT_STEP = (
    "Zarejestruj nową exact current identity dla tego bieżącego wiersza klasyfikacji."
)
CLASSIFICATION_MISSING_SAFE_NEXT_STEP = (
    "Odśwież bieżącą exact klasyfikację, a potem zarejestruj nową identity."
)


class ContentDeliveryIdentityDriftRecovery(BaseModel):
    """What the binding packed versus the exact current classification row."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    response_type: Literal["content_delivery_identity_drift_recovery"] = (
        "content_delivery_identity_drift_recovery"
    )
    contract_version: Literal["content_delivery_identity_drift_recovery_v1"] = (
        "content_delivery_identity_drift_recovery_v1"
    )
    binding_id: str = Field(min_length=1, max_length=240)
    status: Literal["current", "drift", "classification_missing"]
    binding_inventory_evidence_ids: tuple[str, ...] = ()
    binding_classification_run_id: str | None = Field(default=None, max_length=240)
    binding_classification_run_digest: str | None = Field(default=None, pattern=_HEX64)
    binding_classification_source_row_digest: str | None = Field(default=None, pattern=_HEX64)
    superseded_binding_digest: str | None = Field(default=None, pattern=_HEX64)
    current_work_item_id: str | None = Field(default=None, max_length=240)
    current_classification_run_id: str | None = Field(default=None, max_length=240)
    current_classification_run_digest: str | None = Field(default=None, pattern=_HEX64)
    current_classification_source_row_digest: str | None = Field(
        default=None, pattern=_HEX64
    )
    current_canonical_path: str | None = Field(default=None, max_length=2048)
    current_public_url: str | None = Field(default=None, max_length=2048)
    current_classification_decision_set_digest: str | None = Field(
        default=None, pattern=_HEX64
    )
    current_inventory_evidence_ids: tuple[str, ...] = ()
    current_final_disposition: Literal["keep", "noindex", "redirect", "remove"] | None = None
    safe_next_step: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def require_typed_recovery(self) -> ContentDeliveryIdentityDriftRecovery:
        current_fields = (
            self.current_work_item_id,
            self.current_classification_run_id,
            self.current_classification_run_digest,
            self.current_classification_source_row_digest,
        )
        if self.status == "drift":
            if any(value is None for value in current_fields):
                raise ValueError("Drifted recovery needs the exact current row identity.")
        elif any(value is not None for value in current_fields):
            raise ValueError("Only a drifted identity exposes a current row identity.")
        return self


def build_content_delivery_identity_drift_recovery(
    binding: ContentDeliveryIdentityBinding,
    classification: ContentDeliveryClassificationLookup,
) -> ContentDeliveryIdentityDriftRecovery:
    """Never reports a drifted binding as usable; always names the current row."""

    projection = build_content_delivery_identity_current_projection(
        binding, classification, assessed_at=utc_now()
    )
    if projection.current_status == "exact_current":
        return ContentDeliveryIdentityDriftRecovery(
            binding_id=binding.binding_id,
            status="current",
            binding_inventory_evidence_ids=binding.inventory_evidence_ids,
            binding_classification_run_id=binding.classification_run_id,
            binding_classification_run_digest=binding.classification_run_digest,
            binding_classification_source_row_digest=binding.classification_source_row_digest,
            safe_next_step=CURRENT_SAFE_NEXT_STEP,
        )
    blocker = projection.current_blocker
    run = classification.run
    if classification.row_status != "exact" or run is None:
        return ContentDeliveryIdentityDriftRecovery(
            binding_id=binding.binding_id,
            status="classification_missing",
            binding_inventory_evidence_ids=binding.inventory_evidence_ids,
            binding_classification_run_id=binding.classification_run_id,
            binding_classification_run_digest=binding.classification_run_digest,
            binding_classification_source_row_digest=binding.classification_source_row_digest,
            safe_next_step=CLASSIFICATION_MISSING_SAFE_NEXT_STEP,
        )
    return ContentDeliveryIdentityDriftRecovery(
        binding_id=binding.binding_id,
        status="drift",
        binding_inventory_evidence_ids=binding.inventory_evidence_ids,
        binding_classification_run_id=binding.classification_run_id,
        binding_classification_run_digest=binding.classification_run_digest,
        binding_classification_source_row_digest=binding.classification_source_row_digest,
        superseded_binding_digest=binding.binding_digest,
        current_work_item_id=run.row.current_work_item_id,
        current_classification_run_id=run.run_id,
        current_classification_run_digest=run.run_digest,
        current_classification_source_row_digest=run.row.source_packet_row_digest,
        current_canonical_path=run.row.canonical_path,
        current_public_url=run.row.public_url,
        current_classification_decision_set_digest=run.decision_set_digest,
        current_inventory_evidence_ids=tuple(
            sorted(set(run.row.primary_evidence_ids) | set(run.row.lineage_evidence_ids))
        ),
        current_final_disposition=binding.final_disposition,
        safe_next_step=(
            DRIFT_SAFE_NEXT_STEP
            if blocker is not None and blocker.reason == "identity_classification_drift"
            else blocker.next_step
            if blocker is not None
            else DRIFT_SAFE_NEXT_STEP
        ),
    )


class ContentDeliveryIdentitySupersession(BaseModel):
    """Append-only rebind intent for one drifted identity; no vendor write."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["wilq_content_delivery_identity_supersession_v1"] = (
        "wilq_content_delivery_identity_supersession_v1"
    )
    receipt_id: str = Field(min_length=1, max_length=240)
    receipt_digest: str = Field(pattern=_HEX64)
    superseded_binding_id: str = Field(min_length=1, max_length=240)
    superseded_binding_digest: str = Field(pattern=_HEX64)
    rebound_work_item_id: str = Field(min_length=1, max_length=240)
    rebound_classification_run_id: str = Field(min_length=1, max_length=240)
    rebound_classification_run_digest: str = Field(pattern=_HEX64)
    rebound_classification_source_row_digest: str = Field(pattern=_HEX64)
    recorded_by: str = Field(min_length=1, max_length=160)
    recorded_at: datetime

    @model_validator(mode="after")
    def require_exact_supersession(self) -> ContentDeliveryIdentitySupersession:
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise ValueError("Supersession time must be timezone-aware.")
        payload = self.model_dump(
            mode="json", exclude={"receipt_id", "receipt_digest"}
        )
        expected = canonical_json_digest(payload)
        if (
            self.receipt_digest != expected
            or self.receipt_id != f"content_delivery_identity_supersession_{expected[:24]}"
        ):
            raise ValueError("Supersession receipt ID/digest does not match its payload.")
        return self


def build_content_delivery_identity_supersession(
    recovery: ContentDeliveryIdentityDriftRecovery,
    *,
    recorded_by: str,
    recorded_at: datetime | None = None,
) -> ContentDeliveryIdentitySupersession:
    """Only a drifted identity may be superseded; current/missing raise."""

    if recovery.status != "drift":
        raise ValueError("Only a drifted delivery identity may be superseded.")
    if not all(
        (
            recovery.superseded_binding_digest,
            recovery.current_work_item_id,
            recovery.current_classification_run_id,
            recovery.current_classification_run_digest,
            recovery.current_classification_source_row_digest,
        )
    ):
        raise ValueError("Drifted recovery must carry the exact rebound inputs.")
    staged = ContentDeliveryIdentitySupersession.model_construct(
        schema_version="wilq_content_delivery_identity_supersession_v1",
        receipt_id="content_delivery_identity_supersession_pending",
        receipt_digest="0" * 64,
        superseded_binding_id=recovery.binding_id,
        superseded_binding_digest=recovery.superseded_binding_digest,
        rebound_work_item_id=recovery.current_work_item_id,
        rebound_classification_run_id=recovery.current_classification_run_id,
        rebound_classification_run_digest=recovery.current_classification_run_digest,
        rebound_classification_source_row_digest=(
            recovery.current_classification_source_row_digest
        ),
        recorded_by=recorded_by,
        recorded_at=(recorded_at or utc_now()).astimezone(UTC),
    )
    payload = staged.model_dump(mode="json", exclude={"receipt_id", "receipt_digest"})
    digest = canonical_json_digest(payload)
    return ContentDeliveryIdentitySupersession.model_validate(
        {
            "receipt_id": f"content_delivery_identity_supersession_{digest[:24]}",
            "receipt_digest": digest,
            **payload,
        }
    )


class ContentDeliveryIdentitySupersessionRecordResult(BaseModel):
    """Append-only store outcome for one supersession receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["created", "idempotent", "conflict"]
    receipt: ContentDeliveryIdentitySupersession


def build_content_delivery_identity_rebind_command(
    recovery: ContentDeliveryIdentityDriftRecovery,
    *,
    recorded_by: str,
    recorded_at: datetime | None = None,
) -> ContentDeliveryIdentityCommand:
    """Exact rebind command for a drifted identity; current/missing raise."""

    if recovery.status != "drift":
        raise ValueError("Only a drifted delivery identity may be rebound.")
    if (
        not recovery.superseded_binding_digest
        or not recovery.current_work_item_id
        or not recovery.current_canonical_path
        or not recovery.current_public_url
        or not recovery.current_classification_run_id
        or not recovery.current_classification_run_digest
        or not recovery.current_classification_decision_set_digest
        or not recovery.current_classification_source_row_digest
        or not recovery.current_inventory_evidence_ids
        or recovery.current_final_disposition is None
    ):
        raise ValueError("Drifted recovery must carry the exact rebind inputs.")
    return ContentDeliveryIdentityCommand(
        canonical_path=recovery.current_canonical_path,
        public_url=recovery.current_public_url,
        current_work_item_id=recovery.current_work_item_id,
        classification_run_id=recovery.current_classification_run_id,
        classification_run_digest=recovery.current_classification_run_digest,
        classification_decision_set_digest=(
            recovery.current_classification_decision_set_digest
        ),
        classification_source_row_digest=recovery.current_classification_source_row_digest,
        inventory_evidence_ids=recovery.current_inventory_evidence_ids,
        inventory_evidence_digest=inventory_evidence_digest(
            recovery.current_inventory_evidence_ids
        ),
        final_disposition=recovery.current_final_disposition,
        recorded_by=recorded_by,
        recorded_at=(recorded_at or utc_now()).astimezone(UTC),
    )


def delivery_identity_rebind_action_id(receipt_digest: str) -> str:
    return f"act_content_delivery_identity_rebind_{receipt_digest[:24]}"


def build_content_delivery_identity_rebind_action(
    recovery: ContentDeliveryIdentityDriftRecovery,
    *,
    recorded_by: str,
    recorded_at: datetime | None = None,
) -> ActionObject:
    """Local-authority ActionObject for one rebind; blocked when not drifted."""

    common = {
        "action_type": CONTENT_DELIVERY_IDENTITY_REBIND_ACTION_TYPE,
        "connector": "wordpress_ekologus",
        "local_authority_only": True,
        "delivery_identity_status": recovery.status,
    }
    if recovery.status != "drift":
        return ActionObject(
            id=f"act_content_delivery_identity_rebind_blocked_{recovery.binding_id[:24]}",
            title="Zarejestruj nową exact current identity",
            domain=OpportunityDomain.content,
            connector="wordpress_ekologus",
            mode=ActionMode.apply,
            risk=ActionRisk.low,
            status=ActionStatus.blocked,
            evidence_ids=list(recovery.binding_inventory_evidence_ids),
            validation_status="not_validated",
            created_by=recorded_by,
            human_diagnosis=(
                "Tylko drifted identity może zostać zastąpiona; ten binding nie jest drifted."
            ),
            recommended_reason=recovery.safe_next_step,
            payload={
                **common,
                "apply_allowed": False,
                "api_mutation_ready": False,
                "blocker_code": REBIND_BLOCKER_CODE,
                "safe_next_step": recovery.safe_next_step,
            },
        )
    receipt = build_content_delivery_identity_supersession(
        recovery, recorded_by=recorded_by, recorded_at=recorded_at
    )
    command = build_content_delivery_identity_rebind_command(
        recovery, recorded_by=recorded_by, recorded_at=recorded_at
    )
    return ActionObject(
        id=delivery_identity_rebind_action_id(receipt.receipt_digest),
        title="Zastąp drifted delivery identity nową exact current identity",
        domain=OpportunityDomain.content,
        connector="wordpress_ekologus",
        mode=ActionMode.apply,
        risk=ActionRisk.low,
        status=ActionStatus.ready_to_apply,
        evidence_ids=list(recovery.current_inventory_evidence_ids),
        validation_status="not_validated",
        created_by=recorded_by,
        human_diagnosis=(
            "Apply zapisuje lokalny receipt supersession i mintuje nową identity z bieżącego "
            "wiersza klasyfikacji; bez zapisu u vendora."
        ),
        recommended_reason=recovery.safe_next_step,
        payload={
            **common,
            "mode": "apply",
            "apply_allowed": True,
            "api_mutation_ready": True,
            "destructive": False,
            "preview_contract": "content_delivery_identity_rebind_v1",
            "supersession": receipt.model_dump(mode="json"),
            "rebind_command": command.model_dump(mode="json"),
            "payload_preview": [
                {
                    "id": receipt.receipt_id,
                    "operation_type": "record_one_delivery_identity_supersession",
                    "preview_contract": "content_delivery_identity_rebind_v1",
                    "apply_allowed": True,
                    "api_mutation_ready": True,
                    "destructive": False,
                    "superseded_binding_id": receipt.superseded_binding_id,
                    "rebound_work_item_id": receipt.rebound_work_item_id,
                }
            ],
        },
    )


def execute_content_delivery_identity_rebind(
    action: ActionObject,
    *,
    store: Any,
    audit_events: list[object],
    confirmed_by: str | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, object] | None, list[str]]:
    """Apply one local rebind: record the supersession, then mint the identity."""

    del audit_events, confirmed_by, now
    payload = action.payload or {}
    if (
        action.status != "ready_to_apply"
        or action.connector != "wordpress_ekologus"
        or payload.get("action_type") != CONTENT_DELIVERY_IDENTITY_REBIND_ACTION_TYPE
        or payload.get("local_authority_only") is not True
    ):
        return None, ["Delivery identity rebind action is not a ready local authority action."]
    try:
        receipt = ContentDeliveryIdentitySupersession.model_validate(
            payload["supersession"]
        )
        command = ContentDeliveryIdentityCommand.model_validate(payload["rebind_command"])
    except (KeyError, TypeError, ValueError):
        return None, ["Delivery identity rebind payload is invalid."]
    if action.id != delivery_identity_rebind_action_id(receipt.receipt_digest):
        return None, ["Delivery identity rebind action payload changed before apply."]
    identity = store.record_content_delivery_identity(command)
    if identity.status == "conflict":
        return None, ["Delivery identity rebind conflicts with an existing identity."]
    supersession = store.record_content_delivery_identity_supersession(receipt)
    return {
        "supersession_receipt_id": supersession.receipt.receipt_id,
        "supersession_status": supersession.status,
        "rebound_binding_id": identity.binding.binding_id,
        "rebound_binding_status": identity.status,
        "rebound_binding_current_status": identity.current.current_status,
        "external_write_attempted": False,
    }, []


__all__ = [
    "CLASSIFICATION_MISSING_SAFE_NEXT_STEP",
    "CURRENT_SAFE_NEXT_STEP",
    "DRIFT_SAFE_NEXT_STEP",
    "ContentDeliveryIdentityDriftRecovery",
    "ContentDeliveryIdentitySupersession",
    "ContentDeliveryIdentitySupersessionRecordResult",
    "CONTENT_DELIVERY_IDENTITY_REBIND_ACTION_TYPE",
    "CONTENT_DELIVERY_IDENTITY_REBIND_ADAPTER",
    "execute_content_delivery_identity_rebind",
    "REBIND_BLOCKER_CODE",
    "build_content_delivery_identity_drift_recovery",
    "build_content_delivery_identity_rebind_action",
    "delivery_identity_rebind_action_id",
    "build_content_delivery_identity_rebind_command",
    "build_content_delivery_identity_supersession",
]
