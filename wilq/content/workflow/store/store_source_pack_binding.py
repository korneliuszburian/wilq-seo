"""Append-only persistence for exact content source-pack bindings."""

from __future__ import annotations

import sqlite3
from typing import cast
from uuid import uuid4

from wilq.content.workflow.source_pack_binding import (
    SOURCE_PACK_BINDING_ADAPTER,
    SOURCE_PACK_BINDING_RECORDED_EVENT,
    ContentSourcePackBinding,
    ContentSourcePackBindingCommand,
    ContentSourcePackBindingRecordResult,
    reconcile_content_source_pack_binding,
)
from wilq.content.workflow.store.store_delivery_identity import binding_from_row
from wilq.content.workflow.store.store_queries import upsert_audit_event
from wilq.schemas.actions import AuditEvent
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping
from wilq.storage.model_json import model_json


class ContentSourcePackBindingStoreMixin:
    """Persist only validated, redacted source-pack receipts."""

    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_content_source_pack_binding(
        self,
        command: ContentSourcePackBindingCommand,
    ) -> ContentSourcePackBindingRecordResult:
        """Reconcile one source pack against the exact S1 binding.

        The lookup is deliberately by the caller-supplied S1 binding ID.  No
        path, slug, source-pack ``latest`` row, or fuzzy work-item fallback is
        consulted.
        """

        accepted = ContentSourcePackBindingCommand.model_validate_json(
            command.model_dump_json(), strict=True
        )
        accepted = accepted.model_copy(update={"recorded_at": utc_now()})
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            identity_row = connection.execute(
                """
                SELECT * FROM content_delivery_identity_bindings
                WHERE binding_id = ?
                """,
                (accepted.identity_binding_id,),
            ).fetchone()
            identity = None if identity_row is None else binding_from_row(identity_row)
            prior_rows = connection.execute(
                """
                SELECT *
                FROM content_source_pack_bindings
                WHERE source_pack_id = ?
                  AND identity_binding_id = ?
                  AND current_work_item_id = ?
                  AND status = 'exact_current'
                ORDER BY rowid
                """,
                (
                    accepted.source_pack_id,
                    accepted.identity_binding_id,
                    accepted.current_work_item_id,
                ),
            ).fetchall()
            prior_bindings = tuple(_binding_from_source_pack_row(row) for row in prior_rows)
            binding = reconcile_content_source_pack_binding(
                accepted,
                identity,
                prior_pack_hashes=tuple(item.source_pack_sha256 for item in prior_bindings),
                prior_source_fact_sets=tuple(item.source_fact_ids for item in prior_bindings),
                prior_evidence_sets=tuple(item.evidence_ids for item in prior_bindings),
            )
            existing_row = connection.execute(
                "SELECT * FROM content_source_pack_bindings WHERE binding_id = ?",
                (binding.binding_id,),
            ).fetchone()
            if existing_row is not None:
                existing = _binding_from_source_pack_row(existing_row)
                if existing.binding_digest != binding.binding_digest:
                    _record_source_pack_binding_conflict_audit(connection, binding, existing)
                    return ContentSourcePackBindingRecordResult(
                        status="conflict",
                        binding=existing,
                    )
                return ContentSourcePackBindingRecordResult(
                    status=(
                        "idempotent"
                        if existing.binding_digest == binding.binding_digest
                        else "conflict"
                    ),
                    binding=existing,
                )
            digest_row = connection.execute(
                "SELECT * FROM content_source_pack_bindings WHERE binding_digest = ?",
                (binding.binding_digest,),
            ).fetchone()
            if digest_row is not None:
                existing = _binding_from_source_pack_row(digest_row)
                _record_source_pack_binding_conflict_audit(connection, binding, existing)
                return ContentSourcePackBindingRecordResult(
                    status="conflict",
                    binding=existing,
                )
            _insert_source_pack_binding(connection, binding)
            _record_source_pack_binding_audit(connection, binding)
            if binding.blocker is not None and prior_bindings:
                _record_source_pack_binding_conflict_audit(connection, binding, prior_bindings[0])
        return ContentSourcePackBindingRecordResult(
            status="conflict" if binding.blocker is not None and prior_bindings else "created",
            binding=binding,
        )

    def load_content_source_pack_binding(
        self,
        binding_id: str,
    ) -> ContentSourcePackBinding | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM content_source_pack_bindings WHERE binding_id = ?",
                (binding_id,),
            ).fetchone()
        return None if row is None else _binding_from_source_pack_row(row)


