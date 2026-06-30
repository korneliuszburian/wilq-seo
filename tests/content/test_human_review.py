from __future__ import annotations

from wilq.content.claims.ledger import ContentClaimLedger, content_claim_entry
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.review.human import (
    ContentHumanReview,
    apply_content_human_review_to_work_item,
    content_human_review_allows_wordpress_handoff,
    content_human_review_blockers,
)
from wilq.content.workflow.models import (
    ContentWorkItem,
    content_workflow_action_allowed,
    content_workflow_blockers,
)


def _item(**overrides: object) -> ContentWorkItem:
    payload: dict[str, object] = {
        "id": "content_work_item_bdo",
        "topic": "BDO dla firm",
        "source_public_url": "https://ekologus.pl/bdo/",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "source_connectors": ["google_search_console", "wordpress_ekologus"],
        "inventory_status": "resolved",
        "canonical_status": "resolved",
        "duplicate_status": "checked",
        "preflight_status": "handoff_allowed",
        "preserve_first_plan_status": "approved",
        "sales_brief_status": "approved",
        "sales_brief_id": "sales_brief_bdo",
        "claim_ledger_status": "approved",
        "claim_ledger_id": "claim_ledger_bdo",
        "draft_package_status": "ready",
        "draft_package_id": "draft_package_bdo",
        "audit_status": "recorded",
        "audit_id": "audit_bdo",
        "measurement_window_status": "planned",
        "measurement_window_id": "measure_bdo",
    }
    payload.update(overrides)
    return ContentWorkItem(**payload)


def _draft_package(**overrides: object) -> ContentDraftPackage:
    payload: dict[str, object] = {
        "id": "draft_package_bdo",
        "work_item_id": "content_work_item_bdo",
        "brief_id": "sales_brief_bdo",
        "claim_ledger_id": "claim_ledger_bdo",
        "title": "BDO dla firm: co sprawdzić",
        "section_to_evidence_map": [
            {"section_heading": "Kogo dotyczy BDO", "evidence_ids": ["ev_gsc_bdo"]}
        ],
        "claims_used": ["Ekologus pomaga firmom w obowiązkach związanych z BDO."],
        "human_review_questions": [
            "Czy szkic brzmi jak Ekologus?",
            "Czy claimy mają dowody?",
        ],
        "publish_ready": False,
    }
    payload.update(overrides)
    return ContentDraftPackage(**payload)


def _review(**overrides: object) -> ContentHumanReview:
    payload: dict[str, object] = {
        "id": "human_review_bdo",
        "work_item_id": "content_work_item_bdo",
        "stage": "draft_package",
        "reviewed_by": "wilku",
        "decision": "approved",
        "notes": "Szkic może iść do WordPress jako draft.",
        "checked_items": [
            "brief zgodny z dowodami",
            "claimy bez gwarancji efektu",
            "CTA bez obietnicy wyniku",
        ],
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "draft_package_id": "draft_package_bdo",
    }
    payload.update(overrides)
    return ContentHumanReview(**payload)


def test_human_review_requires_reviewer_checks_and_evidence() -> None:
    review = _review(reviewed_by=" ", checked_items=[], evidence_ids=[])

    blockers = content_human_review_blockers(
        item=_item(),
        review=review,
        draft_package=_draft_package(),
    )

    assert {blocker.code for blocker in blockers} == {
        "missing_reviewer",
        "missing_checked_items",
        "missing_evidence",
    }


def test_human_review_blocks_wordpress_handoff_when_not_approved() -> None:
    item = _item()
    review = _review(decision="needs_changes")

    reviewed_item = apply_content_human_review_to_work_item(item, review)

    assert reviewed_item.human_review_status == "needs_changes"
    assert reviewed_item.human_review_id == review.id
    assert not content_human_review_allows_wordpress_handoff(
        item=item,
        review=review,
        draft_package=_draft_package(),
    )
    assert "missing_human_review" in [
        blocker.code
        for blocker in content_workflow_blockers(reviewed_item, "create_wordpress_draft")
    ]
    assert not content_workflow_action_allowed(reviewed_item, "create_wordpress_draft")


def test_approved_draft_review_updates_workflow_and_allows_handoff_gate() -> None:
    item = _item(human_review_status="missing", human_review_id=None)
    review = _review()

    reviewed_item = apply_content_human_review_to_work_item(item, review)

    assert content_human_review_allows_wordpress_handoff(
        item=item,
        review=review,
        draft_package=_draft_package(),
    )
    assert reviewed_item.human_review_status == "approved"
    assert reviewed_item.human_review_id == "human_review_bdo"
    assert content_workflow_blockers(reviewed_item, "create_wordpress_draft") == []
    assert content_workflow_action_allowed(reviewed_item, "create_wordpress_draft")


def test_human_review_must_handle_removed_or_blocked_draft_claims() -> None:
    risky_claim = "Ta treść zwiększy liczbę leadów."
    draft_package = _draft_package(claims_removed_or_blocked=[risky_claim])

    missing = content_human_review_blockers(
        item=_item(),
        review=_review(),
        draft_package=draft_package,
    )
    handled = content_human_review_blockers(
        item=_item(),
        review=_review(blocked_claims_handled=[risky_claim]),
        draft_package=draft_package,
    )

    assert "unhandled_blocked_claims" in [blocker.code for blocker in missing]
    assert handled == []


def test_claim_ledger_review_must_handle_blocking_claim_ids() -> None:
    ledger = ContentClaimLedger(
        id="claim_ledger_bdo",
        work_item_id="content_work_item_bdo",
        entries=[
            content_claim_entry(
                claim_id="claim_compliance",
                claim_text="Usługa zapewnia pełną zgodność z wymaganiami.",
                claim_type="legal_requirement_claim",
                evidence_ids=["ev_service_note"],
            )
        ],
    )

    missing = content_human_review_blockers(
        item=_item(),
        review=_review(stage="claim_ledger", draft_package_id=None),
        claim_ledger=ledger,
    )
    handled = content_human_review_blockers(
        item=_item(),
        review=_review(
            stage="claim_ledger",
            draft_package_id=None,
            blocked_claims_handled=["claim_compliance"],
        ),
        claim_ledger=ledger,
    )

    assert "unhandled_blocked_claims" in [blocker.code for blocker in missing]
    assert handled == []
