from __future__ import annotations

from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.handoff.wordpress import (
    ContentWordPressDraftAuditEnvelope,
    ContentWordPressDraftHandoffBlocker,
    apply_content_wordpress_draft_handoff_to_work_item,
    build_content_wordpress_draft_handoff,
    content_wordpress_draft_handoff_blockers,
)
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.models import ContentWorkItem


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
        "human_review_status": "approved",
        "human_review_id": "human_review_bdo",
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
        "publish_ready": False,
    }
    payload.update(overrides)
    return ContentDraftPackage(**payload)


def _review(**overrides: object) -> ContentHumanReview:
    payload: dict[str, object] = {
        "id": "human_review_bdo",
        "work_item_id": "content_work_item_bdo",
        "stage": "wordpress_handoff",
        "reviewed_by": "wilku",
        "decision": "approved",
        "checked_items": ["draft package", "claimy", "final canonical"],
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "draft_package_id": "draft_package_bdo",
    }
    payload.update(overrides)
    return ContentHumanReview(**payload)


def _audit(**overrides: object) -> ContentWordPressDraftAuditEnvelope:
    payload: dict[str, object] = {
        "audit_id": "audit_bdo",
        "actor": "wilku",
        "reason": "Przekazanie zatwierdzonego szkicu do WordPress jako draft.",
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "human_review_id": "human_review_bdo",
    }
    payload.update(overrides)
    return ContentWordPressDraftAuditEnvelope(**payload)


def test_wordpress_handoff_blocks_without_approved_review_audit_and_final_url() -> None:
    item = _item(
        final_canonical_url=None,
        canonical_status="missing",
        human_review_status="needs_changes",
    )

    blockers = content_wordpress_draft_handoff_blockers(
        item=item,
        draft_package=_draft_package(),
        human_review=_review(decision="needs_changes"),
        audit=None,
    )

    assert "missing_final_canonical" in [blocker.code for blocker in blockers]
    assert "human_review_not_approved" in [blocker.code for blocker in blockers]
    _assert_operator_blockers_have_no_jargon(blockers)
    assert "missing_audit" in [blocker.code for blocker in blockers]


def test_wordpress_handoff_blocks_dev_preview_as_final_canonical() -> None:
    result = build_content_wordpress_draft_handoff(
        item=_item(final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/"),
        draft_package=_draft_package(),
        human_review=_review(),
        audit=_audit(),
    )

    assert result.handoff is None
    assert "invalid_final_canonical" in [blocker.code for blocker in result.blockers]
    _assert_operator_blockers_have_no_jargon(result.blockers)


def test_wordpress_handoff_plan_is_draft_only_and_never_publish() -> None:
    result = build_content_wordpress_draft_handoff(
        item=_item(),
        draft_package=_draft_package(),
        human_review=_review(),
        audit=_audit(),
    )

    assert result.blockers == []
    assert result.handoff is not None
    assert result.handoff.connector == "wordpress_ekologus"
    assert result.handoff.post_status == "draft"
    assert result.handoff.publish_allowed is False
    assert result.handoff.destructive_update_allowed is False
    assert result.handoff.final_canonical_url == "https://ekologus.pl/bdo/"
    assert result.handoff.preview_url == "https://ekologus.dev.proudsite.pl/bdo/"


def test_wordpress_handoff_requires_matching_draft_package() -> None:
    result = build_content_wordpress_draft_handoff(
        item=_item(),
        draft_package=_draft_package(id="draft_package_other"),
        human_review=_review(),
        audit=_audit(),
    )

    assert result.handoff is None
    assert "draft_package_mismatch" in [blocker.code for blocker in result.blockers]
    _assert_operator_blockers_have_no_jargon(result.blockers)


def test_wordpress_handoff_updates_workflow_as_prepared_or_created() -> None:
    result = build_content_wordpress_draft_handoff(
        item=_item(wordpress_handoff_status="missing", wordpress_post_id=None),
        draft_package=_draft_package(),
        human_review=_review(),
        audit=_audit(),
    )
    assert result.handoff is not None

    prepared = apply_content_wordpress_draft_handoff_to_work_item(_item(), result.handoff)
    created = apply_content_wordpress_draft_handoff_to_work_item(
        _item(),
        result.handoff,
        wordpress_post_id="123",
    )

    assert prepared.wordpress_handoff_status == "prepared"
    assert prepared.wordpress_post_id is None
    assert created.wordpress_handoff_status == "draft_created"
    assert created.wordpress_post_id == "123"


def _assert_operator_blockers_have_no_jargon(
    blockers: list[ContentWordPressDraftHandoffBlocker],
) -> None:
    forbidden_terms = [
        "human review",
        "review ",
        "handoff",
        "claimy",
        "publish-ready",
        "audit envelope",
        "Draft Package",
        "work item",
        "final canonical URL",
    ]
    for blocker in blockers:
        text = " ".join([blocker.label, blocker.reason, blocker.next_step])
        for term in forbidden_terms:
            assert term.lower() not in text.lower()