def _binding_from_source_pack_row(row: sqlite3.Row) -> ContentSourcePackBinding:
    binding = ContentSourcePackBinding.model_validate_json(
        cast(str, row["payload_json"]), strict=True
    )
    expected = (
        binding.binding_id,
        binding.binding_digest,
        binding.source_pack_id,
        binding.source_pack_sha256,
        binding.identity_binding_id,
        binding.identity_binding_digest,
        binding.current_work_item_id,
        binding.source_facts_digest,
        binding.evidence_ids_digest,
        binding.fresh_context_digest,
        binding.status,
        binding.recorded_by,
        binding.recorded_at.isoformat(),
    )
    stored = tuple(
        row[name]
        for name in (
            "binding_id",
            "binding_digest",
            "source_pack_id",
            "source_pack_sha256",
            "identity_binding_id",
            "identity_binding_digest",
            "current_work_item_id",
            "source_facts_digest",
            "evidence_ids_digest",
            "fresh_context_digest",
            "status",
            "recorded_by",
            "recorded_at",
        )
    )
    if stored != expected:
        raise ValueError("Stored source-pack binding scalars do not match payload.")
    return binding


def _insert_source_pack_binding(
    connection: sqlite3.Connection,
    binding: ContentSourcePackBinding,
) -> None:
    redacted = ContentSourcePackBinding.model_validate(
        redact_mapping(binding.model_dump(mode="json"))
    )
    connection.execute(
        """
        INSERT INTO content_source_pack_bindings (
          binding_id, binding_digest, source_pack_id, source_pack_sha256,
          identity_binding_id, identity_binding_digest, current_work_item_id,
          source_facts_digest, evidence_ids_digest, fresh_context_digest,
          status, recorded_by, recorded_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            redacted.binding_id,
            redacted.binding_digest,
            redacted.source_pack_id,
            redacted.source_pack_sha256,
            redacted.identity_binding_id,
            redacted.identity_binding_digest,
            redacted.current_work_item_id,
            redacted.source_facts_digest,
            redacted.evidence_ids_digest,
            redacted.fresh_context_digest,
            redacted.status,
            redacted.recorded_by,
            redacted.recorded_at.isoformat(),
            model_json(redacted),
        ),
    )


def _record_source_pack_binding_audit(
    connection: sqlite3.Connection,
    binding: ContentSourcePackBinding,
) -> None:
    evidence_ids = sorted(
        set(binding.evidence_ids)
        | set(binding.source_fact_registry_receipt.evidence_ids)
        | set(binding.fresh_context_attestation.evidence_ids)
    )
    upsert_audit_event(
        connection,
        AuditEvent(
            id=f"audit_{binding.binding_id}",
            event_type=SOURCE_PACK_BINDING_RECORDED_EVENT,
            event_type_label=(
                "Zapisano dokładne powiązanie paczki źródłowej"
                if binding.status == "exact_current"
                else "Zapisano zablokowane powiązanie paczki źródłowej"
            ),
            actor=binding.recorded_by,
            summary=(
                "Zapisano dokładne powiązanie paczki źródłowej z rejestrem i dowodami. "
                "Nie wykonano zapisu zewnętrznego."
                if binding.status == "exact_current"
                else "Zapisano zablokowane powiązanie paczki źródłowej z typowaną blokadą."
            ),
            evidence_ids=evidence_ids,
            details={
                "trace": {
                    "binding_id": binding.binding_id,
                    "binding_digest": binding.binding_digest,
                    "source_pack_id": binding.source_pack_id,
                    "source_pack_sha256": binding.source_pack_sha256,
                    "source_fact_registry_digest": (
                        binding.source_fact_registry_receipt.registry_digest
                    ),
                    "fresh_context_digest": binding.fresh_context_digest,
                    "fresh_context_run_id": binding.fresh_context_attestation.run_id,
                },
                "adapter": SOURCE_PACK_BINDING_ADAPTER,
                "external_write_attempted": False,
            },
        ),
    )


def _record_source_pack_binding_conflict_audit(
    connection: sqlite3.Connection,
    attempted: ContentSourcePackBinding,
    existing: ContentSourcePackBinding,
) -> None:
    upsert_audit_event(
        connection,
        AuditEvent(
            id=f"audit_source_pack_conflict_{attempted.binding_id}_{uuid4().hex}",
            event_type="content_source_pack_binding_conflict",
            event_type_label="Odrzucono konflikt powiązania paczki źródłowej",
            actor=attempted.recorded_by,
            summary="Odrzucono próbę zmiany niezmiennego powiązania paczki źródłowej.",
            evidence_ids=sorted(set(attempted.evidence_ids) | set(existing.evidence_ids)),
            details={
                "trace": {
                    "attempted_binding_digest": attempted.binding_digest,
                    "existing_binding_id": existing.binding_id,
                    "existing_binding_digest": existing.binding_digest,
                },
                "adapter": SOURCE_PACK_BINDING_ADAPTER,
                "external_write_attempted": False,
            },
        ),
    )


__all__ = ["ContentSourcePackBindingStoreMixin"]
