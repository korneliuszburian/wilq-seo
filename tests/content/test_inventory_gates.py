from __future__ import annotations

from wilq.content.inventory.gates import content_inventory_gate_status


def test_inventory_gate_confirms_existing_public_content_for_refresh() -> None:
    status = content_inventory_gate_status(
        decision_type="refresh_or_merge",
        wordpress_match="found",
    )

    assert status["inventory_gate_status"] == "confirmed_current_inventory"
    assert status["canonical_gate_status"] == "public_canonical_confirmed"
    assert status["duplicate_gate_status"] == "existing_public_content_requires_refresh_or_merge"
    assert "nie nowy artykuł" in status["content_gate_summary"]


def test_inventory_gate_blocks_merge_or_create_until_manual_review() -> None:
    status = content_inventory_gate_status(
        decision_type="merge_create_after_inventory_check",
        wordpress_match="missing",
    )

    assert status["inventory_gate_status"] == "missing_inventory_match"
    assert status["canonical_gate_status"] == "blocked_until_content_url_review"
    assert status["duplicate_gate_status"] == "manual_merge_or_create_review"
    assert "kontrola URL i duplikatów" in status["content_gate_summary"]


def test_inventory_gate_blocks_create_until_inventory_review() -> None:
    status = content_inventory_gate_status(
        decision_type="inventory_check_before_create",
        wordpress_match="missing",
    )

    assert status["inventory_gate_status"] == "missing_inventory_match"
    assert status["canonical_gate_status"] == "blocked_until_inventory_review"
    assert status["duplicate_gate_status"] == "create_blocked_until_duplicate_check"
    assert "Plan nowej treści jest zablokowany" in status["content_gate_summary"]


def test_inventory_gate_marks_non_content_plans_as_not_applicable() -> None:
    status = content_inventory_gate_status(
        decision_type="block_as_tracking_not_content",
        wordpress_match="missing",
    )

    assert status["inventory_gate_status"] == "not_applicable"
    assert status["canonical_gate_status"] == "not_applicable"
    assert status["duplicate_gate_status"] == "not_applicable"
    assert "nie jest bezpośrednim planem treści" in status["content_gate_summary"]
