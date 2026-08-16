from __future__ import annotations

import json
import sqlite3
from contextlib import AbstractContextManager
from typing import Protocol, cast

from wilq.content.measurement.deployment import ContentPublicDeployment
from wilq.security.redaction import redact_mapping
from wilq.storage.model_json import model_json


class PublicDeploymentStore(Protocol):
    def run_transaction(self) -> AbstractContextManager[sqlite3.Connection]:
        ...


def save_public_deployment(
    store: PublicDeploymentStore, deployment: ContentPublicDeployment
) -> ContentPublicDeployment:
    redacted = ContentPublicDeployment.model_validate(
        redact_mapping(deployment.model_dump(mode="json"))
    )
    with store.run_transaction() as connection:
        connection.execute(
            """
            INSERT INTO content_public_deployments
              (
                deployment_id, work_item_id, revision_id, revision_digest,
                publication_evidence_id, confirmed_at, payload_json
              )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(work_item_id, revision_id, revision_digest, publication_evidence_id)
            DO NOTHING
            """,
            (
                redacted.deployment_id,
                redacted.work_item_id,
                redacted.revision_id,
                redacted.revision_digest,
                redacted.publication_evidence_id,
                redacted.confirmed_at.isoformat(),
                model_json(redacted),
            ),
        )
        row = connection.execute(
            "SELECT payload_json FROM content_public_deployments WHERE deployment_id = ?",
            (redacted.deployment_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError("Nie udało się odczytać zapisanego potwierdzenia wdrożenia.")
    return ContentPublicDeployment.model_validate(
        json.loads(cast(str, row["payload_json"]))
    )


def public_deployment(
    store: PublicDeploymentStore,
    *,
    work_item_id: str,
    revision_id: str,
    revision_digest: str,
) -> ContentPublicDeployment | None:
    with store.run_transaction() as connection:
        row = connection.execute(
            """
            SELECT payload_json FROM content_public_deployments
            WHERE work_item_id = ? AND revision_id = ? AND revision_digest = ?
            ORDER BY confirmed_at DESC, rowid DESC LIMIT 1
            """,
            (work_item_id, revision_id, revision_digest),
        ).fetchone()
    if row is None:
        return None
    return ContentPublicDeployment.model_validate(
        json.loads(cast(str, row["payload_json"]))
    )
