"""Append-only persistence for landing/hub authorization receipts."""

from __future__ import annotations

import sqlite3
from typing import cast

from wilq.content.workflow.landing_hub import (
    ContentLandingHubAuthorization,
    ContentLandingHubAuthorizationRecordResult,
    canonical_source_fact_registry_digest,
)
from wilq.content.workflow.store.store_production_classification import (
    _classification_from_row,
)
from wilq.storage.model_json import model_json


class ContentLandingHubAuthorizationStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_landing_hub_authorization(
        self,
        authorization: ContentLandingHubAuthorization,
    ) -> ContentLandingHubAuthorizationRecordResult:
        accepted = ContentLandingHubAuthorization.model_validate_json(
            authorization.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            _assert_current_landing_hub_authorization(connection, accepted)
            existing_row = connection.execute(
                "SELECT * FROM content_landing_hub_authorizations WHERE authorization_id = ?",
                (accepted.authorization_id,),
            ).fetchone()
            if existing_row is not None:
                existing = _authorization_from_row(existing_row)
                return ContentLandingHubAuthorizationRecordResult(
                    status=(
                        "idempotent"
                        if existing.authorization_digest == accepted.authorization_digest
                        else "conflict"
                    ),
                    authorization=existing,
                )
            digest_row = connection.execute(
                "SELECT * FROM content_landing_hub_authorizations WHERE authorization_digest = ?",
                (accepted.authorization_digest,),
            ).fetchone()
            if digest_row is not None:
                return ContentLandingHubAuthorizationRecordResult(
                    status="conflict",
                    authorization=_authorization_from_row(digest_row),
                )
            connection.execute(
                """
                INSERT INTO content_landing_hub_authorizations (
                  authorization_id, authorization_digest, work_item_id,
                  classification_run_id, classification_run_digest,
                  decision_set_digest, source_packet_row_digest,
                  canonical_path, public_url, content_kind, input_digest,
                  authorized_by, authorized_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    accepted.content_kind,
                    accepted.input_digest,
                    accepted.authorized_by,
                    accepted.authorized_at.isoformat(),
                    model_json(accepted),
                ),
            )
        return ContentLandingHubAuthorizationRecordResult(
            status="created",
            authorization=accepted,
        )

    def load_landing_hub_authorization(
        self,
        authorization_id: str,
    ) -> ContentLandingHubAuthorization | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM content_landing_hub_authorizations WHERE authorization_id = ?",
                (authorization_id,),
            ).fetchone()
        return None if row is None else _authorization_from_row(row)

    def load_latest_landing_hub_authorization(
        self,
        work_item_id: str,
    ) -> ContentLandingHubAuthorization | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM content_landing_hub_authorizations
                WHERE work_item_id = ?
                ORDER BY authorized_at DESC, rowid DESC
                LIMIT 1
                """,
                (work_item_id,),
            ).fetchone()
            if row is None:
                return None
            authorization = _authorization_from_row(row)
            _assert_current_landing_hub_authorization(connection, authorization)
        return authorization


def _assert_current_landing_hub_authorization(
    connection: sqlite3.Connection,
    authorization: ContentLandingHubAuthorization,
) -> None:
    row = connection.execute(
        """
        SELECT * FROM content_production_classifications
        WHERE run_id = ?
        LIMIT 1
        """,
        (authorization.classification_run_id,),
    ).fetchone()
    if row is None:
        raise ValueError("Landing/hub authorization requires a current classification.")
    run = _classification_from_row(row)
    classified = run.for_work_item(authorization.work_item_id)
    if (
        classified is None
        or classified.current_work_item_id != authorization.work_item_id
        or run.run_digest != authorization.classification_run_digest
        or run.input.decision_set_digest != authorization.decision_set_digest
        or classified.source_packet_row_digest != authorization.source_packet_row_digest
        or classified.canonical_path != authorization.canonical_path
        or classified.public_url != authorization.public_url
        or run.freshness.requires_refresh
        or authorization.wordpress_content_type.casefold() not in {"page", "pages"}
        or authorization.source_fact_registry_digest
        != canonical_source_fact_registry_digest()
    ):
        raise ValueError("Landing/hub authorization no longer matches current classification.")


def _authorization_from_row(row: sqlite3.Row) -> ContentLandingHubAuthorization:
    authorization = ContentLandingHubAuthorization.model_validate_json(
        cast(str, row["payload_json"]), strict=True
    )
    expected = (
        authorization.authorization_id,
        authorization.authorization_digest,
        authorization.work_item_id,
        authorization.classification_run_id,
        authorization.classification_run_digest,
        authorization.decision_set_digest,
        authorization.source_packet_row_digest,
        authorization.canonical_path,
        authorization.public_url,
        authorization.content_kind,
        authorization.input_digest,
        authorization.authorized_by,
        authorization.authorized_at.isoformat(),
    )
    stored = tuple(
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
            "content_kind",
            "input_digest",
            "authorized_by",
            "authorized_at",
        )
    )
    if stored != expected:
        raise ValueError("Stored landing/hub authorization scalars do not match payload.")
    return authorization


__all__ = ["ContentLandingHubAuthorizationStoreMixin"]
