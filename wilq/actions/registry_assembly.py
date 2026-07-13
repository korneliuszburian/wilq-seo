from __future__ import annotations

from collections.abc import Iterable

from wilq.actions.content_refresh import seed_content_refresh_action
from wilq.actions.ga4.tracking_quality import seed_ga4_tracking_quality_action
from wilq.actions.google_ads.oauth import oauth_repair_action
from wilq.actions.google_ads.recommendations import seed_recommendation_review_action
from wilq.actions.merchant import seed_merchant_feed_issue_action
from wilq.actions.wordpress_draft import existing_draft_update_action
from wilq.schemas import ActionObject


def seed_static_actions(
    additional_actions: Iterable[ActionObject | None] = (),
) -> dict[str, ActionObject]:
    """Build the prepare-only inventory shared by list and direct lookup."""
    actions = [
        seed_recommendation_review_action(),
        seed_merchant_feed_issue_action(),
        seed_ga4_tracking_quality_action(),
        seed_content_refresh_action(),
        existing_draft_update_action(),
        oauth_repair_action(),
    ]
    actions.extend(action for action in additional_actions if action is not None)
    return {action.id: action for action in actions}


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
