from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from typing import Any, Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
)
from wilq.content.workflow.target.target_mapping import (
    ContentTargetDraftPreview,
    ContentTargetMappingConfirmation,
    ContentTargetMappingConfirmationCommand,
    ContentTargetMappingPreview,
    new_content_target_mapping_confirmation,
)
from wilq.content.workflow.target.target_mapping_blockers import ContentTargetMappingBlocker
from wilq.content.workflow.target.target_mapping_preview_models import (
    ContentTargetDraftPreviewBlocker,
)

CONTENT_TARGET_MAPPING_RECORD_TYPE: Literal["content_target_mapping_confirmation"] = (
    "content_target_mapping_confirmation"
)
CONTENT_TARGET_MAPPING_RECORD_VERSION: Literal[1] = 1


class ContentTargetMappingPersistenceError(ValueError):
    """A fail-closed persisted mapping error that never includes stored JSON."""


class ContentTargetMappingPersistedRecord(BaseModel):
    """One immutable confirmation and the exact observation it confirmed."""

    model_config = ConfigDict(extra="forbid")

    record_type: Literal["content_target_mapping_confirmation"] = CONTENT_TARGET_MAPPING_RECORD_TYPE
    version: Literal[1] = CONTENT_TARGET_MAPPING_RECORD_VERSION
    preview_snapshot: ContentTargetMappingPreview
    preview_snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    confirmation: ContentTargetMappingConfirmation

    @model_validator(mode="after")
    def require_exact_confirmed_snapshot(self) -> Self:
        preview = self.preview_snapshot
        confirmation = self.confirmation
        target = preview.target
        if (
            preview.status != "ready_for_human_mapping"
            or target is None
            or preview.binding_digest is None
            or preview.confirmation is not None
            or bool(preview.blockers)
            or target.target_contract.authority != "observation_only"
            or target.target_contract.write_authorized is not False
        ):
            raise ValueError("Persisted target mapping snapshot is not an exact observation.")
        if (
            preview.work_item_id != confirmation.work_item_id
            or preview.revision != confirmation.revision
            or target.target_contract_digest != confirmation.target_contract_digest
            or preview.binding_digest != confirmation.binding_digest
        ):
            raise ValueError("Persisted target mapping identities do not match.")
        if preview.binding_digest != _canonical_target_mapping_binding_digest(preview):
            raise ValueError("Persisted target mapping binding digest does not match.")

        command = ContentTargetMappingConfirmationCommand(
            expected_revision_digest=confirmation.revision.content_digest,
            expected_target_contract_digest=confirmation.target_contract_digest,
            expected_binding_digest=confirmation.binding_digest,
            delivery_scope=confirmation.delivery_scope,
            selections=confirmation.selections,
            confirmed_by=confirmation.confirmed_by,
        )
        recomputed = new_content_target_mapping_confirmation(
            work_item_id=confirmation.work_item_id,
            preview=preview,
            command=command,
            confirmation_number=confirmation.confirmation_number,
            created_at=confirmation.created_at,
        )
        if recomputed.confirmation_digest != confirmation.confirmation_digest:
            raise ValueError("Persisted target mapping confirmation digest does not match.")
        if canonical_target_mapping_preview_digest(preview) != self.preview_snapshot_digest:
            raise ValueError("Persisted target mapping preview digest does not match.")
        return self


