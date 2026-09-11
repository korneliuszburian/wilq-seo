from __future__ import annotations

import sqlite3

from wilq.content.workflow.target.target_mapping import (
    ContentTargetMappingConfirmation,
    ContentTargetMappingConfirmationCommand,
    ContentTargetMappingConfirmationResult,
    ContentTargetMappingPreview,
    new_content_target_mapping_confirmation,
)
from wilq.content.workflow.target.target_mapping_persistence import (
    ContentTargetMappingDraftState,
    ContentTargetMappingPersistedRecord,
    build_content_target_mapping_persisted_record,
    content_target_mapping_confirmation_scalars,
    decode_content_target_mapping_payload,
    draft_state_from_decoded_payload,
)
from wilq.schemas.core import utc_now
from wilq.storage.model_json import model_json as _model_json

_TARGET_MAPPING_SCALAR_COLUMNS = (
    "confirmation_id",
    "work_item_id",
    "revision_id",
    "revision_digest",
    "target_contract_digest",
    "binding_digest",
    "confirmation_number",
    "confirmation_digest",
    "created_at",
)


class _TargetMappingConfirmationStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_target_mapping_confirmation(
        self,
        *,
        work_item_id: str,
        preview: ContentTargetMappingPreview,
        command: ContentTargetMappingConfirmationCommand,
    ) -> ContentTargetMappingConfirmationResult:
        if work_item_id != preview.work_item_id:
            raise ValueError("Zadanie potwierdzenia mapowania nie pasuje do podglądu.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            latest_revision = _latest_target_mapping_payload_for_revision(
                connection,
                work_item_id=work_item_id,
                revision_id=preview.revision.revision_id,
            )
            latest = _latest_exact_target_mapping_payload(
                connection,
                work_item_id=work_item_id,
                revision_id=preview.revision.revision_id,
                target_contract_digest=(
                    "" if preview.target is None else preview.target.target_contract_digest
                ),
                binding_digest="" if preview.binding_digest is None else preview.binding_digest,
            )
            latest_confirmation = (
                None
                if latest is None
                else (
                    latest.confirmation
                    if isinstance(latest, ContentTargetMappingPersistedRecord)
                    else latest
                )
            )
            confirmation = new_content_target_mapping_confirmation(
                work_item_id=work_item_id,
                preview=preview,
                command=command,
                confirmation_number=(
                    1
                    if latest_confirmation is None
                    else latest_confirmation.confirmation_number + 1
                ),
                created_at=utc_now().isoformat(),
            )
            if (
                isinstance(latest_revision, ContentTargetMappingPersistedRecord)
                and latest_revision.confirmation.confirmation_digest
                == confirmation.confirmation_digest
            ):
                return ContentTargetMappingConfirmationResult(
                    status="idempotent",
                    confirmation=latest_revision.confirmation,
                )

            record = build_content_target_mapping_persisted_record(
                preview=preview,
                confirmation=confirmation,
            )
            scalars = content_target_mapping_confirmation_scalars(confirmation)
            connection.execute(
                """
                INSERT INTO content_target_mapping_confirmations (
                  confirmation_id, work_item_id, revision_id, revision_digest,
                  target_contract_digest, binding_digest, confirmation_number,
                  confirmation_digest, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scalars["confirmation_id"],
                    scalars["work_item_id"],
                    scalars["revision_id"],
                    scalars["revision_digest"],
                    scalars["target_contract_digest"],
                    scalars["binding_digest"],
                    scalars["confirmation_number"],
                    scalars["confirmation_digest"],
                    scalars["created_at"],
                    _model_json(record),
                ),
            )
        return ContentTargetMappingConfirmationResult(
            status="created",
            confirmation=confirmation,
        )

    def load_target_mapping_confirmation(
        self,
        *,
        work_item_id: str,
        revision_id: str,
        target_contract_digest: str,
        binding_digest: str,
    ) -> ContentTargetMappingConfirmation | None:
        with self._connect() as connection:
            payload = _latest_exact_target_mapping_payload(
                connection,
                work_item_id=work_item_id,
                revision_id=revision_id,
                target_contract_digest=target_contract_digest,
                binding_digest=binding_digest,
            )
        if isinstance(payload, ContentTargetMappingPersistedRecord):
            return payload.confirmation
        return payload

    def load_target_mapping_draft_state(
        self,
        *,
        work_item_id: str,
        revision_id: str,
    ) -> ContentTargetMappingDraftState | None:
        with self._connect() as connection:
            payload = _latest_target_mapping_payload_for_revision(
                connection,
                work_item_id=work_item_id,
                revision_id=revision_id,
            )
        return None if payload is None else draft_state_from_decoded_payload(payload)


def _latest_target_mapping_payload_for_revision(
    connection: sqlite3.Connection,
    *,
    work_item_id: str,
    revision_id: str,
) -> ContentTargetMappingPersistedRecord | ContentTargetMappingConfirmation | None:
    row = connection.execute(
        """
        SELECT confirmation_id, work_item_id, revision_id, revision_digest,
               target_contract_digest, binding_digest, confirmation_number,
               confirmation_digest, created_at, payload_json
        FROM content_target_mapping_confirmations
        WHERE work_item_id = ? AND revision_id = ?
        ORDER BY created_at DESC, confirmation_id DESC
        LIMIT 1
        """,
        (work_item_id, revision_id),
    ).fetchone()
    return None if row is None else _decode_target_mapping_row(row)


def _latest_exact_target_mapping_payload(
    connection: sqlite3.Connection,
    *,
    work_item_id: str,
    revision_id: str,
    target_contract_digest: str,
    binding_digest: str,
) -> ContentTargetMappingPersistedRecord | ContentTargetMappingConfirmation | None:
    row = connection.execute(
        """
        SELECT confirmation_id, work_item_id, revision_id, revision_digest,
               target_contract_digest, binding_digest, confirmation_number,
               confirmation_digest, created_at, payload_json
        FROM content_target_mapping_confirmations
        WHERE work_item_id = ? AND revision_id = ? AND target_contract_digest = ?
          AND binding_digest = ?
        ORDER BY confirmation_number DESC, confirmation_id DESC
        LIMIT 1
        """,
        (work_item_id, revision_id, target_contract_digest, binding_digest),
    ).fetchone()
    return None if row is None else _decode_target_mapping_row(row)


def _decode_target_mapping_row(
    row: sqlite3.Row,
) -> ContentTargetMappingPersistedRecord | ContentTargetMappingConfirmation:
    return decode_content_target_mapping_payload(
        row["payload_json"],
        sql_scalars={column: row[column] for column in _TARGET_MAPPING_SCALAR_COLUMNS},
    )


__all__ = ["_TargetMappingConfirmationStoreMixin"]
