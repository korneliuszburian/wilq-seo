"""Append-only persistence for exact content delivery identity bindings."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import cast

from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationRun,
    project_content_production_classification,
)
from wilq.content.workflow.delivery_identity import (
    ContentDeliveryClassificationLookup,
    ContentDeliveryIdentityBinding,
    ContentDeliveryIdentityCommand,
    ContentDeliveryIdentityCurrentProjection,
    ContentDeliveryIdentityRecordResult,
    ContentDeliveryRecord,
    build_content_delivery_identity_current_projection,
    build_content_delivery_record,
    reconcile_content_delivery_identity,
)
from wilq.content.workflow.delivery_identity_recovery import (
    ContentDeliveryIdentitySupersession,
    ContentDeliveryIdentitySupersessionRecordResult,
)
from wilq.content.workflow.store.store_production_classification import (
    HISTORICAL_PRODUCTION_POLICY_IDS,
    _classification_from_row,
    load_latest_production_classification_from_connection,
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
                existing = binding_from_row(existing_row)
                existing_record = _delivery_record_for_binding(connection, existing.binding_id)
                return ContentDeliveryIdentityRecordResult(
                    status=(
                        "idempotent"
                        if existing.binding_digest == binding.binding_digest
                        else "conflict"
                    ),
                    binding=existing,
                    delivery_record=existing_record,
                    current=_current_identity_projection(connection, existing),
                )
            digest_row = connection.execute(
                "SELECT * FROM content_delivery_identity_bindings WHERE binding_digest = ?",
                (binding.binding_digest,),
            ).fetchone()
            if digest_row is not None:
                return ContentDeliveryIdentityRecordResult(
                    status="conflict",
                    binding=binding_from_row(digest_row),
                    delivery_record=_delivery_record_for_binding(
                        connection, cast(str, digest_row["binding_id"])
                    ),
                    current=_current_identity_projection(
                        connection, binding_from_row(digest_row)
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
            current = _current_identity_projection(connection, binding)
        return ContentDeliveryIdentityRecordResult(
            status="created", binding=binding, delivery_record=delivery_record, current=current
        )

    def load_content_delivery_identity(
        self, binding_id: str
    ) -> ContentDeliveryIdentityBinding | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM content_delivery_identity_bindings WHERE binding_id = ?",
                (binding_id,),
            ).fetchone()
        return None if row is None else binding_from_row(row)

    def list_content_delivery_identity_bindings(self) -> list[ContentDeliveryIdentityBinding]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM content_delivery_identity_bindings "
                "ORDER BY canonical_path, recorded_at, binding_id"
            ).fetchall()
        return [binding_from_row(row) for row in rows]

    def list_content_delivery_identity_current_projections(
        self,
    ) -> list[ContentDeliveryIdentityCurrentProjection]:
        with self._connect() as connection:
            latest = load_latest_production_classification_from_connection(connection)
            superseded_ids = {
                str(row["superseded_binding_id"])
                for row in connection.execute(
                    "SELECT DISTINCT superseded_binding_id "
                    "FROM content_delivery_identity_supersessions"
                ).fetchall()
            }
            rows = connection.execute(
                "SELECT * FROM content_delivery_identity_bindings "
                "ORDER BY canonical_path, recorded_at, binding_id"
            ).fetchall()
            assessed_at = datetime.now(UTC)
            return [
                build_content_delivery_identity_current_projection(
                    binding := binding_from_row(row),
                    _classification_lookup_for_binding(latest, binding),
                    assessed_at=assessed_at,
                    superseded=binding.binding_id in superseded_ids,
                )
                for row in rows
            ]

    def record_content_delivery_identity_supersession(
        self,
        receipt: ContentDeliveryIdentitySupersession,
    ) -> ContentDeliveryIdentitySupersessionRecordResult:
        """Append one supersession receipt with idempotent/conflict semantics."""

        accepted = ContentDeliveryIdentitySupersession.model_validate_json(
            receipt.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_row = connection.execute(
                "SELECT * FROM content_delivery_identity_supersessions WHERE receipt_id = ?",
                (accepted.receipt_id,),
            ).fetchone()
            if existing_row is not None:
                existing = _supersession_from_row(existing_row)
                return ContentDeliveryIdentitySupersessionRecordResult(
                    status=(
                        "idempotent"
                        if existing.receipt_digest == accepted.receipt_digest
                        else "conflict"
                    ),
                    receipt=existing,
                )
            digest_row = connection.execute(
                "SELECT * FROM content_delivery_identity_supersessions WHERE receipt_digest = ?",
                (accepted.receipt_digest,),
            ).fetchone()
            if digest_row is not None:
                return ContentDeliveryIdentitySupersessionRecordResult(
                    status="conflict",
                    receipt=_supersession_from_row(digest_row),
                )
            connection.execute(
                """
                INSERT INTO content_delivery_identity_supersessions (
                  receipt_id, receipt_digest, superseded_binding_id, rebound_work_item_id,
                  recorded_by, recorded_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    accepted.receipt_id,
                    accepted.receipt_digest,
                    accepted.superseded_binding_id,
                    accepted.rebound_work_item_id,
                    accepted.recorded_by,
                    accepted.recorded_at.isoformat(),
                    accepted.model_dump_json(),
                ),
            )
            return ContentDeliveryIdentitySupersessionRecordResult(
                status="created", receipt=accepted
            )

    def load_content_delivery_identity_supersession(
        self, receipt_id: str
    ) -> ContentDeliveryIdentitySupersession | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM content_delivery_identity_supersessions WHERE receipt_id = ?",
                (receipt_id,),
            ).fetchone()
            if row is None:
                return None
            return _supersession_from_row(row)

    def load_content_delivery_classification_lookup(
        self, binding: ContentDeliveryIdentityBinding
    ) -> ContentDeliveryClassificationLookup:
        with self._connect() as connection:
            latest = load_latest_production_classification_from_connection(connection)
        return _classification_lookup_for_binding(latest, binding)

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
            binding = binding_from_row(row)
            delivery_record = _delivery_record_for_binding(connection, binding_id)
            current = _current_identity_projection(connection, binding)
        return ContentDeliveryIdentityRecordResult(
            status="idempotent",
            binding=binding,
            delivery_record=delivery_record,
            current=current,
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
    if run.input.policy_id in HISTORICAL_PRODUCTION_POLICY_IDS:
        return ContentDeliveryClassificationLookup(row_status="not_current")
    latest = load_latest_production_classification_from_connection(connection)
    if latest is None or latest.run_id != run.run_id:
        return ContentDeliveryClassificationLookup(row_status="not_current")
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


def _supersession_from_row(
    row: sqlite3.Row,
) -> ContentDeliveryIdentitySupersession:
    return ContentDeliveryIdentitySupersession.model_validate_json(
        cast(str, row["payload_json"]), strict=True
    )


def _current_identity_projection(
    connection: sqlite3.Connection,
    binding: ContentDeliveryIdentityBinding,
) -> ContentDeliveryIdentityCurrentProjection:
    latest = load_latest_production_classification_from_connection(connection)
    superseded = (
        connection.execute(
            "SELECT 1 FROM content_delivery_identity_supersessions "
            "WHERE superseded_binding_id = ? LIMIT 1",
            (binding.binding_id,),
        ).fetchone()
        is not None
    )
    return build_content_delivery_identity_current_projection(
        binding,
        _classification_lookup_for_binding(latest, binding),
        assessed_at=datetime.now(UTC),
        superseded=superseded,
    )


def _classification_lookup_for_binding(
    run: object | None,
    binding: ContentDeliveryIdentityBinding,
) -> ContentDeliveryClassificationLookup:
    if run is None:
        return ContentDeliveryClassificationLookup(row_status="run_missing")
    current_run = cast(ContentProductionClassificationRun, run)
    row = current_run.for_work_item(binding.current_work_item_id)
    if row is None:
        return ContentDeliveryClassificationLookup(row_status="missing")
    return ContentDeliveryClassificationLookup(
        row_status="exact",
        run=project_content_production_classification(current_run, row),
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


def binding_from_row(row: sqlite3.Row) -> ContentDeliveryIdentityBinding:
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


__all__ = ["ContentDeliveryIdentityStoreMixin", "binding_from_row"]
