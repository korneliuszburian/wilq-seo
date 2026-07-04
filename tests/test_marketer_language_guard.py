from __future__ import annotations

from scripts.marketer_language_guard import (
    ACTIVE_PLAN_FILES,
    FORBIDDEN_PHRASES,
    FORBIDDEN_PLAN_RULE_PHRASES,
    GOAL_005_WILKU_FORBIDDEN_PHRASES,
    GOAL_005_WILKU_MATERIAL_FILES,
    _active_plan_rule_errors,
    _goal_005_wilku_material_errors,
)


def test_marketer_language_guard_tracks_active_plan_rule_language() -> None:
    assert "PLAN.md" in {path.as_posix() for path in ACTIVE_PLAN_FILES}
    assert "PLANS.md" in {path.as_posix() for path in ACTIVE_PLAN_FILES}
    assert "docs/goals/001-goal.md" in {
        path.as_posix() for path in ACTIVE_PLAN_FILES
    }
    assert "No evidence ID" in FORBIDDEN_PLAN_RULE_PHRASES
    assert "must not invent metrics" in FORBIDDEN_PLAN_RULE_PHRASES


def test_active_plan_docs_do_not_use_old_english_rule_wording() -> None:
    assert _active_plan_rule_errors() == []


def test_guard_blocks_bare_ads_missing_status_copy() -> None:
    blocked = {item.phrase for item in FORBIDDEN_PHRASES}

    assert "status: " + "brak" in blocked
    assert "kanał: " + "brak" in blocked


def test_goal_005_wilku_material_guard_tracks_recent_handoffs() -> None:
    assert "scripts/record_goal_005_content_uat_result.py" in {
        path.as_posix() for path in GOAL_005_WILKU_MATERIAL_FILES
    }
    assert "docs/handoffs/2026-07-03-wilku-service-profile-review-now.md" in {
        path.as_posix() for path in GOAL_005_WILKU_MATERIAL_FILES
    }

    blocked = {item.phrase for item in GOAL_005_WILKU_FORBIDDEN_PHRASES}

    assert "eval:" in blocked
    assert "raw private text" in blocked
    assert "completion proof" in blocked
    assert "kolejka content" in blocked
    assert "trace czytelny" in blocked


def test_goal_005_wilku_materials_do_not_use_old_trace_wording() -> None:
    assert _goal_005_wilku_material_errors() == []
