from __future__ import annotations

from collections.abc import Callable

from wilq.schemas import ActionObject, MetricFact

ActionFactory = Callable[[list[MetricFact]], ActionObject | None]
LocaloFacts = Callable[[list[MetricFact]], list[MetricFact]]
LocaloPayload = Callable[[list[MetricFact]], dict[str, object] | None]
LocaloAction = Callable[..., ActionObject]
SocialFactory = Callable[[list[MetricFact]], dict[str, ActionObject]]


def seed_non_ads_metric_actions(
    *,
    by_connector: dict[str, list[MetricFact]],
    merchant_action: ActionFactory,
    ga4_action: ActionFactory,
    localo_facts: LocaloFacts,
    localo_payload: LocaloPayload,
    localo_action: LocaloAction,
    social_action: SocialFactory,
) -> dict[str, ActionObject]:
    actions: dict[str, ActionObject] = {}
    _add_action(actions, merchant_action(by_connector.get("google_merchant_center", [])))
    _add_action(actions, ga4_action(by_connector.get("google_analytics_4", [])))

    localo_metric_facts = localo_facts(by_connector.get("localo", []))
    visibility_payload = localo_payload(localo_metric_facts)
    if visibility_payload is not None:
        localo_review = localo_action(
            localo_facts=localo_metric_facts,
            localo_visibility_payload=visibility_payload,
        )
        actions[localo_review.id] = localo_review

    social_facts = [
        *by_connector.get("google_search_console", []),
        *by_connector.get("google_merchant_center", []),
        *by_connector.get("wordpress_ekologus", []),
        *by_connector.get("google_analytics_4", []),
    ]
    if social_facts:
        actions.update(social_action(social_facts))
    return actions


def _add_action(actions: dict[str, ActionObject], action: ActionObject | None) -> None:
    if action is not None:
        actions[action.id] = action
