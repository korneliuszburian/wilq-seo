from __future__ import annotations

import json

import pytest

from wilq.connectors.wordpress.client import _wordpress_draft_value_digest
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionBoundary,
    ContentWordPressDraftExecutionResult,
    ContentWordPressDraftPayload,
)
from wilq.content.workflow.documents.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionReviewCommand,
    ContentDraftRevisionSection,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.store.store_evidence import ExactWordPressDraftApplyReceipt
from wilq.schemas import ActionMutationAuditRecord, AuditEvent

ACTION_ID = "act_exact_wordpress_receipt"
MUTATION_AUDIT_ID = "mutation_exact_wordpress_receipt"


def _seed_exact_applied_receipt(tmp_path) -> tuple[
    ContentWorkflowStore,
    ContentDraftRevisionBinding,
]:
    store = ContentWorkflowStore(tmp_path / "exact-wordpress-receipt.sqlite3")
    work_item_id = "work_item_exact_wordpress_receipt"
    created = store.append_draft_revision(
        ContentDraftRevisionAppendCommand(
            work_item_id=work_item_id,
            draft_package_id="draft_package_exact_wordpress_receipt",
            draft_package_digest="b" * 64,
            planning_digest="c" * 64,
            final_canonical_url="https://ekologus.pl/exact-wordpress-receipt/",
            title="Dokładny szkic WordPress",
            sections=[
                ContentDraftRevisionSection(
                    heading="Zakres",
                    body_markdown="Treść dokładnego szkicu.",
                    evidence_ids=["ev_exact_wordpress_receipt"],
                )
            ],
            created_by="operator_test",
        )
    )
    assert created.revision is not None
    revision = created.revision
    reviewed = store.review_draft_revision(
        ContentDraftRevisionReviewCommand(
            work_item_id=work_item_id,
            revision_id=revision.revision_id,
            revision_digest=revision.content_digest,
            decision="approved",
            reviewed_by="operator_test",
            checked_items=["tekst"],
            evidence_ids=["ev_exact_wordpress_receipt"],
        )
    )
    assert reviewed.review is not None
    binding = ContentDraftRevisionBinding(
        work_item_id=work_item_id,
        handoff_id=f"wordpress_draft_handoff_{work_item_id}_{revision.revision_id}",
        revision_id=revision.revision_id,
        content_digest=revision.content_digest,
        draft_package_id=revision.draft_package_id,
        draft_package_digest=revision.draft_package_digest,
        planning_digest=revision.planning_digest,
        approval_decision_id=reviewed.review.decision_id,
        final_canonical_url=revision.final_canonical_url,
    )
    title = "Dokładny szkic WordPress"
    content_markdown = "Treść dokładnego szkicu."
    execution = ContentWordPressDraftExecutionResult(
        status="created",
        mode="live",
        boundary=ContentWordPressDraftExecutionBoundary(
            live_write_enabled=True,
            live_adapter_configured=True,
        ),
        revision_binding=binding,
        wordpress_post_id="1901",
        endpoint="posts",
        payload=ContentWordPressDraftPayload(
            title=title,
            content_markdown=content_markdown,
            final_canonical_url=binding.final_canonical_url,
        ),
        expected_content_digest=_wordpress_draft_value_digest(content_markdown),
        observed_content_digest=_wordpress_draft_value_digest(content_markdown),
        expected_title_digest=_wordpress_draft_value_digest(title),
        observed_title_digest=_wordpress_draft_value_digest(title),
        external_write_attempted=True,
    )
    audit_event = AuditEvent(
        id="audit_exact_wordpress_receipt",
        action_id=ACTION_ID,
        event_type="apply_succeeded",
        actor="operator_test",
        summary="Utworzono jeden dokładny szkic WordPress.",
        details={"wordpress_draft_binding": binding.model_dump(mode="json")},
    )
    mutation_audit = ActionMutationAuditRecord(
        id=MUTATION_AUDIT_ID,
        action_id=ACTION_ID,
        connector="wordpress_ekologus",
        action_type="wordpress_draft_handoff",
        status="applied",
        adapter_reached=True,
        external_write_attempted=True,
        mutation_attempted=True,
        mutation_adapter="wordpress_draft_execution_boundary",
        actor="operator_test",
        audit_event_id=audit_event.id,
        wordpress_draft_binding=binding,
        summary="Utworzono jeden dokładny szkic WordPress.",
    )
    assert (
        store.claim_wordpress_revision_apply(
            binding,
            action_id=ACTION_ID,
            claimed_by="operator_test",
        )
        == "acquired"
    )
    store.finish_wordpress_revision_apply_claim(
        binding,
        status="applied",
        audit_event=audit_event,
        mutation_audit=mutation_audit,
        adapter_result={"execution_result": execution.model_dump(mode="json")},
    )
    return store, binding


