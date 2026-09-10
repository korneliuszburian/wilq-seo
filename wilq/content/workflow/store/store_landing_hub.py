"""Append-only persistence for landing/hub authorization receipts."""

from __future__ import annotations

import json
import sqlite3
from typing import cast

from wilq.content.workflow.decisions.inventory_binding import ContentKindInventoryBinding
from wilq.content.workflow.landing_hub import (
    ContentLandingHubAuthorization,
    ContentLandingHubAuthorizationRecordResult,
    canonical_source_fact_registry_digest,
    inventory_evidence_digest,
)
from wilq.content.workflow.store.store_production_classification import (
    load_latest_production_classification_from_connection,
)
from wilq.security.redaction import redact_mapping
from wilq.storage.model_json import model_json


class ContentLandingHubAuthorizationStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_landing_hub_authorization(
        self,
        authorization: ContentLandingHubAuthorization,
        *,
        inventory_binding: ContentKindInventoryBinding | None = None,
    ) -> ContentLandingHubAuthorizationRecordResult:
        payload = authorization.model_dump(mode="json")
        redacted_payload = redact_mapping(payload)
        if redacted_payload != payload:
            raise ValueError("Landing/hub authorization must be redacted before persistence.")
        accepted = ContentLandingHubAuthorization.model_validate_json(
            json.dumps(redacted_payload, ensure_ascii=False), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            _assert_current_landing_hub_authorization(connection, accepted, inventory_binding)
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
        *,
        inventory_binding: ContentKindInventoryBinding | None = None,
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
            _assert_current_landing_hub_authorization(connection, authorization, inventory_binding)
        return authorization


def _assert_current_landing_hub_authorization(
    connection: sqlite3.Connection,
    authorization: ContentLandingHubAuthorization,
    inventory_binding: ContentKindInventoryBinding | None,
) -> None:
    if inventory_binding is None:
        raise ValueError("Landing/hub authorization requires current inventory evidence.")
    run = load_latest_production_classification_from_connection(connection)
    if run is None:
        raise ValueError("Landing/hub authorization requires a current classification.")
    classified = run.for_work_item(authorization.work_item_id)
    if (
        classified is None
        or classified.current_work_item_id != authorization.work_item_id
        or classified.decision not in {"refresh", "write"}
        or any(blocker.blocks_initial_generation is True for blocker in classified.blockers)
        or run.run_id != authorization.classification_run_id
        or run.run_digest != authorization.classification_run_digest
        or run.input.decision_set_digest != authorization.decision_set_digest
        or classified.source_packet_row_digest != authorization.source_packet_row_digest
        or classified.canonical_path != authorization.canonical_path
        or classified.public_url != authorization.public_url
        or run.freshness.requires_refresh
        or not inventory_binding.trusted
        or inventory_binding.work_item_id != authorization.work_item_id
        or inventory_binding.canonical_path != authorization.canonical_path
        or inventory_binding.public_url != authorization.public_url
        or inventory_binding.content_kind != "landing_or_hub"
        or inventory_binding.wordpress_content_type.casefold() not in {"page", "pages"}
        or inventory_binding.wordpress_content_type != authorization.wordpress_content_type
        or tuple(sorted(inventory_binding.inventory_evidence_ids))
        != authorization.inventory_evidence_ids
        or inventory_evidence_digest(tuple(sorted(inventory_binding.inventory_evidence_ids)))
        != authorization.inventory_evidence_digest
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
