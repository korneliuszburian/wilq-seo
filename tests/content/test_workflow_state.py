from __future__ import annotations

from _marketer_language import assert_marketer_text_has_no_workflow_jargon

from wilq.content.workflow.models import (
    ContentWorkItem,
    content_workflow_action_allowed,
    content_workflow_blockers,
)


def _base_item(**overrides: object) -> ContentWorkItem:
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
        "preflight_status": "brief_allowed",
        "preserve_first_plan_status": "approved",
    }
    payload.update(overrides)
    return ContentWorkItem(**payload)


def test_prepare_draft_blocks_missing_required_content_gates() -> None:
    item = _base_item(
        preflight_status="missing",
        sales_brief_status="missing",
        claim_ledger_status="missing",
        measurement_window_status="missing",
    )

    blockers = content_workflow_blockers(item, "prepare_draft")
    blocker_codes = [blocker.code for blocker in blockers]

    assert "missing_preflight" in blocker_codes
    assert "missing_sales_brief" in blocker_codes
    assert "missing_claim_ledger" in blocker_codes
    assert "missing_measurement_window" in blocker_codes
    assert_marketer_text_has_no_workflow_jargon(
        text
        for blocker in blockers
        for text in (blocker.label, blocker.reason, blocker.next_step)
    )
    assert not content_workflow_action_allowed(item, "prepare_draft")


def test_prepare_draft_is_allowed_after_brief_claims_and_measurement_plan() -> None:
    item = _base_item(
        sales_brief_status="approved",
        sales_brief_id="brief_bdo",
        claim_ledger_status="approved",
        claim_ledger_id="claims_bdo",
        measurement_window_status="planned",
        measurement_window_id="measure_bdo",
    )

    assert content_workflow_blockers(item, "prepare_draft") == []
    assert content_workflow_action_allowed(item, "prepare_draft")


def test_dev_preview_url_cannot_be_final_canonical() -> None:
    item = _base_item(final_canonical_url="https://ekologus.dev.proudsite.pl/bdo/")

    blockers = content_workflow_blockers(item, "prepare_sales_brief")
    blocker_codes = [blocker.code for blocker in blockers]

    assert "invalid_final_canonical" in blocker_codes
    assert_marketer_text_has_no_workflow_jargon(
        text
        for blocker in blockers
        for text in (blocker.label, blocker.reason, blocker.next_step)
    )
    assert not content_workflow_action_allowed(item, "prepare_sales_brief")


def test_wordpress_draft_handoff_blocks_without_human_review_and_audit() -> None:
    item = _base_item(
        preflight_status="handoff_allowed",
        sales_brief_status="approved",
        sales_brief_id="brief_bdo",
        claim_ledger_status="approved",
        claim_ledger_id="claims_bdo",
        draft_package_status="ready",
        draft_package_id="draft_bdo",
        measurement_window_status="planned",
        measurement_window_id="measure_bdo",
    )

    blockers = content_workflow_blockers(item, "create_wordpress_draft")
    blocker_codes = [blocker.code for blocker in blockers]

    assert "missing_human_review" in blocker_codes
    assert "missing_audit" in blocker_codes
    assert_marketer_text_has_no_workflow_jargon(
        text
        for blocker in blockers
        for text in (blocker.label, blocker.reason, blocker.next_step)
    )
    assert not content_workflow_action_allowed(item, "create_wordpress_draft")


def test_wordpress_draft_handoff_is_allowed_after_review_audit_and_measurement_plan() -> None:
    item = _base_item(
        preflight_status="handoff_allowed",
        sales_brief_status="approved",
        sales_brief_id="brief_bdo",
        claim_ledger_status="approved",
        claim_ledger_id="claims_bdo",
        draft_package_status="ready",
        draft_package_id="draft_bdo",
        human_review_status="approved",
        human_review_id="review_bdo",
        audit_status="recorded",
        audit_id="audit_bdo",
        measurement_window_status="planned",
        measurement_window_id="measure_bdo",
    )

    assert content_workflow_blockers(item, "create_wordpress_draft") == []
    assert content_workflow_action_allowed(item, "create_wordpress_draft")


def test_measurement_outcome_claim_is_blocked_until_window_ready() -> None:
    item = _base_item(
        measurement_window_status="planned",
        measurement_window_id="measure_bdo",
    )

    blockers = content_workflow_blockers(item, "claim_measurement_outcome")

    assert [blocker.code for blocker in blockers] == ["measurement_window_not_ready"]
    assert "nie może mówić" in blockers[0].reason
    assert_marketer_text_has_no_workflow_jargon(
        text
        for blocker in blockers
        for text in (blocker.label, blocker.reason, blocker.next_step)
    )
    assert not content_workflow_action_allowed(item, "claim_measurement_outcome")


def test_measurement_outcome_claim_is_allowed_when_window_is_ready() -> None:
    item = _base_item(
        measurement_window_status="ready_for_review",
        measurement_window_id="measure_bdo",
    )

    assert content_workflow_blockers(item, "claim_measurement_outcome") == []
    assert content_workflow_action_allowed(item, "claim_measurement_outcome")