@pytest.mark.parametrize("tamper", ["execution_approval", "audit_approval", "audit_action"])
def test_exact_wordpress_draft_apply_receipt_is_all_or_nothing(
    tmp_path,
    tamper: str,
) -> None:
    store, binding = _seed_exact_applied_receipt(tmp_path)

    receipt = store.load_exact_wordpress_draft_apply_receipt(
        binding,
        ACTION_ID,
        MUTATION_AUDIT_ID,
    )
    assert isinstance(receipt, ExactWordPressDraftApplyReceipt)
    assert receipt.binding == binding
    assert receipt.action_id == ACTION_ID
    assert receipt.mutation_audit_id == MUTATION_AUDIT_ID
    assert receipt.mutation_audit.wordpress_draft_binding == binding
    assert receipt.execution_result.revision_binding == binding

    # A changed URL must not recover the row through work-item/handoff or URL
    # heuristics: all lookups are exact and claim-key bound.
    assert (
        store.load_exact_wordpress_draft_apply_receipt(
            binding.model_copy(update={"final_canonical_url": "https://ekologus.pl/other/"}),
            ACTION_ID,
            MUTATION_AUDIT_ID,
        )
        is None
    )

    with store._connect() as connection:
        if tamper == "execution_approval":
            row = connection.execute(
                """
                SELECT payload_json FROM content_wordpress_draft_execution_history
                WHERE work_item_id = ? AND handoff_id = ? AND revision_id = ?
                  AND revision_digest = ?
                """,
                (
                    binding.work_item_id,
                    binding.handoff_id,
                    binding.revision_id,
                    binding.content_digest,
                ),
            ).fetchone()
            assert row is not None
            payload = json.loads(row["payload_json"])
            payload["revision_binding"]["approval_decision_id"] = "approval_tampered"
            connection.execute(
                """
                UPDATE content_wordpress_draft_execution_history
                SET payload_json = ?
                WHERE work_item_id = ? AND handoff_id = ? AND revision_id = ?
                  AND revision_digest = ?
                """,
                (
                    json.dumps(payload),
                    binding.work_item_id,
                    binding.handoff_id,
                    binding.revision_id,
                    binding.content_digest,
                ),
            )
        else:
            row = connection.execute(
                "SELECT payload_json FROM action_mutation_audits WHERE id = ? AND action_id = ?",
                (MUTATION_AUDIT_ID, ACTION_ID),
            ).fetchone()
            assert row is not None
            payload = json.loads(row["payload_json"])
            if tamper == "audit_approval":
                payload["wordpress_draft_binding"]["approval_decision_id"] = "approval_tampered"
            else:
                payload["action_id"] = "act_other_action"
            connection.execute(
                "UPDATE action_mutation_audits SET payload_json = ? WHERE id = ?",
                (json.dumps(payload), MUTATION_AUDIT_ID),
            )

    assert (
        store.load_exact_wordpress_draft_apply_receipt(
            binding,
            ACTION_ID,
            MUTATION_AUDIT_ID,
        )
        is None
    )


@pytest.mark.parametrize(
    "tampered_fields",
    [
        {"observed_content_digest": "b" * 64},
        {"observed_title_digest": None},
        {"observed_title_digest": "e" * 64},
        {"endpoint": None},
        {"payload": None},
        {"expected_acf_digest": "f" * 64},
        {"observed_acf_digest": "f" * 64},
        (
            {
                "expected_acf_digest": "f" * 64,
                "observed_acf_digest": "e" * 64,
            }
        ),
    ],
    ids=[
        "content_mismatch",
        "title_missing",
        "title_mismatch",
        "endpoint_missing",
        "payload_missing",
        "acf_missing",
        "acf_observed_only",
        "acf_mismatch",
    ],
)
def test_exact_wordpress_draft_apply_receipt_requires_exact_readback_digests(
    tmp_path,
    tampered_fields: dict[str, str | None],
) -> None:
    store, binding = _seed_exact_applied_receipt(tmp_path)

    with store._connect() as connection:
        row = connection.execute(
            """
            SELECT payload_json FROM content_wordpress_draft_execution_history
            WHERE work_item_id = ? AND handoff_id = ? AND revision_id = ?
              AND revision_digest = ?
            """,
            (
                binding.work_item_id,
                binding.handoff_id,
                binding.revision_id,
                binding.content_digest,
            ),
        ).fetchone()
        assert row is not None
        payload = json.loads(row["payload_json"])
        payload.update(tampered_fields)
        connection.execute(
            """
            UPDATE content_wordpress_draft_execution_history
            SET payload_json = ?
            WHERE work_item_id = ? AND handoff_id = ? AND revision_id = ?
              AND revision_digest = ?
            """,
            (
                json.dumps(payload),
                binding.work_item_id,
                binding.handoff_id,
                binding.revision_id,
                binding.content_digest,
            ),
        )

    assert (
        store.load_exact_wordpress_draft_apply_receipt(
            binding,
            ACTION_ID,
            MUTATION_AUDIT_ID,
        )
        is None
    )


@pytest.mark.parametrize("tamper", ["payload_title", "acf_payload_without_digests"])
def test_exact_wordpress_draft_apply_receipt_binds_readback_digests_to_payload(
    tmp_path,
    tamper: str,
) -> None:
    store, binding = _seed_exact_applied_receipt(tmp_path)

    with store._connect() as connection:
        row = connection.execute(
            """
            SELECT payload_json FROM content_wordpress_draft_execution_history
            WHERE work_item_id = ? AND handoff_id = ? AND revision_id = ?
              AND revision_digest = ?
            """,
            (
                binding.work_item_id,
                binding.handoff_id,
                binding.revision_id,
                binding.content_digest,
            ),
        ).fetchone()
        assert row is not None
        execution_payload = json.loads(row["payload_json"])
        assert execution_payload["payload"] is not None
        if tamper == "payload_title":
            execution_payload["payload"]["title"] = "Inny tytuł"
        else:
            execution_payload["payload"]["authoring_mode"] = "acf_flexible_content"
        connection.execute(
            """
            UPDATE content_wordpress_draft_execution_history
            SET payload_json = ?
            WHERE work_item_id = ? AND handoff_id = ? AND revision_id = ?
              AND revision_digest = ?
            """,
            (
                json.dumps(execution_payload),
                binding.work_item_id,
                binding.handoff_id,
                binding.revision_id,
                binding.content_digest,
            ),
        )

    assert (
        store.load_exact_wordpress_draft_apply_receipt(
            binding,
            ACTION_ID,
            MUTATION_AUDIT_ID,
        )
        is None
    )
