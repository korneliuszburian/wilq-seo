"""Append-only persistence for exact current content verification receipts."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, cast

from wilq.content.workflow.current_verification import (
    ContentCurrentVerification,
    ContentCurrentVerificationCommand,
    ContentCurrentVerificationRecordResult,
    reconcile_current_verification,
)
from wilq.content.workflow.decisions.production import project_content_production_classification
from wilq.content.workflow.documents.revisions import ContentDraftRevisionReview
from wilq.content.workflow.store.store_production_classification import (
    HISTORICAL_PRODUCTION_POLICY_IDS,
    _classification_from_row,
)
from wilq.storage.model_json import model_json

if TYPE_CHECKING:
    from wilq.content.workflow._source_pack_binding_models import ContentSourcePackBinding
    from wilq.content.workflow.decisions.production import (
        ContentProductionClassificationProjection,
    )
    from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
    from wilq.content.workflow.documents.revision_binding import (
        ContentDraftRevisionBinding,
    )
    from wilq.content.workflow.store.store_evidence import ExactWordPressDraftApplyReceipt


class ContentCurrentVerificationStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    if TYPE_CHECKING:

        def load_exact_wordpress_draft_apply_receipt(
            self,
            binding: ContentDraftRevisionBinding,
            action_id: str,
            mutation_audit_id: str,
        ) -> ExactWordPressDraftApplyReceipt | None: ...

    def record_current_verification(
        self,
        command: ContentCurrentVerificationCommand,
    ) -> ContentCurrentVerificationRecordResult:
        accepted = ContentCurrentVerificationCommand.model_validate_json(
            command.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            identity = _identity(connection, accepted.identity_binding_id)
            source_pack = _source_pack(connection, accepted.source_pack_binding_id)
            classification = _classification(connection, identity)
            review_matches = _review_matches(connection, accepted, identity)
        receipt = self.load_exact_wordpress_draft_apply_receipt(
            accepted.wordpress_draft_binding,
            accepted.action_id,
            accepted.mutation_audit_id,
        )
        verification = reconcile_current_verification(
            accepted,
            classification=classification,
            identity=identity,
            source_pack=source_pack,
            review_matches=review_matches,
            exact_readback_matches=receipt is not None,
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT payload_json FROM content_current_verifications WHERE verification_id = ?",
                (verification.verification_id,),
            ).fetchone()
            if existing is not None:
                stored = ContentCurrentVerification.model_validate_json(
                    cast(str, existing["payload_json"]), strict=True
                )
                return ContentCurrentVerificationRecordResult(
                    status=(
                        "idempotent"
                        if stored.verification_digest == verification.verification_digest
                        else "conflict"
                    ),
                    verification=stored,
                )
            connection.execute(
                """
                INSERT INTO content_current_verifications (
                  verification_id, verification_digest, status, identity_binding_id,
                  source_pack_binding_id, current_work_item_id, revision_id,
                  payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    verification.verification_id,
                    verification.verification_digest,
                    verification.status,
                    verification.identity_binding_id,
                    verification.source_pack_binding_id,
                    verification.current_work_item_id,
                    verification.revision_id,
                    model_json(verification),
                ),
            )
        return ContentCurrentVerificationRecordResult(status="created", verification=verification)

    def load_current_verification(self, verification_id: str) -> ContentCurrentVerification | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_current_verifications WHERE verification_id = ?",
                (verification_id,),
            ).fetchone()
        return (
            None
            if row is None
            else ContentCurrentVerification.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )


def _identity(
    connection: sqlite3.Connection, binding_id: str
) -> ContentDeliveryIdentityBinding | None:
    from wilq.content.workflow.store.store_delivery_identity import binding_from_row

    row = connection.execute(
        "SELECT * FROM content_delivery_identity_bindings WHERE binding_id = ?", (binding_id,)
    ).fetchone()
    return None if row is None else binding_from_row(row)


def _source_pack(
    connection: sqlite3.Connection, binding_id: str
) -> ContentSourcePackBinding | None:
    from wilq.content.workflow.store.store_source_pack_binding import _binding_from_source_pack_row

    row = connection.execute(
        "SELECT * FROM content_source_pack_bindings WHERE binding_id = ?", (binding_id,)
    ).fetchone()
    return None if row is None else _binding_from_source_pack_row(row)


def _classification(
    connection: sqlite3.Connection,
    identity: ContentDeliveryIdentityBinding | None,
) -> ContentProductionClassificationProjection | None:
    if identity is None:
        return None
    row = connection.execute(
        "SELECT * FROM content_production_classifications WHERE run_id = ?",
        (identity.classification_run_id,),
    ).fetchone()
    if row is None or cast(str, row["policy_id"]) in HISTORICAL_PRODUCTION_POLICY_IDS:
        return None
    run = _classification_from_row(row)
    matches = [
        item for item in run.rows if item.current_work_item_id == identity.current_work_item_id
    ]
    return None if len(matches) != 1 else project_content_production_classification(run, matches[0])


def _review_matches(
    connection: sqlite3.Connection,
    command: ContentCurrentVerificationCommand,
    identity: ContentDeliveryIdentityBinding | None,
) -> bool:
    if identity is None:
        return False
    row = connection.execute(
        "SELECT payload_json FROM content_draft_revision_reviews WHERE decision_id = ?",
        (command.review_decision_id,),
    ).fetchone()
    if row is None:
        return False
    review = ContentDraftRevisionReview.model_validate_json(cast(str, row["payload_json"]))
    return (
        review.decision == "approved"
        and review.work_item_id == identity.current_work_item_id
        and review.revision_id == command.revision_id
        and review.revision_digest == command.revision_digest
    )


__all__ = ["ContentCurrentVerificationStoreMixin"]
