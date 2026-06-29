from __future__ import annotations

from scripts.marketer_language_guard import (
    ACTIVE_PLAN_FILES,
    FORBIDDEN_PLAN_RULE_PHRASES,
    _active_plan_rule_errors,
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