class ContentTargetMappingDraftState(BaseModel):
    """Latest local state for snapshot-first mapping and draft preview reads."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["snapshot_available", "legacy_confirmation"]
    confirmation: ContentTargetMappingConfirmation
    preview_snapshot: ContentTargetMappingPreview | None = None
    preview_snapshot_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def require_state_shape(self) -> Self:
        snapshot_fields_present = (
            self.preview_snapshot is not None and self.preview_snapshot_digest is not None
        )
        if self.status == "snapshot_available" and not snapshot_fields_present:
            raise ValueError("Snapshot-available target mapping state requires a snapshot.")
        if self.status == "legacy_confirmation" and (
            self.preview_snapshot is not None or self.preview_snapshot_digest is not None
        ):
            raise ValueError("Legacy target mapping state cannot invent a snapshot.")
        return self


DecodedTargetMappingPayload = ContentTargetMappingPersistedRecord | ContentTargetMappingConfirmation


def build_content_target_mapping_persisted_record(
    *,
    preview: ContentTargetMappingPreview,
    confirmation: ContentTargetMappingConfirmation,
) -> ContentTargetMappingPersistedRecord:
    snapshot = ContentTargetMappingPreview.model_validate(
        preview.model_copy(update={"confirmation": None}, deep=True).model_dump(mode="json")
    )
    return ContentTargetMappingPersistedRecord(
        preview_snapshot=snapshot,
        preview_snapshot_digest=canonical_target_mapping_preview_digest(snapshot),
        confirmation=confirmation.model_copy(deep=True),
    )


def canonical_target_mapping_preview_digest(preview: ContentTargetMappingPreview) -> str:
    return _canonical_sha256(preview.model_dump(mode="json"))


def decode_content_target_mapping_payload(
    payload_json: object,
    *,
    sql_scalars: Mapping[str, object],
) -> DecodedTargetMappingPayload:
    """Dispatch legacy/current payloads strictly and verify the SQL projection."""

    if type(payload_json) is not str:
        raise ContentTargetMappingPersistenceError(
            "Persisted target mapping payload must be JSON text."
        )
    try:
        payload = json.loads(
            payload_json,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_nonfinite_json,
        )
    except ValueError:
        raise ContentTargetMappingPersistenceError(
            "Persisted target mapping payload is not valid JSON."
        ) from None
    if not isinstance(payload, dict):
        raise ContentTargetMappingPersistenceError(
            "Persisted target mapping payload must be an object."
        )

    has_record_type = "record_type" in payload
    has_version = "version" in payload
    try:
        if not has_record_type and not has_version:
            decoded: DecodedTargetMappingPayload = ContentTargetMappingConfirmation.model_validate(
                payload
            )
        elif not has_record_type or not has_version:
            raise ContentTargetMappingPersistenceError(
                "Persisted target mapping discriminator is malformed."
            )
        elif payload["record_type"] != CONTENT_TARGET_MAPPING_RECORD_TYPE:
            raise ContentTargetMappingPersistenceError(
                "Persisted target mapping record type is unsupported."
            )
        elif payload["version"] != CONTENT_TARGET_MAPPING_RECORD_VERSION:
            raise ContentTargetMappingPersistenceError(
                "Persisted target mapping record version is unsupported."
            )
        else:
            decoded = ContentTargetMappingPersistedRecord.model_validate(payload)
    except ContentTargetMappingPersistenceError:
        raise
    except (ValueError, TypeError):
        raise ContentTargetMappingPersistenceError(
            "Persisted target mapping payload is malformed."
        ) from None

    confirmation = (
        decoded.confirmation
        if isinstance(decoded, ContentTargetMappingPersistedRecord)
        else decoded
    )
    _verify_sql_scalars(confirmation, sql_scalars)
    return decoded


def draft_state_from_decoded_payload(
    decoded: DecodedTargetMappingPayload,
) -> ContentTargetMappingDraftState:
    if isinstance(decoded, ContentTargetMappingPersistedRecord):
        return ContentTargetMappingDraftState(
            status="snapshot_available",
            confirmation=decoded.confirmation,
            preview_snapshot=decoded.preview_snapshot,
            preview_snapshot_digest=decoded.preview_snapshot_digest,
        )
    return ContentTargetMappingDraftState(
        status="legacy_confirmation",
        confirmation=decoded,
    )


def build_persisted_target_mapping_preview(
    *,
    state: ContentTargetMappingDraftState,
    revisions: list[ContentDraftRevision],
    human_review: ContentDraftRevisionReview | None,
) -> ContentTargetMappingPreview:
    """Project persisted evidence through the current local revision approval."""

    snapshot = state.preview_snapshot
    if state.status != "snapshot_available" or snapshot is None:
        raise ValueError("Persisted target mapping state does not contain a snapshot.")
    local_revision = next(
        (
            revision
            for revision in revisions
            if revision.work_item_id == snapshot.work_item_id
            and revision.revision_id == snapshot.revision.revision_id
            and revision.content_digest == snapshot.revision.content_digest
        ),
        None,
    )
    if _is_exact_approved_review(snapshot, local_revision, human_review):
        return snapshot.model_copy(
            update={"confirmation": state.confirmation},
            deep=True,
        )
    blocker = ContentTargetMappingBlocker(
        code="revision_not_approved",
        label="Dokument wymaga zatwierdzenia",
        reason=(
            "Mapowanie można przygotować wyłącznie dla dokładnej rewizji "
            "zatwierdzonej przez człowieka."
        ),
        next_step="Otwórz review tej rewizji i zapisz decyzję człowieka.",
    )
    return ContentTargetMappingPreview(
        work_item_id=snapshot.work_item_id,
        revision=snapshot.revision,
        status="blocked",
        components=[
            component.model_copy(update={"status": "blocked", "reason": blocker.reason})
            for component in snapshot.components
        ],
        blockers=[blocker],
        caveats=["Nie przygotowano payloadu, draftu ani zapisu do WordPressa."],
    )


def build_legacy_target_mapping_draft_preview(
    state: ContentTargetMappingDraftState,
) -> ContentTargetDraftPreview:
    """Expose a typed blocker without inventing a snapshot for a legacy decision."""

    if state.status != "legacy_confirmation":
        raise ValueError("Legacy target mapping projection requires a legacy confirmation.")
    confirmation = state.confirmation
    return ContentTargetDraftPreview(
        work_item_id=confirmation.work_item_id,
        revision=confirmation.revision,
        status="blocked",
        blockers=[
            ContentTargetDraftPreviewBlocker(
                code="mapping_stale",
                label="Potwierdzenie mapowania wymaga odświeżenia",
                reason=(
                    "Historyczne potwierdzenie nie zawiera dokładnego podglądu "
                    "targetu z chwili decyzji człowieka."
                ),
                next_step=(
                    "Otwórz przypisanie dokumentu do dev i zapisz nowe jawne "
                    "potwierdzenie aktualnego odczytu."
                ),
            )
        ],
        caveats=["Nie przygotowano ActionObjectu, draftu ani zapisu do WordPressa."],
    )


def confirmation_for_live_target_mapping(
    *,
    state: ContentTargetMappingDraftState | None,
    work_item_id: str,
    revision_id: str,
    mapping: ContentTargetMappingPreview,
) -> ContentTargetMappingConfirmation | None:
    """Return only a snapshot-bearing confirmation matching the current live read."""

    if state is None or state.status != "snapshot_available" or mapping.target is None:
        return None
    confirmation = state.confirmation
    if (
        mapping.status == "ready_for_human_mapping"
        and confirmation.work_item_id == work_item_id
        and confirmation.revision.revision_id == revision_id
        and confirmation.revision == mapping.revision
        and confirmation.target_contract_digest == mapping.target.target_contract_digest
        and confirmation.binding_digest == mapping.binding_digest
    ):
        return confirmation
    return None


def content_target_mapping_confirmation_scalars(
    confirmation: ContentTargetMappingConfirmation,
) -> dict[str, object]:
    return {
        "confirmation_id": confirmation.confirmation_id,
        "work_item_id": confirmation.work_item_id,
        "revision_id": confirmation.revision.revision_id,
        "revision_digest": confirmation.revision.content_digest,
        "target_contract_digest": confirmation.target_contract_digest,
        "binding_digest": confirmation.binding_digest,
        "confirmation_number": confirmation.confirmation_number,
        "confirmation_digest": confirmation.confirmation_digest,
        "created_at": confirmation.created_at,
    }


def _verify_sql_scalars(
    confirmation: ContentTargetMappingConfirmation,
    sql_scalars: Mapping[str, object],
) -> None:
    expected = content_target_mapping_confirmation_scalars(confirmation)
    for key, expected_value in expected.items():
        actual_value = sql_scalars.get(key)
        if type(actual_value) is not type(expected_value) or actual_value != expected_value:
            raise ContentTargetMappingPersistenceError(
                "Persisted target mapping SQL columns do not match the payload."
            )


def _canonical_sha256(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _canonical_target_mapping_binding_digest(preview: ContentTargetMappingPreview) -> str:
    # Record v1 deliberately freezes the digest schema it verifies. A future
    # mapping digest needs a new record version instead of silently reinterpreting v1.
    if preview.target is None:
        raise ValueError("Persisted target mapping binding requires an exact target.")
    return _canonical_sha256(
        {
            "revision": preview.revision.model_dump(mode="json"),
            "target_contract_digest": preview.target.target_contract_digest,
            "components": [component.model_dump(mode="json") for component in preview.components],
        }
    )


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key.")
        result[key] = value
    return result


def _reject_nonfinite_json(_: str) -> Never:
    raise ValueError("Non-finite JSON value.")


def _is_exact_approved_review(
    snapshot: ContentTargetMappingPreview,
    revision: ContentDraftRevision | None,
    review: ContentDraftRevisionReview | None,
) -> bool:
    return bool(
        revision is not None
        and review is not None
        and review.decision == "approved"
        and review.work_item_id == snapshot.work_item_id
        and review.revision_id == snapshot.revision.revision_id
        and review.revision_digest == snapshot.revision.content_digest
    )


__all__ = [
    "CONTENT_TARGET_MAPPING_RECORD_TYPE",
    "CONTENT_TARGET_MAPPING_RECORD_VERSION",
    "ContentTargetMappingDraftState",
    "ContentTargetMappingPersistedRecord",
    "ContentTargetMappingPersistenceError",
    "build_legacy_target_mapping_draft_preview",
    "build_content_target_mapping_persisted_record",
    "build_persisted_target_mapping_preview",
    "canonical_target_mapping_preview_digest",
    "confirmation_for_live_target_mapping",
    "content_target_mapping_confirmation_scalars",
    "decode_content_target_mapping_payload",
    "draft_state_from_decoded_payload",
]
