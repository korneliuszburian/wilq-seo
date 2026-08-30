from __future__ import annotations

import sqlite3
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import wilq.content.workflow.decisions.production as production_module
from tests.content.production_classification_synthetic import build_inputs, resign
from wilq.content.workflow.decisions.production import (
    WAVE0_PRODUCTION_ACCEPTANCE_POLICY,
    ContentProductionClassificationRow,
    ContentProductionClassificationRun,
    classification_counts,
    parse_content_production_classification,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionDecision,
    ContentDraftRevisionReview,
    ContentDraftRevisionSection,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.model_json import model_json

AUDIT_TIME = datetime(2026, 8, 30, 10, 5, tzinfo=UTC)


def exact_public_bdo_run() -> ContentProductionClassificationRun:
    baseline = build_inputs()
    packet = deepcopy(baseline.packet)
    rows = cast(list[dict[str, object]], packet["rows"])
    row = rows[0]
    policy = WAVE0_PRODUCTION_ACCEPTANCE_POLICY
    binding = policy.protected_binding
    retained_id = binding.retained_work_item_id
    assert retained_id is not None
    public_url = f"{policy.public_origin}{binding.canonical_path}/"
    row.update(
        {
            "path": binding.canonical_path,
            "public_url": public_url,
            "work_item_identity": {
                "current_inventory_work_item_id": binding.current_work_item_id,
                "retained_work_item_id": retained_id,
            },
            "revision": {
                "revision_id": binding.revision_id,
                "digest": binding.revision_digest,
                "approved": True,
                "complete": True,
            },
            "retained_revision_binding": {
                "binding_basis": "exact_normalized_path_with_retained_revision_state",
                "current_inventory_work_item_id": binding.current_work_item_id,
                "retained_work_item_id": retained_id,
                "retained_revision_id": binding.revision_id,
                "retained_revision_digest": binding.revision_digest,
                "identity_reconciliation_status": "fork",
                "verified_draft_action_ids": list(binding.action_ids),
                "verified_draft_post_ids": list(binding.draft_post_ids),
                "must_not_regenerate": True,
            },
            "draft_and_action_state": _public_verified_state(public_url, retained_id),
        }
    )
    second_path = cast(str, rows[1]["path"])
    synthetic_policy = baseline.policy.model_copy(
        update={
            "canonical_paths": tuple(sorted((binding.canonical_path, second_path))),
            "protected_binding": binding,
            "public_origin": policy.public_origin,
        }
    )
    accepted = resign(packet, policy=synthetic_policy, sync_policy_decision=True)
    return parse_content_production_classification(
        packet_bytes=accepted.packet_bytes,
        judge_bytes=accepted.judge_bytes,
        acceptance_policy=accepted.policy,
        recorded_by="wilku",
        reviewed_by="independent_test_reviewer",
        recorded_at=AUDIT_TIME,
    )


def retained_missing_run(*, historical_owner: str | None) -> ContentProductionClassificationRun:
    run = exact_public_bdo_run()
    payload = run.rows[0].model_dump(mode="python")
    current_id = cast(str, payload["current_work_item_id"])
    action_owner = historical_owner or current_id
    payload["retained_work_item_id"] = None
    retained = cast(dict[str, object], payload["retained_binding"])
    retained["retained_work_item_id"] = None
    retained["identity_reconciliation_status"] = "retained_missing"
    actions = cast(list[dict[str, object]], payload["verified_actions"])
    actions[0]["bound_work_item_id"] = action_owner
    row = ContentProductionClassificationRow.model_validate(payload)
    return _rebuild_run(run, (row, run.rows[1]))


def stale_reuse_run() -> ContentProductionClassificationRun:
    run = exact_public_bdo_run()
    return production_module._build_run(
        input_receipt=run.input,
        counts=run.counts,
        freshness=run.freshness.model_copy(update={"state": "stale", "requires_refresh": True}),
        source_receipts=run.source_receipts,
        judge_receipt=run.judge_receipt,
        rows=run.rows,
        audit=run.audit,
    )


def nonreuse_run(
    decision: production_module.Classification,
) -> ContentProductionClassificationRun:
    run = exact_public_bdo_run()
    payload = run.rows[1].model_dump(mode="python")
    payload["decision"] = decision
    row = ContentProductionClassificationRow.model_validate(payload)
    return _rebuild_run(run, (run.rows[0], row))


def ready_store(path: Path) -> ContentWorkflowStore:
    store = ContentWorkflowStore(path)
    run = exact_public_bdo_run()
    binding = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding
    retained_id = binding.retained_work_item_id
    assert retained_id is not None
    store.record_production_classification(run)
    revision = draft_revision(retained_id, binding.revision_id, binding.revision_digest)
    insert_revision(store, revision)
    insert_review(store, draft_review(revision))
    return store


def seed_reuse_state(store: ContentWorkflowStore, state: str) -> None:
    binding = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding
    owner = binding.retained_work_item_id
    assert owner is not None
    if state == "missing_revision":
        return
    revision_id = "other_revision" if state == "revision_id_drift" else binding.revision_id
    digest = "d" * 64 if state == "revision_digest_drift" else binding.revision_digest
    revision = draft_revision(owner, revision_id, digest)
    insert_revision(store, revision)
    if state == "later_revision":
        insert_review(store, draft_review(revision))
        later = draft_revision(owner, "later_revision", "e" * 64, number=56)
        insert_revision(store, later)
        insert_review(store, draft_review(later))
        return
    if state in {"revision_id_drift", "revision_digest_drift", "missing_review"}:
        return
    insert_review(store, draft_review(revision))
    if state == "latest_nonapproved_review":
        insert_review(store, draft_review(revision, decision="needs_changes", number=2))
    elif state == "review_identity_mismatch":
        _replace_latest_review_payload(
            store,
            revision.revision_id,
            draft_review(revision).model_copy(update={"work_item_id": "other_owner"}),
        )
    elif state == "review_digest_mismatch":
        _replace_latest_review_payload(
            store,
            revision.revision_id,
            draft_review(revision).model_copy(update={"revision_digest": "f" * 64}),
        )


def draft_revision(
    work_item_id: str,
    revision_id: str,
    digest: str,
    *,
    number: int = 55,
) -> ContentDraftRevision:
    binding = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding
    return ContentDraftRevision(
        revision_id=revision_id,
        work_item_id=work_item_id,
        revision_number=number,
        content_digest=digest,
        draft_package_id=f"draft_{revision_id}",
        draft_package_digest=WAVE0_PRODUCTION_ACCEPTANCE_POLICY.decision_set_digest,
        final_canonical_url=(
            f"{WAVE0_PRODUCTION_ACCEPTANCE_POLICY.public_origin}{binding.canonical_path}/"
        ),
        title="BDO",
        sections=[
            ContentDraftRevisionSection(
                heading="Zakres BDO",
                body_markdown="Zachowana treść BDO do dokładnego przeglądu.",
            )
        ],
        created_by="wilku",
        created_at=AUDIT_TIME,
    )


def draft_review(
    revision: ContentDraftRevision,
    *,
    decision: ContentDraftRevisionDecision = "approved",
    number: int = 1,
) -> ContentDraftRevisionReview:
    return ContentDraftRevisionReview(
        decision_id=f"review_{revision.revision_id}_{number}",
        decision_number=number,
        work_item_id=revision.work_item_id,
        revision_id=revision.revision_id,
        revision_digest=revision.content_digest,
        decision=decision,
        reviewed_by="wilku",
        notes="" if decision == "approved" else "Najnowsze review wymaga zmian.",
        checked_items=["Treść i źródła"],
        evidence_ids=[WAVE0_PRODUCTION_ACCEPTANCE_POLICY.policy_id],
        created_at=AUDIT_TIME,
    )


def insert_revision(store: ContentWorkflowStore, revision: ContentDraftRevision) -> None:
    with store._connect() as connection:
        connection.execute(
            """
            INSERT INTO content_draft_revisions (
              revision_id, work_item_id, revision_number, base_revision_id,
              content_digest, created_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                revision.revision_id,
                revision.work_item_id,
                revision.revision_number,
                revision.base_revision_id,
                revision.content_digest,
                revision.created_at.isoformat(),
                model_json(revision),
            ),
        )


def insert_review(store: ContentWorkflowStore, review: ContentDraftRevisionReview) -> None:
    with store._connect() as connection:
        connection.execute(
            """
            INSERT INTO content_draft_revision_reviews (
              decision_id, work_item_id, revision_id, decision_number,
              revision_digest, decision, created_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review.decision_id,
                review.work_item_id,
                review.revision_id,
                review.decision_number,
                review.revision_digest,
                review.decision,
                review.created_at.isoformat(),
                model_json(review),
            ),
        )


def insert_revision_and_review(
    connection: sqlite3.Connection,
    revision: ContentDraftRevision,
    review: ContentDraftRevisionReview,
) -> None:
    connection.execute(
        """
        INSERT INTO content_draft_revisions (
          revision_id, work_item_id, revision_number, base_revision_id,
          content_digest, created_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            revision.revision_id,
            revision.work_item_id,
            revision.revision_number,
            revision.base_revision_id,
            revision.content_digest,
            revision.created_at.isoformat(),
            model_json(revision),
        ),
    )
    connection.execute(
        """
        INSERT INTO content_draft_revision_reviews (
          decision_id, work_item_id, revision_id, decision_number,
          revision_digest, decision, created_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            review.decision_id,
            review.work_item_id,
            review.revision_id,
            review.decision_number,
            review.revision_digest,
            review.decision,
            review.created_at.isoformat(),
            model_json(review),
        ),
    )


def _public_verified_state(public_url: str, owner: str) -> dict[str, object]:
    binding = WAVE0_PRODUCTION_ACCEPTANCE_POLICY.protected_binding
    action_id = binding.action_ids[0]
    post_id = binding.draft_post_ids[0]
    audit_id = f"mutation_audit_{action_id}"
    return {
        "verified_current_action_bindings": [
            {
                "action_id": action_id,
                "mutation_audit_id": audit_id,
                "action_type": "content_dev_draft_create",
                "status": "applied",
                "bound_work_item_id": owner,
                "bound_revision_id": binding.revision_id,
                "bound_content_digest": binding.revision_digest,
                "bound_final_canonical_url": public_url,
                "adapter_reached": True,
                "external_write_attempted": True,
            }
        ],
        "verified_current_draft_bindings": [
            {
                "action_id": action_id,
                "apply_audit_id": audit_id,
                "post_id": post_id,
                "revision_id": binding.revision_id,
                "revision_digest": binding.revision_digest,
                "readback_content_digest": binding.revision_digest,
                "state_class": "dev_draft_verified",
                "wordpress_draft_status": "draft",
                "readback_status": "verified",
            }
        ],
    }


def _rebuild_run(
    run: ContentProductionClassificationRun,
    rows: tuple[ContentProductionClassificationRow, ...],
) -> ContentProductionClassificationRun:
    return production_module._build_run(
        input_receipt=run.input,
        counts=classification_counts(rows),
        freshness=run.freshness,
        source_receipts=run.source_receipts,
        judge_receipt=run.judge_receipt,
        rows=rows,
        audit=run.audit,
    )


def _replace_latest_review_payload(
    store: ContentWorkflowStore,
    revision_id: str,
    review: ContentDraftRevisionReview,
) -> None:
    with store._connect() as connection:
        connection.execute(
            """
            UPDATE content_draft_revision_reviews SET payload_json = ?
            WHERE revision_id = ? AND decision_number = 1
            """,
            (model_json(review), revision_id),
        )


__all__ = [
    "draft_review",
    "draft_revision",
    "exact_public_bdo_run",
    "insert_review",
    "insert_revision",
    "insert_revision_and_review",
    "nonreuse_run",
    "ready_store",
    "retained_missing_run",
    "seed_reuse_state",
    "stale_reuse_run",
]
