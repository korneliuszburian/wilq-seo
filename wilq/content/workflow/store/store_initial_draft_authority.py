from __future__ import annotations

import sqlite3

from wilq.content.drafts.initial_draft_authority import (
    InitialDraftAuthorityBlocked,
    InitialDraftAuthorityConflict,
    InitialDraftAuthorityIntent,
    InitialDraftAuthorityResolution,
    InitialDraftAuthorityReused,
    InitialDraftAuthorityUnclassified,
    SubmitExpectation,
)
from wilq.content.workflow.decisions.production import (
    ClassificationLookupBasis,
    ContentProductionClassificationRow,
    ContentProductionClassificationRun,
)
from wilq.content.workflow.decisions.production_reuse import (
    ExactProductionReuseBlocked,
    resolve_exact_production_reuse,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
)
from wilq.content.workflow.store.store_production_classification import (
    load_latest_production_classification_from_connection,
)
from wilq.content.workflow.store.store_queries import (
    latest_draft_revision,
    latest_draft_revision_review_for_work_item,
)


class InitialDraftAuthorityStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def resolve_initial_draft_authority(
        self,
        requested_work_item_id: str,
        intent: InitialDraftAuthorityIntent,
    ) -> InitialDraftAuthorityResolution:
        with self._connect() as connection:
            connection.execute("BEGIN")
            run = load_latest_production_classification_from_connection(connection)
            if run is None:
                if (
                    isinstance(intent, SubmitExpectation)
                    and intent.expected_production_classification_run_digest is not None
                ):
                    return InitialDraftAuthorityConflict(
                        requested_work_item_id=requested_work_item_id,
                        code="production_classification_missing",
                    )
                return InitialDraftAuthorityUnclassified(
                    requested_work_item_id=requested_work_item_id
                )

            if isinstance(intent, SubmitExpectation):
                expected_digest = intent.expected_production_classification_run_digest
                if expected_digest is not None and expected_digest != run.run_digest:
                    return InitialDraftAuthorityConflict(
                        requested_work_item_id=requested_work_item_id,
                        code="stale_production_classification",
                    )

            row = run.for_work_item(requested_work_item_id)
            if row is None:
                if (
                    isinstance(intent, SubmitExpectation)
                    and intent.expected_production_classification_run_digest is not None
                ):
                    return InitialDraftAuthorityConflict(
                        requested_work_item_id=requested_work_item_id,
                        code="production_classification_item_missing",
                    )
                return InitialDraftAuthorityUnclassified(
                    requested_work_item_id=requested_work_item_id
                )
            lookup_basis = row.lookup_basis_for_work_item(requested_work_item_id)
            if lookup_basis is None:
                raise ValueError("Accepted classification lost its requested identity.")
            if row.decision == "refresh":
                return InitialDraftAuthorityBlocked(
                    requested_work_item_id=requested_work_item_id,
                    code="production_generation_disabled",
                    reason_pl=row.rationale_pl,
                    safe_next_step_pl=row.next_step_pl,
                    source_codes=tuple(blocker.code for blocker in row.blockers),
                    classification_decision="refresh",
                )
            if (
                isinstance(intent, SubmitExpectation)
                and intent.expected_production_classification_run_digest is None
            ):
                return InitialDraftAuthorityConflict(
                    requested_work_item_id=requested_work_item_id,
                    code="production_classification_digest_required",
                )
            if row.decision != "reuse":
                return InitialDraftAuthorityBlocked(
                    requested_work_item_id=requested_work_item_id,
                    code="production_generation_disabled",
                    reason_pl=row.rationale_pl,
                    safe_next_step_pl=row.next_step_pl,
                    source_codes=tuple(blocker.code for blocker in row.blockers),
                    classification_decision=row.decision,
                )
            stale = _stale_reuse_resolution(run, requested_work_item_id)
            if stale is not None:
                return stale

            return _resolve_reuse_authority(
                connection,
                run=run,
                row=row,
                lookup_basis=lookup_basis,
                requested_work_item_id=requested_work_item_id,
            )


def _latest_reuse_revision_and_review(
    connection: sqlite3.Connection,
    revision_owner: str | None,
) -> tuple[ContentDraftRevision | None, ContentDraftRevisionReview | None]:
    if revision_owner is None:
        return (None, None)
    revision = latest_draft_revision(connection, revision_owner)
    if revision is None:
        return (None, None)
    review = latest_draft_revision_review_for_work_item(
        connection,
        work_item_id=revision_owner,
        revision_id=revision.revision_id,
    )
    return (revision, review)


def _resolve_reuse_authority(
    connection: sqlite3.Connection,
    *,
    run: ContentProductionClassificationRun,
    row: ContentProductionClassificationRow,
    lookup_basis: ClassificationLookupBasis,
    requested_work_item_id: str,
) -> InitialDraftAuthorityResolution:
    binding = row.retained_binding
    current_work_item_id = row.current_work_item_id
    if binding is None or current_work_item_id is None:
        raise ValueError("Accepted reuse classification lost its retained binding.")
    revision_owner = row.reusable_work_item_id
    latest_revision, latest_review = _latest_reuse_revision_and_review(connection, revision_owner)
    reuse = resolve_exact_production_reuse(
        revision_owner_work_item_id=revision_owner,
        expected_revision_id=binding.retained_revision_id,
        expected_revision_digest=binding.retained_revision_digest,
        latest_revision=latest_revision,
        latest_review=latest_review,
    )
    if isinstance(reuse, ExactProductionReuseBlocked):
        return InitialDraftAuthorityBlocked(
            requested_work_item_id=requested_work_item_id,
            code=reuse.code,
        )
    return InitialDraftAuthorityReused(
        classification_run_id=run.run_id,
        classification_run_digest=run.run_digest,
        decision_set_digest=run.input.decision_set_digest,
        requested_work_item_id=requested_work_item_id,
        lookup_basis=lookup_basis,
        current_work_item_id=current_work_item_id,
        retained_work_item_id=row.retained_work_item_id,
        revision_work_item_id=reuse.revision_owner_work_item_id,
        identity_reconciliation_status=binding.identity_reconciliation_status,
        revision=reuse.revision,
        approved_review=reuse.review,
    )


def _stale_reuse_resolution(
    run: ContentProductionClassificationRun,
    requested_work_item_id: str,
) -> InitialDraftAuthorityBlocked | None:
    if not run.freshness.requires_refresh:
        return None
    return InitialDraftAuthorityBlocked(
        requested_work_item_id=requested_work_item_id,
        code="stale_production_classification",
        reason_pl=(
            "Zaakceptowana klasyfikacja produkcyjna wymaga odświeżenia "
            "przed ponownym użyciem dokumentu."
        ),
        safe_next_step_pl=(
            "Odśwież klasyfikację z aktualnych źródeł i ponownie zwiąż żądanie z jej digestem."
        ),
        source_codes=run.freshness.connector_ids,
    )


__all__ = ["InitialDraftAuthorityStoreMixin"]
