"""State-store transaction invariants for classified refresh generation."""

from __future__ import annotations

import json
import sqlite3

from wilq.content.workflow.decisions.planning import ContentPlanningProposal
from wilq.content.workflow.documents.revisions import ContentDraftRevisionAppendCommand
from wilq.content.workflow.refresh_preparation_contracts import (
    ContentRefreshPreparationAuthorization,
    ContentRefreshPreparationBinding,
    refresh_preparation_binding_matches_content_identity,
)
from wilq.content.workflow.store.store_production_classification import (
    load_latest_production_classification_from_connection,
)


class RefreshPreparationAtomicityError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def assert_refresh_preparation_proposal_current(
    connection: sqlite3.Connection,
    proposal: ContentPlanningProposal,
) -> None:
    _assert_refresh_preparation_current(
        connection,
        binding=proposal.refresh_preparation_binding,
        work_item_id=proposal.work_item_id,
        service_card_id=proposal.service_card_id,
        planning_input_digest=proposal.planning_input_digest,
        final_canonical_url=proposal.final_canonical_url,
    )


def assert_refresh_preparation_revision_current(
    connection: sqlite3.Connection,
    command: ContentDraftRevisionAppendCommand,
) -> None:
    _assert_refresh_preparation_current(
        connection,
        binding=command.refresh_preparation_binding,
        work_item_id=command.work_item_id,
        service_card_id=command.service_card_id,
        planning_input_digest=command.planning_input_digest,
        final_canonical_url=command.final_canonical_url,
    )


def _assert_refresh_preparation_current(
    connection: sqlite3.Connection,
    *,
    binding: ContentRefreshPreparationBinding | None,
    work_item_id: str,
    service_card_id: str | None,
    planning_input_digest: str | None,
    final_canonical_url: str | None,
) -> None:
    if not _table_exists(connection, "content_production_classifications"):
        if binding is not None:
            raise RefreshPreparationAtomicityError("refresh_preparation_authorization_stale")
        return
    classification = load_latest_production_classification_from_connection(connection)
    if classification is None:
        if binding is not None:
            raise RefreshPreparationAtomicityError("refresh_preparation_authorization_stale")
        return
    row = classification.for_work_item(work_item_id)
    if row is None:
        if binding is not None:
            raise RefreshPreparationAtomicityError("refresh_preparation_authorization_foreign")
        return
    if row.current_work_item_id != work_item_id or row.decision != "refresh":
        raise RefreshPreparationAtomicityError("refresh_preparation_proposal_binding_mismatch")
    if binding is None:
        raise RefreshPreparationAtomicityError("refresh_preparation_authorization_missing")
    if not refresh_preparation_binding_matches_content_identity(
        binding,
        work_item_id=work_item_id,
        service_card_id=service_card_id,
        planning_input_digest=planning_input_digest,
        final_canonical_url=final_canonical_url,
    ):
        raise RefreshPreparationAtomicityError("refresh_preparation_proposal_binding_mismatch")
    if (
        binding.classification_run_id != classification.run_id
        or binding.classification_run_digest != classification.run_digest
        or binding.decision_set_digest != classification.input.decision_set_digest
        or binding.source_packet_row_digest != row.source_packet_row_digest
        or binding.canonical_path != row.canonical_path
        or binding.public_url != row.public_url
    ):
        raise RefreshPreparationAtomicityError("refresh_preparation_authorization_stale")
    authorization = _authorization_for_binding(connection, binding)
    if authorization is None or authorization.binding != binding:
        raise RefreshPreparationAtomicityError("refresh_preparation_authorization_stale")


def _authorization_for_binding(
    connection: sqlite3.Connection,
    binding: ContentRefreshPreparationBinding,
) -> ContentRefreshPreparationAuthorization | None:
    if not _table_exists(connection, "content_refresh_preparation_authorizations"):
        return None
    row = connection.execute(
        """
        SELECT *
        FROM content_refresh_preparation_authorizations
        WHERE authorization_id = ? AND authorization_digest = ?
        LIMIT 1
        """,
        (binding.authorization_id, binding.authorization_digest),
    ).fetchone()
    if row is None:
        return None
    try:
        authorization = ContentRefreshPreparationAuthorization.model_validate(
            json.loads(str(row["payload_json"]))
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
        return authorization if stored_scalars == expected_scalars else None
    except Exception as error:
        raise RefreshPreparationAtomicityError(
            "refresh_preparation_authorization_stale"
        ) from error


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (name,),
        ).fetchone()
        is not None
    )


__all__ = [
    "RefreshPreparationAtomicityError",
    "assert_refresh_preparation_proposal_current",
    "assert_refresh_preparation_revision_current",
]
