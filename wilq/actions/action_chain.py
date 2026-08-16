"""Shared verification of the four-event ActionObject apply chain."""

from __future__ import annotations

from collections.abc import Callable

from wilq.schemas import ActionWordPressDraftApplyBlocker, AuditEvent

ActionChain = tuple[AuditEvent, AuditEvent, AuditEvent, AuditEvent]


def revision_bound_action_chain[Binding](
    events: list[AuditEvent],
    *,
    confirmed_by: str,
    binding_from_event: Callable[[AuditEvent], Binding | None] | None = None,
    expected_binding: Binding | None = None,
) -> tuple[ActionChain | None, list[ActionWordPressDraftApplyBlocker]]:
    """Verify the complete, ordered, actor-bound ActionObject apply chain."""
    latest_events = sorted(events, key=lambda event: event.created_at, reverse=True)
    preview = _latest_event(latest_events, {"action_preview_generated"})
    review = next(
        (event for event in latest_events if event.event_type.startswith("human_review_")),
        None,
    )
    confirmation = _latest_event(
        latest_events,
        {
            "action_apply_confirmed",
            "action_confirmation_blocked",
            "action_apply_confirmation_blocked",
        },
    )
    impact = _latest_event(
        latest_events,
        {"action_impact_check_completed", "action_impact_check_blocked"},
    )
    chain_events = [preview, review, confirmation, impact]
    if any(event is None for event in chain_events):
        return None, [
            _blocker(
                "wordpress_action_chain_incomplete",
                "Brakuje pełnego śladu akcji",
                "Apply wymaga preview, approved review, confirm i impact dla tej wersji.",
                "Przejdź po kolei przez cztery kroki ActionObject.",
            )
        ]
    assert preview is not None
    assert review is not None
    assert confirmation is not None
    assert impact is not None
    resolved_events = [event for event in chain_events if event is not None]
    event_bindings = (
        [binding_from_event(event) for event in resolved_events]
        if binding_from_event is not None
        else []
    )
    if event_bindings and any(binding != expected_binding for binding in event_bindings):
        return None, [
            _blocker(
                "wordpress_action_chain_binding_mismatch",
                "Ślad akcji dotyczy innej wersji",
                "Najnowsze preview, review, confirm i impact muszą mieć identyczny binding.",
                "Ponów cały łańcuch ActionObject dla aktualnej zatwierdzonej wersji.",
            )
        ]
    if review.event_type != "human_review_approved_for_prepare":
        return None, [
            _blocker(
                "wordpress_action_review_not_approved",
                "Review ActionObject nie zatwierdza wersji",
                "Najnowsza decyzja ActionObject dla tej wersji nie jest approved_for_prepare.",
                "Sprawdź wersję i zapisz zatwierdzające review ActionObject.",
            )
        ]
    if confirmation.event_type != "action_apply_confirmed":
        return None, [
            _blocker(
                "wordpress_action_confirmation_invalid",
                "Brakuje ważnego potwierdzenia",
                "Najnowsze potwierdzenie tej wersji jest zablokowane albo nie istnieje.",
                "Potwierdź aktualny podgląd jako operator.",
            )
        ]
    if impact.event_type != "action_impact_check_completed":
        return None, [
            _blocker(
                "wordpress_action_impact_invalid",
                "Sprawdzenie efektu jest zablokowane",
                "Apply wymaga zakończonego impact check dla tej samej wersji.",
                "Uzupełnij dowody i ponów impact check.",
            )
        ]
    if confirmation.actor != confirmed_by:
        return None, [
            _blocker(
                "wordpress_action_actor_mismatch",
                "Operator nie pasuje do potwierdzenia",
                "Osoba wywołująca apply musi być osobą, która potwierdziła podgląd.",
                "Wykonaj apply jako operator zapisany w confirm.",
            )
        ]
    if not (
        preview.created_at <= review.created_at <= confirmation.created_at <= impact.created_at
    ):
        return None, [
            _blocker(
                "wordpress_action_chain_order_invalid",
                "Kroki akcji są nieaktualne",
                "Preview, review, confirm i impact nie zostały wykonane w wymaganej kolejności.",
                "Ponów cały łańcuch ActionObject od podglądu.",
            )
        ]
    return (preview, review, confirmation, impact), []


def _latest_event(events: list[AuditEvent], event_types: set[str]) -> AuditEvent | None:
    return next((event for event in events if event.event_type in event_types), None)


def _blocker(
    code: str, label: str, reason: str, next_step: str
) -> ActionWordPressDraftApplyBlocker:
    return ActionWordPressDraftApplyBlocker(
        code=code, label=label, reason=reason, next_step=next_step
    )
