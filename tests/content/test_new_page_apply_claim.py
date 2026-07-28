from __future__ import annotations

from types import SimpleNamespace

import pytest

from wilq.content.workflow.new_page_revision_binding import ContentNewPageDraftBinding
from wilq.content.workflow.store_new_page_apply import NewPageApplyClaimStore
from wilq.schemas import ActionApplyRequest


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


def test_new_page_claim_is_single_use_for_one_exact_revision(monkeypatch, tmp_path) -> None:
    binding = _binding()
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
        "wilq.content.workflow.store_new_page_apply.latest_draft_revision",
        lambda connection, work_item_id: revision,
    )
    monkeypatch.setattr(
        "wilq.content.workflow.store_new_page_apply.latest_draft_revision_review",
        lambda connection, revision_id: review,
    )
    store = NewPageApplyClaimStore(tmp_path / "claims.sqlite3")

    assert (
        store.claim_new_page_revision_apply(binding, action_id="act_a", claimed_by="Wilku")
        == "acquired"
    )
    assert (
        store.claim_new_page_revision_apply(binding, action_id="act_b", claimed_by="Wilku")
        == "in_progress"
    )
    store.finish_new_page_revision_apply_claim(binding, status="applied")
    assert (
        store.claim_new_page_revision_apply(binding, action_id="act_b", claimed_by="Wilku")
        == "applied"
    )


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
