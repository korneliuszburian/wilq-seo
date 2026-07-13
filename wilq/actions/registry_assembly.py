from __future__ import annotations

from collections.abc import Iterable

from wilq.schemas import ActionObject


def assemble_action_registry(
    static_actions: dict[str, ActionObject],
    metric_actions: dict[str, ActionObject],
    *,
    live_data_available: bool,
    configure_action_id: str,
    live_actions: Iterable[ActionObject | None],
) -> dict[str, ActionObject]:
    """Build the one inventory shared by action list and direct lookup."""
    actions = {**static_actions, **metric_actions}
    if not live_data_available:
        return actions
    actions.pop(configure_action_id, None)
    for action in live_actions:
        if action is not None:
            actions[action.id] = action
    return actions
