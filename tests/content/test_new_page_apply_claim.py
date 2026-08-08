from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest

from wilq.content.workflow.store.store_new_page_apply import NewPageApplyClaimStore
from wilq.content.workflow.target.new_page_revision_binding import ContentNewPageDraftBinding
from wilq.schemas import ActionApplyRequest, ActionMutationAuditRecord, AuditEvent


def _binding() -> ContentNewPageDraftBinding:
    return ContentNewPageDraftBinding(
        work_item_id="content_work_item_new_page_claim",
        brief_id="brief_claim",
        brief_digest="a" * 64,
        foundation_id="foundation_claim",
        service_card_id="service_environment",
        service_card_digest="b" * 64,
        revision_id="revision_claim",
        revision_digest="c" * 64,
        authoring_profile_digest="d" * 64,
        content_type="page",
    )


def _adapter_result() -> dict[str, object]:
    return {
        "wordpress_post_id": "42",
        "status": "draft",
        "link": "https://ekologus.dev.proudsite.pl/?p=42",
        "edit_link": (
            "https://ekologus.dev.proudsite.pl/wp-admin/post.php?post=42&action=edit"
        ),
        "external_write_attempted": True,
        "unsafe_vendor_payload": "must-not-be-persisted",
    }


def _stub_current_approved(monkeypatch, binding: ContentNewPageDraftBinding) -> None:
    revision = SimpleNamespace(
        document_kind="new_page",
        revision_id=binding.revision_id,
        content_digest=binding.revision_digest,
        new_page_document_identity=SimpleNamespace(
            brief_id=binding.brief_id,
            brief_digest=binding.brief_digest,
            foundation_id=binding.foundation_id,
            service_card_id=binding.service_card_id,
            service_card_digest=binding.service_card_digest,
        ),
    )
    review = SimpleNamespace(
        decision="approved",
        revision_id=binding.revision_id,
        revision_digest=binding.revision_digest,
    )
    monkeypatch.setattr(
        "wilq.content.workflow.store.store_new_page_apply.latest_draft_revision",
        lambda connection, work_item_id: revision,
    )
    monkeypatch.setattr(
        "wilq.content.workflow.store.store_new_page_apply.latest_draft_revision_review",
        lambda connection, revision_id: review,
    )


def _applied_audits(
    binding: ContentNewPageDraftBinding,
) -> tuple[AuditEvent, ActionMutationAuditRecord]:
    audit_event = AuditEvent(
        id="audit_new_page_claim_applied",
        action_id="act_a",
        event_type="action_apply_completed",
        actor="Wilku",
        summary="Szkic nowej strony został utworzony.",
    )
    mutation_audit = ActionMutationAuditRecord(
        id="mutation_new_page_claim_applied",
        action_id="act_a",
        connector="wordpress_ekologus",
        status="applied",
        actor="Wilku",
        audit_event_id=audit_event.id,
        summary="Wynik zapisu nowej strony został utrwalony.",
        new_page_draft_binding=binding,
    )
    return audit_event, mutation_audit


