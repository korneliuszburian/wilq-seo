"""Append-only storage for a scoped classified-refresh authorization."""

from __future__ import annotations

import json
import sqlite3
from typing import cast

from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorization,
    ContentRefreshPreparationAuthorizationRecordResult,
)
from wilq.content.workflow.store.store_content_kind_receipt import (
    assert_persisted_editorial_content_kind_receipt,
)
from wilq.content.workflow.store.store_production_classification import (
    load_latest_production_classification_from_connection,
)
from wilq.storage.model_json import model_json


class RefreshPreparationAuthorizationStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_refresh_preparation_authorization(
        self,
        authorization: ContentRefreshPreparationAuthorization,
    ) -> ContentRefreshPreparationAuthorizationRecordResult:
        accepted = ContentRefreshPreparationAuthorization.model_validate_json(
            authorization.model_dump_json(),
            strict=True,
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if accepted.content_kind == "editorial":
                assert_persisted_editorial_content_kind_receipt(connection, accepted)
            _assert_current_refresh_authorization(connection, accepted)
            existing_row = connection.execute(
                """
                SELECT *
                FROM content_refresh_preparation_authorizations
                WHERE work_item_id = ?
                  AND classification_run_digest = ?
                  AND decision_set_digest = ?
                  AND source_packet_row_digest = ?
                  AND canonical_path = ?
                  AND public_url = ?
                  AND planning_input_digest = ?
                  AND content_kind = ?
                  AND service_card_id IS ?
                LIMIT 1
                """,
                (
                    accepted.work_item_id,
                    accepted.classification_run_digest,
                    accepted.decision_set_digest,
                    accepted.source_packet_row_digest,
                    accepted.canonical_path,
                    accepted.public_url,
                    accepted.planning_input_digest,
                    accepted.content_kind,
                    accepted.service_card_id,
                ),
            ).fetchone()
            if existing_row is not None:
                existing = _authorization_from_row(existing_row)
                return ContentRefreshPreparationAuthorizationRecordResult(
                    status=(
                        "idempotent"
                        if existing.authorization_digest == accepted.authorization_digest
                        else "conflict"
                    ),
                    authorization=existing,
                )
            connection.execute(
                """
                INSERT INTO content_refresh_preparation_authorizations (
                  authorization_id, authorization_digest, work_item_id,
                  classification_run_id, classification_run_digest, decision_set_digest,
                  source_packet_row_digest, canonical_path, public_url,
                  planning_input_digest, content_kind, service_card_id,
                  authorized_by, authorized_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    accepted.authorization_id,
                    accepted.authorization_digest,
                    accepted.work_item_id,
                    accepted.classification_run_id,
                    accepted.classification_run_digest,
                    accepted.decision_set_digest,
                    accepted.source_packet_row_digest,
                    accepted.canonical_path,
                    accepted.public_url,
                    accepted.planning_input_digest,
                    accepted.content_kind,
                    accepted.service_card_id,
                    accepted.authorized_by,
                    accepted.authorized_at.isoformat(),
                    model_json(accepted),
                ),
            )
        return ContentRefreshPreparationAuthorizationRecordResult(
            status="created",
            authorization=accepted,
        )

    def load_refresh_preparation_authorization(
        self,
        authorization_id: str,
    ) -> ContentRefreshPreparationAuthorization | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM content_refresh_preparation_authorizations
                WHERE authorization_id = ?
                LIMIT 1
                """,
                (authorization_id,),
            ).fetchone()
        return None if row is None else _authorization_from_row(row)

    def find_refresh_preparation_authorization(
        self,
        *,
        work_item_id: str,
        classification_run_digest: str,
        decision_set_digest: str,
        source_packet_row_digest: str,
        canonical_path: str,
        public_url: str,
        planning_input_digest: str,
        service_card_id: str | None,
        content_kind: str = "service",
    ) -> ContentRefreshPreparationAuthorization | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM content_refresh_preparation_authorizations
                WHERE work_item_id = ?
                  AND classification_run_digest = ?
                  AND decision_set_digest = ?
                  AND source_packet_row_digest = ?
                  AND canonical_path = ?
                  AND public_url = ?
                  AND planning_input_digest = ?
                  AND content_kind = ?
                  AND service_card_id IS ?
                LIMIT 1
                """,
                (
                    work_item_id,
                    classification_run_digest,
                    decision_set_digest,
                    source_packet_row_digest,
                    canonical_path,
                    public_url,
                    planning_input_digest,
                    content_kind,
                    service_card_id,
                ),
            ).fetchone()
        return None if row is None else _authorization_from_row(row)


def _authorization_from_row(row: sqlite3.Row) -> ContentRefreshPreparationAuthorization:
    authorization = ContentRefreshPreparationAuthorization.model_validate(
        json.loads(cast(str, row["payload_json"]))
    )
    expected_scalars = (
        authorization.authorization_id,
        authorization.authorization_digest,
        authorization.work_item_id,
        authorization.classification_run_id,
        authorization.classification_run_digest,
        authorization.decision_set_digest,
        authorization.source_packet_row_digest,
        authorization.canonical_path,
        authorization.public_url,
        authorization.planning_input_digest,
        authorization.content_kind,
        authorization.service_card_id,
        authorization.authorized_by,
        authorization.authorized_at.isoformat(),
    )
    stored_scalars = tuple(
        row[name]
        for name in (
            "authorization_id",
            "authorization_digest",
            "work_item_id",
            "classification_run_id",
            "classification_run_digest",
            "decision_set_digest",
            "source_packet_row_digest",
            "canonical_path",
            "public_url",
            "planning_input_digest",
            "content_kind",
            "service_card_id",
            "authorized_by",
            "authorized_at",
        )
    )
    if stored_scalars != expected_scalars:
        raise ValueError("Stored refresh preparation authorization scalars do not match receipt.")
    return authorization


def _assert_current_refresh_authorization(
    connection: sqlite3.Connection,
    authorization: ContentRefreshPreparationAuthorization,
) -> None:
    run = load_latest_production_classification_from_connection(connection)
    if run is None:
        raise ValueError("Refresh authorization requires a current classification.")
    row = run.for_work_item(authorization.work_item_id)
    if (
        row is None
        or row.current_work_item_id != authorization.work_item_id
        or row.decision != "refresh"
        or run.freshness.requires_refresh
        or run.run_id != authorization.classification_run_id
        or run.run_digest != authorization.classification_run_digest
        or run.input.decision_set_digest != authorization.decision_set_digest
        or row.source_packet_row_digest != authorization.source_packet_row_digest
        or row.canonical_path != authorization.canonical_path
        or row.public_url != authorization.public_url
        or authorization.acknowledged_classification_blocker_codes
        != sorted(item.code for item in row.blockers)
    ):
        raise ValueError("Refresh authorization does not bind the current classified row.")


__all__ = ["RefreshPreparationAuthorizationStoreMixin"]
