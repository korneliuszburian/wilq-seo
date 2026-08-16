from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from tests._contract_support.action_safety_factory import synthetic_apply_ready_action
from wilq.actions.google_ads.business_context import (
    strategy_review_action,
    target_confirmation_action,
)
from wilq.actions.service import confirm_action, record_action_review
from wilq.schemas import ActionConfirmRequest, ActionObject, ActionReviewRequest
from wilq.storage.local_state import local_state_store


def test_ads_review_persistence_is_owned_by_action_service(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ads_review.sqlite3"))
    action = strategy_review_action(evidence_ids=["ev_ads_strategy"])

    result = record_action_review(
        action,
        ActionReviewRequest(
            outcome="approved_for_prepare",
            reviewed_by="submitted_operator",
            notes="Strategia sprawdzona przed dalszym przygotowaniem.",
            checked_items=["review_target_fit"],
            blockers=["brak zapisu zmian"],
        ),
    )

    review = local_state_store().latest_ads_strategy_review()
    assert review is not None
    assert review.action_id == action.id
    assert review.outcome == "approved_for_prepare"
    assert review.reviewed_by == result.audit_event.actor
    assert review.reviewed_by == "local_operator"
    assert review.notes == "Strategia sprawdzona przed dalszym przygotowaniem."
    assert review.checked_items == ["review_target_fit"]
    assert review.blockers == ["brak zapisu zmian"]
    assert review.audit_event_id == result.audit_event.id
    assert review.evidence_ids == action.evidence_ids


@pytest.mark.parametrize(
    ("confirm_request", "action_factory"),
    [
        (
            ActionConfirmRequest(confirmed_by="operator", notes="Brak celu."),
            lambda: target_confirmation_action(
                missing_read_contracts=[], evidence_ids=["ev_ads_target"]
            ),
        ),
        (
            ActionConfirmRequest(
                confirmed_by="operator",
                notes="Potwierdzam podgląd.",
                preview_acknowledged=True,
                target_roas=4.2,
            ),
            lambda: synthetic_apply_ready_action("act_non_ads_confirmation"),
        ),
    ],
)
def test_ads_guardrail_persistence_is_limited_to_confirmed_ads_action(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    confirm_request: ActionConfirmRequest,
    action_factory: Callable[[], ActionObject],
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ads_confirmation.sqlite3"))
    action = action_factory()

    result = confirm_action(action, confirm_request)

    assert local_state_store().latest_ads_target_guardrail_confirmation() is None
    if action.id == "act_non_ads_confirmation":
        assert result.confirmed is True
    else:
        assert result.confirmed is False


def test_confirmed_ads_target_persists_stamped_audit_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "ads_target.sqlite3"))
    action = target_confirmation_action(
        missing_read_contracts=[], evidence_ids=["ev_ads_target"]
    )

    result = confirm_action(
        action,
        ActionConfirmRequest(
            confirmed_by="submitted_operator",
            notes="Potwierdzam roboczy target.",
            target_roas=4.2,
        ),
    )

    confirmation = local_state_store().latest_ads_target_guardrail_confirmation()
    assert result.confirmed is True
    assert confirmation is not None
    assert confirmation.action_id == action.id
    assert confirmation.target_roas == 4.2
    assert confirmation.target_cpa_micros is None
    assert confirmation.confirmed_by == result.audit_event.actor == "local_operator"
    assert confirmation.notes == "Potwierdzam roboczy target."
    assert confirmation.audit_event_id == result.audit_event.id
    assert confirmation.evidence_ids == action.evidence_ids