def test_new_page_claim_finalization_is_atomic(monkeypatch, tmp_path) -> None:
    binding = _binding()
    _stub_current_approved(monkeypatch, binding)
    store = NewPageApplyClaimStore(tmp_path / "claims.sqlite3")

    assert (
        store.claim_new_page_revision_apply(binding, action_id="act_a", claimed_by="Wilku")
        == "acquired"
    )
    assert (
        store.claim_new_page_revision_apply(binding, action_id="act_b", claimed_by="Wilku")
        == "in_progress"
    )
    audit_event, mutation_audit = _applied_audits(binding)
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            """
            CREATE TRIGGER abort_new_page_apply
            AFTER UPDATE OF status ON content_new_page_revision_apply_claims
            WHEN NEW.status = 'applied'
            BEGIN
              SELECT RAISE(ABORT, 'simulated crash after claim update');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="simulated crash"):
        store.finish_new_page_revision_apply_claim(
            binding,
            status="applied",
            audit_event=audit_event,
            mutation_audit=mutation_audit,
            adapter_result=_adapter_result(),
        )

    with sqlite3.connect(store.path) as connection:
        assert connection.execute(
            "SELECT status FROM content_new_page_revision_apply_claims"
        ).fetchone() == ("claimed",)
        assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone() == (0,)
        assert connection.execute(
            "SELECT COUNT(*) FROM action_mutation_audits"
        ).fetchone() == (0,)
        connection.execute("DROP TRIGGER abort_new_page_apply")
        connection.execute(
            """
            CREATE TRIGGER require_new_page_apply_audits
            BEFORE UPDATE OF status ON content_new_page_revision_apply_claims
            WHEN NEW.status = 'applied' AND (
              NOT EXISTS (SELECT 1 FROM audit_events WHERE id = 'audit_new_page_claim_applied')
              OR NOT EXISTS (
                SELECT 1 FROM action_mutation_audits
                WHERE id = 'mutation_new_page_claim_applied'
              )
            )
            BEGIN
              SELECT RAISE(ABORT, 'claim cannot be applied before both audits exist');
            END
            """
        )

    store.finish_new_page_revision_apply_claim(
        binding,
        status="applied",
        audit_event=audit_event,
        mutation_audit=mutation_audit,
        adapter_result=_adapter_result(),
    )

    with sqlite3.connect(store.path) as connection:
        claim_status = connection.execute(
            "SELECT status FROM content_new_page_revision_apply_claims"
        ).fetchone()
        audit_count = connection.execute(
            "SELECT COUNT(*) FROM audit_events WHERE id = ?", (audit_event.id,)
        ).fetchone()
        mutation_count = connection.execute(
            "SELECT COUNT(*) FROM action_mutation_audits WHERE id = ?",
            (mutation_audit.id,),
        ).fetchone()
    assert claim_status == ("applied",)
    assert audit_count == (1,)
    assert mutation_count == (1,)


def test_new_page_claim_finalization_is_idempotent_and_recovers_redacted_result(
    monkeypatch, tmp_path
) -> None:
    binding = _binding()
    _stub_current_approved(monkeypatch, binding)
    store = NewPageApplyClaimStore(tmp_path / "idempotent-claim.sqlite3")
    audit_event, mutation_audit = _applied_audits(binding)
    assert store.claim_new_page_revision_apply(
        binding, action_id="act_a", claimed_by="Wilku"
    ) == "acquired"
    store.finish_new_page_revision_apply_claim(
        binding,
        status="applied",
        audit_event=audit_event,
        mutation_audit=mutation_audit,
        adapter_result=_adapter_result(),
    )
    store.finish_new_page_revision_apply_claim(
        binding,
        status="applied",
        audit_event=audit_event,
        mutation_audit=mutation_audit,
        adapter_result=_adapter_result(),
    )
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone() == (1,)
        assert connection.execute(
            "SELECT COUNT(*) FROM action_mutation_audits"
        ).fetchone() == (1,)
    assert (
        store.claim_new_page_revision_apply(binding, action_id="act_b", claimed_by="Wilku")
        == "applied"
    )
    recovered = store.result_for_action("act_a")
    assert recovered is not None
    assert recovered.wordpress_post_id == "42"
    assert recovered.status == "draft"
    assert recovered.link == "https://ekologus.dev.proudsite.pl/?p=42"
    with sqlite3.connect(store.path) as connection:
        result_json = connection.execute(
            "SELECT result_json FROM content_new_page_revision_apply_claims"
        ).fetchone()[0]
    assert "unsafe_vendor_payload" not in result_json


def test_applied_new_page_claim_without_result_is_uncertain(monkeypatch, tmp_path) -> None:
    binding = _binding()
    _stub_current_approved(monkeypatch, binding)
    store = NewPageApplyClaimStore(tmp_path / "uncertain-claim.sqlite3")
    assert store.claim_new_page_revision_apply(
        binding, action_id="act_uncertain", claimed_by="Wilku"
    ) == "acquired"
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            """
            UPDATE content_new_page_revision_apply_claims
            SET status = 'applied', result_json = NULL
            """
        )

    restarted_store = NewPageApplyClaimStore(store.path)
    assert restarted_store.claim_new_page_revision_apply(
        binding, action_id="act_retry", claimed_by="Wilku"
    ) == "uncertain"
    assert restarted_store.result_for_action("act_uncertain") is None


def test_existing_new_page_apply_claim_table_gains_result_column(tmp_path) -> None:
    path = tmp_path / "legacy-claim.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE content_new_page_revision_apply_claims (
              claim_key TEXT PRIMARY KEY,
              work_item_id TEXT NOT NULL,
              revision_id TEXT NOT NULL,
              revision_digest TEXT NOT NULL,
              action_id TEXT NOT NULL,
              status TEXT NOT NULL CHECK (status IN ('claimed', 'applied', 'failed')),
              claimed_by TEXT NOT NULL,
              claimed_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )

    assert NewPageApplyClaimStore(path).result_for_action("missing") is None
    with sqlite3.connect(path) as connection:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(content_new_page_revision_apply_claims)"
            )
        }
    assert "result_json" in columns


def test_apply_request_rejects_mixed_legacy_and_new_page_bindings() -> None:
    binding = _binding()

    assert (
        ActionApplyRequest(
            confirm=True, confirmed_by="Wilku", new_page_draft=binding
        ).new_page_draft
        == binding
    )
    with pytest.raises(ValueError, match="cannot mix"):
        ActionApplyRequest(
            confirm=True,
            confirmed_by="Wilku",
            new_page_draft=binding,
            wordpress_draft={
                "work_item_id": "other",
                "handoff_id": "handoff",
                "revision_id": "revision",
                "content_digest": "a" * 64,
                "draft_package_id": "package",
                "draft_package_digest": "b" * 64,
                "planning_digest": "c" * 64,
                "approval_decision_id": "review",
                "final_canonical_url": "https://ekologus.pl/",
            },
        )
