"""Canonical ContentWorkflowStore mixin for acquisition run receipts."""

from __future__ import annotations

import sqlite3
from typing import cast

from wilq.content.workflow.evidence_acquisition_contracts import EvidenceAcquisitionRun
from wilq.storage.model_json import model_json


class EvidenceAcquisitionStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def save_evidence_acquisition_run(
        self, run: EvidenceAcquisitionRun
    ) -> EvidenceAcquisitionRun:
        accepted = EvidenceAcquisitionRun.model_validate_json(
            run.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT payload_json FROM content_evidence_acquisition_runs "
                "WHERE run_id = ?",
                (accepted.run_id,),
            ).fetchone()
            if existing is not None:
                stored = EvidenceAcquisitionRun.model_validate_json(
                    cast(str, existing["payload_json"]), strict=True
                )
                if stored.run_digest != accepted.run_digest:
                    raise ValueError("evidence_acquisition_run_conflict")
                return stored
            existing_request = connection.execute(
                "SELECT payload_json FROM content_evidence_acquisition_runs "
                "WHERE request_digest = ?",
                (accepted.request_digest,),
            ).fetchone()
            if existing_request is not None:
                return EvidenceAcquisitionRun.model_validate_json(
                    cast(str, existing_request["payload_json"]), strict=True
                )
            connection.execute(
                """
                INSERT INTO content_evidence_acquisition_runs (
                  run_id, run_digest, request_digest, status, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    accepted.run_id,
                    accepted.run_digest,
                    accepted.request_digest,
                    accepted.status,
                    model_json(accepted),
                ),
            )
        return accepted

    def get_evidence_acquisition_run_by_request_digest(
        self, request_digest: str
    ) -> EvidenceAcquisitionRun | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_evidence_acquisition_runs "
                "WHERE request_digest = ?",
                (request_digest,),
            ).fetchone()
        return (
            None
            if row is None
            else EvidenceAcquisitionRun.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def get_evidence_acquisition_run(self, run_id: str) -> EvidenceAcquisitionRun | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_evidence_acquisition_runs "
                "WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return (
            None
            if row is None
            else EvidenceAcquisitionRun.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def list_evidence_acquisition_runs(self) -> list[EvidenceAcquisitionRun]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM content_evidence_acquisition_runs "
                "ORDER BY run_id"
            ).fetchall()
        return [
            EvidenceAcquisitionRun.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
            for row in rows
        ]


__all__ = ["EvidenceAcquisitionStoreMixin"]
