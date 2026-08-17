"""Shared verification of the four-event ActionObject apply chain."""

from __future__ import annotations

from collections.abc import Callable

from wilq.content.operator_copy import build_blocker
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
            build_blocker(
                ActionWordPressDraftApplyBlocker,
                code="wordpress_action_chain_incomplete",
                label="Brakuje pełnego śladu akcji",
                reason="Apply wymaga preview, approved review, confirm i impact dla tej wersji.",
                next_step="Przejdź po kolei przez cztery kroki ActionObject.",
            )
        ]
    if preview is None:
        raise RuntimeError("Preview disappeared after complete ActionObject chain check.")
    if review is None:
        raise RuntimeError("Review disappeared after complete ActionObject chain check.")
    if confirmation is None:
        raise RuntimeError("Confirmation disappeared after complete ActionObject chain check.")
    if impact is None:
        raise RuntimeError("Impact disappeared after complete ActionObject chain check.")
    resolved_events = [event for event in chain_events if event is not None]
    event_bindings = (
        [binding_from_event(event) for event in resolved_events]
        if binding_from_event is not None
        else []
    )
    if event_bindings and any(binding != expected_binding for binding in event_bindings):
        return None, [
            build_blocker(
                ActionWordPressDraftApplyBlocker,
                code="wordpress_action_chain_binding_mismatch",
                label="Ślad akcji dotyczy innej wersji",
                reason="Najnowsze preview, review, confirm i impact muszą mieć identyczny binding.",
                next_step="Ponów cały łańcuch ActionObject dla aktualnej zatwierdzonej wersji.",
            )
        ]
    if review.event_type != "human_review_approved_for_prepare":
        return None, [
            build_blocker(
                ActionWordPressDraftApplyBlocker,
                code="wordpress_action_review_not_approved",
                label="Review ActionObject nie zatwierdza wersji",
                reason="Najnowsza decyzja ActionObject dla tej wersji nie jest approved_for_prepare.",  # noqa: E501
                next_step="Sprawdź wersję i zapisz zatwierdzające review ActionObject.",
            )
        ]
    if confirmation.event_type != "action_apply_confirmed":
        return None, [
            build_blocker(
                ActionWordPressDraftApplyBlocker,
                code="wordpress_action_confirmation_invalid",
                label="Brakuje ważnego potwierdzenia",
                reason="Najnowsze potwierdzenie tej wersji jest zablokowane albo nie istnieje.",
                next_step="Potwierdź aktualny podgląd jako operator.",
            )
        ]
    if impact.event_type != "action_impact_check_completed":
        return None, [
            build_blocker(
                ActionWordPressDraftApplyBlocker,
                code="wordpress_action_impact_invalid",
                label="Sprawdzenie efektu jest zablokowane",
                reason="Apply wymaga zakończonego impact check dla tej samej wersji.",
                next_step="Uzupełnij dowody i ponów impact check.",
            )
        ]
    if confirmation.actor != confirmed_by:
        return None, [
            build_blocker(
                ActionWordPressDraftApplyBlocker,
                code="wordpress_action_actor_mismatch",
                label="Operator nie pasuje do potwierdzenia",
                reason="Osoba wywołująca apply musi być osobą, która potwierdziła podgląd.",
                next_step="Wykonaj apply jako operator zapisany w confirm.",
            )
        ]
    if not (
        preview.created_at <= review.created_at <= confirmation.created_at <= impact.created_at
    ):
        return None, [
            build_blocker(
                ActionWordPressDraftApplyBlocker,
                code="wordpress_action_chain_order_invalid",
                label="Kroki akcji są nieaktualne",
                reason="Preview, review, confirm i impact nie zostały wykonane w wymaganej kolejności.",  # noqa: E501
                next_step="Ponów cały łańcuch ActionObject od podglądu.",
            )
        ]
    return (preview, review, confirmation, impact), []


def _latest_event(events: list[AuditEvent], event_types: set[str]) -> AuditEvent | None:
    return next((event for event in events if event.event_type in event_types), None)
