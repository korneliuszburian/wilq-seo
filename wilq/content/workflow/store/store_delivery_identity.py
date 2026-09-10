"""Append-only persistence for exact content delivery identity bindings."""

from __future__ import annotations

import sqlite3
from typing import cast

from wilq.content.workflow.decisions.production import project_content_production_classification
from wilq.content.workflow.delivery_identity import (
    ContentDeliveryClassificationLookup,
    ContentDeliveryIdentityBinding,
    ContentDeliveryIdentityCommand,
    ContentDeliveryIdentityRecordResult,
    ContentDeliveryRecord,
    build_content_delivery_record,
    reconcile_content_delivery_identity,
)
from wilq.content.workflow.store.store_production_classification import (
    _classification_from_row,
)
from wilq.storage.model_json import model_json


class ContentDeliveryIdentityStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_content_delivery_identity(
        self,
        command: ContentDeliveryIdentityCommand,
    ) -> ContentDeliveryIdentityRecordResult:
        """Reconcile and append one exact receipt without any fallback lookup."""

        accepted = ContentDeliveryIdentityCommand.model_validate_json(
            command.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            classification = _load_exact_classification_projection(connection, accepted)
            binding = reconcile_content_delivery_identity(accepted, classification)
            delivery_record = build_content_delivery_record(binding)
            existing_row = connection.execute(
                "SELECT * FROM content_delivery_identity_bindings WHERE binding_id = ?",
                (binding.binding_id,),
            ).fetchone()
            if existing_row is not None:
                existing = _binding_from_row(existing_row)
                existing_record = _delivery_record_for_binding(connection, existing.binding_id)
                return ContentDeliveryIdentityRecordResult(
                    status=(
                        "idempotent"
                        if existing.binding_digest == binding.binding_digest
                        else "conflict"
                    ),
                    binding=existing,
                    delivery_record=existing_record,
                )
            digest_row = connection.execute(
                "SELECT * FROM content_delivery_identity_bindings WHERE binding_digest = ?",
                (binding.binding_digest,),
            ).fetchone()
            if digest_row is not None:
                return ContentDeliveryIdentityRecordResult(
                    status="conflict",
                    binding=_binding_from_row(digest_row),
                    delivery_record=_delivery_record_for_binding(
                        connection, cast(str, digest_row["binding_id"])
                    ),
                )
            connection.execute(
                """
                INSERT INTO content_delivery_identity_bindings (
                  binding_id, binding_digest, canonical_path, public_url,
                  current_work_item_id, retained_work_item_id,
                  classification_run_id, classification_run_digest,
                  classification_source_row_digest, inventory_evidence_digest,
                  status, recorded_by, recorded_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    binding.binding_id,
                    binding.binding_digest,
                    binding.canonical_path,
                    binding.public_url,
                    binding.current_work_item_id,
                    binding.retained_work_item_id,
                    binding.classification_run_id,
                    binding.classification_run_digest,
                    binding.classification_source_row_digest,
                    binding.inventory_evidence_digest,
                    binding.status,
                    binding.recorded_by,
                    binding.recorded_at.isoformat(),
                    model_json(binding),
                ),
            )
            connection.execute(
                """
                INSERT INTO content_delivery_records (
                  record_id, record_digest, binding_id, binding_digest,
                  final_disposition, content_state, delivery_status,
                  robot_ready, blocker_code, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    delivery_record.record_id,
                    delivery_record.record_digest,
                    delivery_record.binding_id,
                    delivery_record.binding_digest,
                    delivery_record.final_disposition,
                    delivery_record.content_state,
                    delivery_record.delivery_status,
                    int(delivery_record.robot_ready),
                    delivery_record.blocker_code,
                    model_json(delivery_record),
                ),
            )
        return ContentDeliveryIdentityRecordResult(
            status="created", binding=binding, delivery_record=delivery_record
        )

    def load_content_delivery_identity(
        self, binding_id: str
    ) -> ContentDeliveryIdentityBinding | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM content_delivery_identity_bindings WHERE binding_id = ?",
                (binding_id,),
            ).fetchone()
        return None if row is None else _binding_from_row(row)

    def load_content_delivery_identity_record(
        self, binding_id: str
    ) -> ContentDeliveryIdentityRecordResult | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM content_delivery_identity_bindings WHERE binding_id = ?",
                (binding_id,),
            ).fetchone()
            if row is None:
                return None
            binding = _binding_from_row(row)
            delivery_record = _delivery_record_for_binding(connection, binding_id)
        return ContentDeliveryIdentityRecordResult(
            status="idempotent",
            binding=binding,
            delivery_record=delivery_record,
        )


def _load_exact_classification_projection(
    connection: sqlite3.Connection,
    command: ContentDeliveryIdentityCommand,
) -> ContentDeliveryClassificationLookup:
    row = connection.execute(
        """
        SELECT * FROM content_production_classifications
        WHERE run_id = ?
        LIMIT 1
        """,
        (command.classification_run_id,),
    ).fetchone()
    if row is None:
        return ContentDeliveryClassificationLookup(row_status="run_missing")
    run = _classification_from_row(row)
    matches = [
        item for item in run.rows if item.current_work_item_id == command.current_work_item_id
    ]
    if len(matches) != 1:
        return ContentDeliveryClassificationLookup(
            row_status="missing" if not matches else "ambiguous"
        )
    return ContentDeliveryClassificationLookup(
        row_status="exact",
        run=project_content_production_classification(run, matches[0]),
    )


def _delivery_record_for_binding(
    connection: sqlite3.Connection, binding_id: str
) -> ContentDeliveryRecord:
    row = connection.execute(
        "SELECT payload_json FROM content_delivery_records WHERE binding_id = ?",
        (binding_id,),
    ).fetchone()
    if row is None:
        raise ValueError("Content delivery identity has no runtime delivery record.")
    return ContentDeliveryRecord.model_validate_json(cast(str, row["payload_json"]), strict=True)


def _binding_from_row(row: sqlite3.Row) -> ContentDeliveryIdentityBinding:
    binding = ContentDeliveryIdentityBinding.model_validate_json(
        cast(str, row["payload_json"]), strict=True
    )
    expected = (
        binding.binding_id,
        binding.binding_digest,
        binding.canonical_path,
        binding.public_url,
        binding.current_work_item_id,
        binding.retained_work_item_id,
        binding.classification_run_id,
        binding.classification_run_digest,
        binding.classification_source_row_digest,
        binding.inventory_evidence_digest,
        binding.status,
        binding.recorded_by,
        binding.recorded_at.isoformat(),
    )
    stored = tuple(
        row[name]
        for name in (
            "binding_id",
            "binding_digest",
            "canonical_path",
            "public_url",
            "current_work_item_id",
            "retained_work_item_id",
            "classification_run_id",
            "classification_run_digest",
            "classification_source_row_digest",
            "inventory_evidence_digest",
            "status",
            "recorded_by",
            "recorded_at",
        )
    )
    if stored != expected:
        raise ValueError("Stored content delivery identity scalars do not match payload.")
    return binding


__all__ = ["ContentDeliveryIdentityStoreMixin"]
